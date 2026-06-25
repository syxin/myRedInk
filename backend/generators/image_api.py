"""Image API 图片生成器"""
import logging
import base64
import json
import re
import requests
from typing import Dict, Any, Optional, List, Union
from .base import ImageGeneratorBase
from ..utils.image_compressor import compress_image
from ..utils.size_helper import compute_pixel_size

logger = logging.getLogger(__name__)


class ImageApiGenerator(ImageGeneratorBase):
    """Image API 生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.debug("初始化 ImageApiGenerator...")
        self.base_url = config.get('base_url', 'https://api.example.com').rstrip('/')
        if self.base_url.endswith('/v1'):
            self.base_url = self.base_url[:-3]
        self.model = config.get('model', 'default-model')
        self.default_aspect_ratio = config.get('default_aspect_ratio', '3:4')
        self.image_size = config.get('image_size', '4K')

        # 支持自定义端点路径
        endpoint_type = config.get('endpoint_type', '/v1/images/generations')
        # 兼容旧的简写格式
        if endpoint_type == 'images':
            endpoint_type = '/v1/images/generations'
        elif endpoint_type == 'chat':
            endpoint_type = '/v1/chat/completions'
        # 确保以 / 开头
        if not endpoint_type.startswith('/'):
            endpoint_type = '/' + endpoint_type
        self.endpoint_type = endpoint_type

        logger.info(f"ImageApiGenerator 初始化完成: base_url={self.base_url}, model={self.model}, endpoint={self.endpoint_type}")

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        if not self.api_key:
            logger.error("Image API Key 未配置")
            raise ValueError(
                "Image API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )
        return True

    def get_supported_sizes(self) -> List[str]:
        """获取支持的图片尺寸"""
        return ["1K", "2K", "4K"]

    def get_supported_aspect_ratios(self) -> List[str]:
        """获取支持的宽高比"""
        return ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = None,
        temperature: float = 1.0,
        model: str = None,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None,
        size: Optional[str] = None,
        aspect_ratio_override: Optional[str] = None,
        image_size: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        生成图片

        Args:
            prompt: 图片描述
            aspect_ratio: 宽高比
            temperature: 创意度（未使用，保留接口兼容）
            model: 模型名称
            reference_image: 单张参考图片数据（向后兼容）
            reference_images: 多张参考图片数据列表
            size: 具体像素串（如 "2400x3200"），写入请求体 size 字段
            image_size: 档位名（如 "1K"/"2K"/"4K"），写入请求体 image_size 字段
            aspect_ratio_override: 显式指定的宽高比（来自前端），优先级高于 aspect_ratio

        Returns:
            生成的图片二进制数据
        """
        self.validate_config()

        # 前端显式选择的宽高比优先
        if aspect_ratio_override:
            aspect_ratio = aspect_ratio_override

        if aspect_ratio is None:
            aspect_ratio = self.default_aspect_ratio

        if model is None:
            model = self.model

        # 像素串：前端传过来已经是具体宽高串
        raw_size = size if size else self.image_size
        effective_size = compute_pixel_size(raw_size, aspect_ratio)

        # 档位名：默认用配置 image_size 里的档位（如 "4K"），前端未传时也用配置值
        effective_image_size = image_size if image_size else self.image_size

        logger.info(
            f"Image API 生成图片: model={model}, aspect_ratio={aspect_ratio}, "
            f"size={effective_size}, endpoint={self.endpoint_type}"
        )

        # 根据端点类型选择不同的生成方式
        if 'chat' in self.endpoint_type or 'completions' in self.endpoint_type:
            return self._generate_via_chat_api(
                prompt, aspect_ratio, model, reference_image, reference_images,
                size=effective_size,
                image_size=effective_image_size
            )
        else:
            return self._generate_via_images_api(
                prompt, aspect_ratio, model, reference_image, reference_images,
                size=effective_size,
                image_size=effective_image_size
            )

    def _generate_via_images_api(
        self,
        prompt: str,
        aspect_ratio: str,
        model: str,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None,
        size: Optional[str] = None,
        image_size: Optional[str] = None
    ) -> bytes:
        """通过 /v1/images/generations 端点生成图片"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "response_format": "b64_json",
            "aspect_ratio": aspect_ratio,
        }
        # size：写具体像素串；image_size：写档位（1K/2K/4K），两个字段同时发
        payload["size"] = size if size else self.image_size
        payload["image_size"] = image_size if image_size else self.image_size

        # 收集所有参考图片
        all_reference_images = []
        if reference_images and len(reference_images) > 0:
            all_reference_images.extend(reference_images)
        if reference_image and reference_image not in all_reference_images:
            all_reference_images.append(reference_image)

        # 如果有参考图片，添加到 image 数组
        if all_reference_images:
            logger.debug(f"  添加 {len(all_reference_images)} 张参考图片")
            image_uris = []
            for idx, img_data in enumerate(all_reference_images):
                compressed_img = compress_image(img_data, max_size_kb=200)
                logger.debug(f"  参考图 {idx}: {len(img_data)} -> {len(compressed_img)} bytes")
                base64_image = base64.b64encode(compressed_img).decode('utf-8')
                data_uri = f"data:image/png;base64,{base64_image}"
                image_uris.append(data_uri)

            payload["image"] = image_uris

            ref_count = len(all_reference_images)
            enhanced_prompt = f"""参考提供的 {ref_count} 张图片的风格（色彩、光影、构图、氛围），生成一张新图片。

新图片内容：{prompt}

要求：
1. 保持相似的色调和氛围
2. 使用相似的光影处理
3. 保持一致的画面质感
4. 如果参考图中有人物或产品，可以适当融入"""
            payload["prompt"] = enhanced_prompt

        api_url = f"{self.base_url}{self.endpoint_type}"
        logger.debug(f"  Image API POST {api_url}, 字段={list(payload.keys())}")

        # 显式以 UTF-8 + ensure_ascii=False 序列化，避免 requests 默认把中文转 \uXXXX
        # 这样既减小 body 体积，也能绕开个别中转站对超长 \u 转义解析的兼容性问题
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        send_headers = {**headers, "Content-Type": "application/json; charset=utf-8"}
        prepared = requests.Request(
            "POST", api_url, headers=send_headers, data=body_bytes
        ).prepare()

        response = requests.Session().send(prepared, timeout=900)
        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(f"Image API 请求失败: status={response.status_code}, error={error_detail}")
            raise Exception(
                f"Image API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                f"请求地址: {api_url}\n"
                "可能原因：\n"
                "1. API密钥无效或已过期\n"
                "2. 请求参数不符合API要求\n"
                "3. API服务端错误\n"
                "4. Base URL配置错误\n"
                "建议：检查API密钥和base_url配置"
            )

        # 解析响应：可能是普通 JSON，也可能是 SSE 流式响应
        # （grsai 之类的服务商会以流式方式逐步推送 progress，最终 chunk 才带 results）
        result = self._parse_response_payload(response)
        logger.debug(
            f"  最终响应键: {list(result.keys()) if isinstance(result, dict) else type(result).__name__}"
        )

        # 尝试从多种格式中提取图片：
        # 格式1: {"data": [{"url": "..."}]} 或 {"data": [{"b64_json": "..."}]}
        # 格式2: {"results": [{"url": "..."}]} （grsai/aitohumanize 等服务商）
        # 格式3: 顶层就是 {"url": "..."}（极少见）
        image_item = None
        if isinstance(result, dict):
            if "data" in result and isinstance(result["data"], list) and len(result["data"]) > 0:
                image_item = result["data"][0]
            elif "results" in result and isinstance(result["results"], list) and len(result["results"]) > 0:
                image_item = result["results"][0]
            elif "url" in result or "b64_json" in result:
                image_item = result

        if image_item:
            # 优先尝试 URL 字段
            if "url" in image_item and image_item["url"]:
                image_url = image_item["url"]
                logger.info(f"检测到图片 URL，准备下载: {image_url[:120]}...")
                return self._download_image(image_url)

            # 尝试 b64_json/base64 字段
            if "b64_json" in image_item:
                b64_data_uri = image_item["b64_json"]
                if b64_data_uri.startswith('data:'):
                    b64_string = b64_data_uri.split(',', 1)[1]
                else:
                    b64_string = b64_data_uri
                image_data = base64.b64decode(b64_string)
                logger.info(f"✅ Image API 图片生成成功: {len(image_data)} bytes")
                return image_data

        logger.error(f"无法从响应中提取图片数据: {str(result)[:200]}")
        raise Exception(
            f"图片数据提取失败：未找到 url 或 b64_json 数据。\n"
            f"API响应片段: {str(result)[:500]}\n"
            "可能原因：\n"
            "1. API返回格式与预期不符\n"
            "2. response_format 参数未生效\n"
            "3. 该模型不支持 b64_json 或 url 格式\n"
            "建议：检查API文档确认返回格式要求"
        )

    def _generate_via_chat_api(
        self,
        prompt: str,
        aspect_ratio: str,
        model: str,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None,
        size: Optional[str] = None,
        image_size: Optional[str] = None,
    ) -> bytes:
        """通过 /v1/chat/completions 端点生成图片（如即梦 API）"""
        import re

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建用户消息内容
        user_content: Any = prompt

        # 收集所有参考图片
        all_reference_images = []
        if reference_images and len(reference_images) > 0:
            all_reference_images.extend(reference_images)
        if reference_image and reference_image not in all_reference_images:
            all_reference_images.append(reference_image)

        # 如果有参考图片，构建多模态消息
        if all_reference_images:
            logger.debug(f"  添加 {len(all_reference_images)} 张参考图片到 chat 消息")
            content_parts = [{"type": "text", "text": prompt}]

            for idx, img_data in enumerate(all_reference_images):
                compressed_img = compress_image(img_data, max_size_kb=200)
                logger.debug(f"  参考图 {idx}: {len(img_data)} -> {len(compressed_img)} bytes")
                base64_image = base64.b64encode(compressed_img).decode('utf-8')
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                })

            user_content = content_parts

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": 4096,
            "temperature": 1.0,
        }

        # 中转站在 chat/completions 路径上常常额外支持 size / aspect_ratio 字段
        # 显式传过去，避免有些站点拿不到值就用默认尺寸出图
        if size:
            payload["size"] = size
        if image_size:
            payload["image_size"] = image_size
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio


        api_url = f"{self.base_url}{self.endpoint_type}"
        logger.debug(f"  Image API chat POST {api_url}, 字段={list(payload.keys())}")

        response = requests.post(api_url, headers=headers, json=payload, timeout=900)

        if response.status_code != 200:
            error_detail = response.text[:500]
            status_code = response.status_code

            if status_code == 401:
                raise Exception(
                    "❌ API Key 认证失败\n\n"
                    "【可能原因】\n"
                    "1. API Key 无效或已过期\n"
                    "2. API Key 格式错误\n\n"
                    "【解决方案】\n"
                    "在系统设置页面检查 API Key 是否正确"
                )
            elif status_code == 429:
                raise Exception(
                    "⏳ API 配额或速率限制\n\n"
                    "【解决方案】\n"
                    "1. 稍后再试\n"
                    "2. 检查 API 配额使用情况"
                )
            else:
                raise Exception(
                    f"❌ Chat API 请求失败 (状态码: {status_code})\n\n"
                    f"【错误详情】\n{error_detail[:300]}\n\n"
                    f"【请求地址】{api_url}\n"
                    f"【模型】{model}"
                )

        result = response.json()
        logger.debug(f"Chat API 响应: {str(result)[:500]}")

        # 解析响应
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]

                if isinstance(content, str):
                    # Markdown 图片链接: ![xxx](url)
                    pattern = r'!\[.*?\]\((https?://[^\s\)]+)\)'
                    urls = re.findall(pattern, content)
                    if urls:
                        logger.info(f"从 Markdown 提取到 {len(urls)} 张图片，下载第一张...")
                        return self._download_image(urls[0])

                    # Markdown 图片 Base64: ![xxx](data:image/...)
                    base64_pattern = r'!\[.*?\]\((data:image\/[^;]+;base64,[^\s\)]+)\)'
                    base64_urls = re.findall(base64_pattern, content)
                    if base64_urls:
                        logger.info("从 Markdown 提取到 Base64 图片数据")
                        base64_data = base64_urls[0].split(",")[1]
                        return base64.b64decode(base64_data)

                    # 纯 Base64 data URL
                    if content.startswith("data:image"):
                        logger.info("检测到 Base64 图片数据")
                        base64_data = content.split(",")[1]
                        return base64.b64decode(base64_data)

                    # 纯 URL
                    if content.startswith("http://") or content.startswith("https://"):
                        logger.info("检测到图片 URL")
                        return self._download_image(content.strip())

        raise Exception(
            "❌ 无法从 Chat API 响应中提取图片数据\n\n"
            f"【响应内容】\n{str(result)[:500]}\n\n"
            "【可能原因】\n"
            "1. 该模型不支持图片生成\n"
            "2. 响应格式与预期不符\n"
            "3. 提示词被安全过滤\n\n"
            "【解决方案】\n"
            "1. 确认模型名称正确\n"
            "2. 修改提示词后重试"
        )

    def _download_image(self, url: str) -> bytes:
        """下载图片并返回二进制数据"""
        logger.info(f"下载图片: {url[:100]}...")
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                logger.info(f"✅ 图片下载成功: {len(response.content)} bytes")
                return response.content
            else:
                raise Exception(f"下载图片失败: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            raise Exception("❌ 下载图片超时，请重试")
        except Exception as e:
            raise Exception(f"❌ 下载图片失败: {str(e)}")

    def _parse_response_payload(self, response: requests.Response) -> dict:
        """
        解析 API 响应，兼容普通 JSON 与 SSE 流式响应。

        部分服务商（如 grsai）会以 text/event-stream 方式流式返回，
        逐行推送中间 progress 状态，最后一行才带 results。
        """
        content_type = response.headers.get("content-type", "").lower()

        # ===== SSE 流式响应 =====
        if "text/event-stream" in content_type or "stream" in content_type:
            logger.info("检测到流式响应，按行解析以获取最终结果...")
            last_valid_json: Optional[dict] = None
            try:
                for raw_line in response.iter_lines(decode_unicode=True, chunk_size=8192):
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if line.startswith("event:"):
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if not line or line.startswith(":"):
                        continue
                    if line in ("[DONE]", "[END]"):
                        break
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug(f"  跳过非 JSON 行: {line[:80]}")
                        continue
                    if not isinstance(chunk, dict):
                        continue
                    last_valid_json = chunk
                    # 一旦出现带图片结果的 chunk 立即返回
                    has_data = isinstance(chunk.get("data"), list) and len(chunk["data"]) > 0
                    has_results = isinstance(chunk.get("results"), list) and len(chunk["results"]) > 0
                    if has_data or has_results:
                        logger.debug(f"  捕获到最终结果 chunk，键={list(chunk.keys())}")
                        return chunk
                if last_valid_json is not None:
                    logger.debug(f"  使用最后一条 JSON 作为结果，键={list(last_valid_json.keys())}")
                    return last_valid_json
                raise ValueError("流式响应中未发现可解析的 JSON")
            except Exception as e:
                logger.warning(f"SSE 解析失败，尝试整体回退: {e}")

        # ===== 普通 JSON 响应 =====
        text = response.text
        try:
            return response.json()
        except json.JSONDecodeError:
            cleaned = text.lstrip("\ufeff").strip()
            # 某些服务商即便 content-type 是 application/json 也会推多段
            # 这种情况下取最后一段非空 JSON
            if "\n" in cleaned:
                segments = [seg.strip() for seg in cleaned.split("\n") if seg.strip()]
                for seg in reversed(segments):
                    if seg.startswith("data:"):
                        seg = seg[5:].strip()
                    try:
                        return json.loads(seg)
                    except json.JSONDecodeError:
                        continue
            # 最后兜底：用正则抓出第一个 JSON 对象
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            logger.error(f"响应无法解析为 JSON，前 500 字符: {text[:500]}")
            raise ValueError("API 返回格式不是有效的 JSON")
