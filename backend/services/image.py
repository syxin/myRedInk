"""图片生成服务"""
import logging
import os
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Generator, List, Optional, Tuple
from backend.config import Config
from backend.generators.factory import ImageGeneratorFactory
from backend.utils.image_compressor import compress_image
from backend.utils.size_helper import compute_pixel_size

logger = logging.getLogger(__name__)


class ImageService:
    """图片生成服务类"""

    # 并发配置
    MAX_CONCURRENT = 15  # 最大并发数
    AUTO_RETRY_COUNT = 1  # 不自动重试，超时后让用户手动重试

    def __init__(self, provider_name: str = None):
        """
        初始化图片生成服务

        Args:
            provider_name: 服务商名称，如果为None则使用配置文件中的激活服务商
        """
        logger.debug("初始化 ImageService...")

        # 获取服务商配置
        if provider_name is None:
            provider_name = Config.get_active_image_provider()

        logger.info(f"使用图片服务商: {provider_name}")
        provider_config = Config.get_image_provider_config(provider_name)

        # 创建生成器实例
        provider_type = provider_config.get('type', provider_name)
        logger.debug(f"创建生成器: type={provider_type}")
        self.generator = ImageGeneratorFactory.create(provider_type, provider_config)

        # 保存配置信息
        self.provider_name = provider_name
        self.provider_config = provider_config

        # 检查是否启用短 prompt 模式
        self.use_short_prompt = provider_config.get('short_prompt', False)

        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()
        self.prompt_template_short = self._load_prompt_template(short=True)

        # 历史记录根目录
        self.history_root_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "history"
        )
        os.makedirs(self.history_root_dir, exist_ok=True)

        # 当前任务的输出目录（每个任务一个子文件夹）
        self.current_task_dir = None

        # 存储任务状态（用于重试）
        self._task_states: Dict[str, Dict] = {}

        logger.info(f"ImageService 初始化完成: provider={provider_name}, type={provider_type}")

    def _load_prompt_template(self, short: bool = False) -> str:
        """加载 Prompt 模板"""
        filename = "image_prompt_short.txt" if short else "image_prompt.txt"
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            filename
        )
        if not os.path.exists(prompt_path):
            # 如果短模板不存在，返回空字符串
            return ""
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _save_image(self, image_data: bytes, filename: str, task_dir: str = None) -> str:
        """
        保存图片到本地，同时生成缩略图

        Args:
            image_data: 图片二进制数据
            filename: 文件名
            task_dir: 任务目录（如果为None则使用当前任务目录）

        Returns:
            保存的文件路径
        """
        if task_dir is None:
            task_dir = self.current_task_dir

        if task_dir is None:
            raise ValueError("任务目录未设置")

        # 保存原图
        filepath = os.path.join(task_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)

        # 生成缩略图（50KB左右）
        thumbnail_data = compress_image(image_data, max_size_kb=50)
        thumbnail_filename = f"thumb_{filename}"
        thumbnail_path = os.path.join(task_dir, thumbnail_filename)
        with open(thumbnail_path, "wb") as f:
            f.write(thumbnail_data)

        return filepath

    def _generate_single_image(
        self,
        page: Dict,
        task_id: str,
        reference_image: Optional[bytes] = None,
        retry_count: int = 0,
        full_outline: str = "",
        user_images: Optional[List[bytes]] = None,
        user_topic: str = "",
        image_size: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        image_size_base: Optional[str] = None
    ) -> Tuple[int, bool, Optional[str], Optional[str]]:
        """
        生成单张图片（带自动重试）

        Args:
            page: 页面数据
            task_id: 任务ID
            reference_image: 参考图片（封面图）
            retry_count: 当前重试次数
            full_outline: 完整的大纲文本
            user_images: 用户上传的参考图片列表
            user_topic: 用户原始输入
            image_size: 用户选择的具体像素串，如 "2400x3200"
            aspect_ratio: 用户选择的宽高比，如 "3:4"
            image_size_base: 用户选择的档位 "1K"/"2K"/"4K"（自定义宽高时为 None）

        Returns:
            (index, success, filename, error_message)
        """
        index = page["index"]
        page_type = page["type"]
        page_content = page["content"]

        try:
            logger.debug(f"生成图片 [{index}]: type={page_type}")

            # 根据配置选择模板（短 prompt 或完整 prompt）
            if self.use_short_prompt and self.prompt_template_short:
                # 短 prompt 模式：只包含页面类型和内容
                prompt = self.prompt_template_short.format(
                    page_content=page_content,
                    page_type=page_type
                )
                logger.debug(f"  使用短 prompt 模式 ({len(prompt)} 字符)")
            else:
                # 完整 prompt 模式：包含大纲和用户需求
                prompt = self.prompt_template.format(
                    page_content=page_content,
                    page_type=page_type,
                    full_outline=full_outline,
                    user_topic=user_topic if user_topic else "未提供"
                )


            # 调用生成器生成图片
            if self.provider_config.get('type') == 'google_genai':
                logger.debug(f"  使用 Google GenAI 生成器")
                # Google GenAI 只接受 aspect_ratio，不接受具体像素 size；
                # 但仍按统一逻辑解析比例（容忍前端 image_size 是 "1K"/"2K"/"4K" 时复用默认比例）
                effective_aspect_ratio = aspect_ratio or self.provider_config.get('default_aspect_ratio', '3:4')
                image_data = self.generator.generate_image(
                    prompt=prompt,
                    aspect_ratio=effective_aspect_ratio,
                    temperature=self.provider_config.get('temperature', 1.0),
                    model=self.provider_config.get('model', 'gemini-3-pro-image-preview'),
                    reference_image=reference_image,
                )
            elif self.provider_config.get('type') == 'image_api':
                logger.debug(f"  使用 Image API 生成器")
                # Image API 支持多张参考图片
                # 组合参考图片：用户上传的图片 + 封面图
                reference_images = []
                if user_images:
                    reference_images.extend(user_images)
                if reference_image:
                    reference_images.append(reference_image)

                effective_aspect_ratio = aspect_ratio or self.provider_config.get('default_aspect_ratio', '3:4')
                effective_size = compute_pixel_size(
                    image_size or self.provider_config.get('image_size'),
                    effective_aspect_ratio,
                )
                image_data = self.generator.generate_image(
                    prompt=prompt,
                    aspect_ratio=effective_aspect_ratio,
                    temperature=self.provider_config.get('temperature', 1.0),
                    model=self.provider_config.get('model', 'nano-banana-2'),
                    reference_images=reference_images if reference_images else None,
                    size=effective_size,
                    image_size=image_size_base,
                )
            else:
                logger.debug(f"  使用 OpenAI 兼容生成器")
                # 同样归一化：传给 OpenAI 兼容接口的 size 必须是像素串
                effective_aspect_ratio = aspect_ratio or self.provider_config.get('default_aspect_ratio', '3:4')
                effective_size = compute_pixel_size(
                    image_size or self.provider_config.get('default_size'),
                    effective_aspect_ratio,
                )
                image_data = self.generator.generate_image(
                    prompt=prompt,
                    size=effective_size,
                    aspect_ratio=effective_aspect_ratio,
                    model=self.provider_config.get('model'),
                    quality=self.provider_config.get('quality', 'standard'),
                    image_size=image_size_base,
                )

            # 保存图片（使用当前任务目录）
            filename = f"{index}.png"
            self._save_image(image_data, filename, self.current_task_dir)
            logger.info(f"✅ 图片 [{index}] 生成成功: {filename}")

            return (index, True, filename, None)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 图片 [{index}] 生成失败: {error_msg[:200]}")
            return (index, False, None, error_msg)

    def generate_images(
        self,
        pages: list,
        task_id: str = None,
        full_outline: str = "",
        user_images: Optional[List[bytes]] = None,
        user_topic: str = "",
        image_size: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        image_size_base: Optional[str] = None,
        sequential_reference: bool = False
    ) -> Generator[Dict[str, Any], None, None]:
        """
        生成图片（生成器，支持 SSE 流式返回）
        优化版本：先生成封面，然后并发生成其他页面

        Args:
            pages: 页面列表
            task_id: 任务 ID（可选）
            full_outline: 完整的大纲文本（用于保持风格一致）
            user_images: 用户上传的参考图片列表（可选）
            user_topic: 用户原始输入（用于保持意图一致）
            image_size: 用户选择的基准分辨率（如 "1K"/"2K"/"4K"）
            aspect_ratio: 用户选择的宽高比
            sequential_reference: 「依次参考」开关。开启且 len(user_images) == len(pages) 时，
                第 N 页仅使用第 N 张用户参考图；关闭时保持旧逻辑（合并封面 + 所有用户图）。

        Yields:
            进度事件字典
        """
        if task_id is None:
            task_id = f"task_{uuid.uuid4().hex[:8]}"

        logger.info(f"开始图片生成任务: task_id={task_id}, pages={len(pages)}")

        # 创建任务专属目录
        self.current_task_dir = os.path.join(self.history_root_dir, task_id)
        os.makedirs(self.current_task_dir, exist_ok=True)
        logger.debug(f"任务目录: {self.current_task_dir}")

        total = len(pages)
        generated_images = []
        failed_pages = []
        cover_image_data = None

        # 压缩用户上传的参考图到200KB以内（减少内存和传输开销）
        compressed_user_images = None
        if user_images:
            compressed_user_images = [compress_image(img, max_size_kb=200) for img in user_images]

        # 判断「依次参考」是否真正生效：开关开启 + 参考图张数 == 页面张数
        seq_ref_enabled = bool(
            sequential_reference
            and compressed_user_images
            and len(compressed_user_images) == total
        )
        if sequential_reference and not seq_ref_enabled:
            logger.warning(
                f"「依次参考」被请求但未生效：user_images={len(compressed_user_images) if compressed_user_images else 0}, "
                f"pages={total}"
            )
        if seq_ref_enabled:
            logger.info(f"✅ 「依次参考」已启用：{total} 页 与 {len(compressed_user_images)} 张参考图一一对应")

        # 初始化任务状态
        self._task_states[task_id] = {
            "pages": pages,
            "generated": {},
            "failed": {},
            "cover_image": None,
            "full_outline": full_outline,
            "user_images": compressed_user_images,
            "user_topic": user_topic,
            "image_size": image_size,
            "aspect_ratio": aspect_ratio,
            "image_size_base": image_size_base,
            "sequential_reference": seq_ref_enabled,
            "total_pages": total,
        }

        # ==================== 判断是否需要封面作为参考 ====================
        # 当有用户参考图或启用依次参考时，不需要先串行生成封面作为风格参考，
        # 所有页面可一起并发生成，消除封面串行阻塞。
        need_cover_first = not seq_ref_enabled and not compressed_user_images

        if not need_cover_first:
            # ============ 全并发模式：封面 + 内容页一起生成 ============
            cover_page = None
            for page in pages:
                if page["type"] == "cover":
                    cover_page = page
                    break
            if cover_page is None and len(pages) > 0:
                cover_page = pages[0]

            high_concurrency = self.provider_config.get('high_concurrency', False)

            if high_concurrency:
                yield {
                    "event": "progress",
                    "data": {
                        "status": "batch_start",
                        "message": f"开始并发生成 {total} 页（含封面）...",
                        "current": 0,
                        "total": total,
                        "phase": "batch"
                    }
                }

                with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
                    future_to_page = {}
                    for page in pages:
                        if seq_ref_enabled:
                            per_page_user_images = [compressed_user_images[page["index"]]]
                        else:
                            per_page_user_images = compressed_user_images
                        future_to_page[executor.submit(
                            self._generate_single_image,
                            page, task_id, None, 0,
                            full_outline, per_page_user_images, user_topic,
                            image_size, aspect_ratio, image_size_base
                        )] = page

                    for page in pages:
                        yield {
                            "event": "progress",
                            "data": {
                                "index": page["index"],
                                "status": "generating",
                                "current": len(generated_images) + 1,
                                "total": total,
                                "phase": "batch"
                            }
                        }

                    for future in as_completed(future_to_page):
                        page = future_to_page[future]
                        try:
                            index, success, filename, error = future.result()
                            phase = "cover" if (page.get("type") == "cover" or page == cover_page) else "content"
                            if success:
                                generated_images.append(filename)
                                self._task_states[task_id]["generated"][index] = filename
                                yield {
                                    "event": "complete",
                                    "data": {
                                        "index": index,
                                        "status": "done",
                                        "image_url": f"/api/images/{task_id}/{filename}",
                                        "phase": phase
                                    }
                                }
                            else:
                                failed_pages.append(page)
                                self._task_states[task_id]["failed"][index] = error
                                yield {
                                    "event": "error",
                                    "data": {
                                        "index": index,
                                        "status": "error",
                                        "message": error,
                                        "retryable": True,
                                        "phase": phase
                                    }
                                }
                        except Exception as e:
                            failed_pages.append(page)
                            error_msg = str(e)
                            self._task_states[task_id]["failed"][page["index"]] = error_msg
                            yield {
                                "event": "error",
                                "data": {
                                    "index": page["index"],
                                    "status": "error",
                                    "message": error_msg,
                                    "retryable": True,
                                    "phase": "content"
                                }
                            }
            else:
                # 顺序模式（低并发）：逐个生成所有页面
                for page in pages:
                    phase = "cover" if (page.get("type") == "cover" or (cover_page and page == cover_page)) else "content"
                    yield {
                        "event": "progress",
                        "data": {
                            "index": page["index"],
                            "status": "generating",
                            "message": "正在生成封面..." if phase == "cover" else f"正在生成第 {page['index'] + 1} 页...",
                            "current": len(generated_images) + 1,
                            "total": total,
                            "phase": phase
                        }
                    }
                    if seq_ref_enabled:
                        per_page_user_images = [compressed_user_images[page["index"]]]
                    else:
                        per_page_user_images = compressed_user_images
                    index, success, filename, error = self._generate_single_image(
                        page, task_id, None, 0, full_outline,
                        per_page_user_images, user_topic,
                        image_size, aspect_ratio, image_size_base
                    )
                    if success:
                        generated_images.append(filename)
                        self._task_states[task_id]["generated"][index] = filename
                        yield {
                            "event": "complete",
                            "data": {
                                "index": index,
                                "status": "done",
                                "image_url": f"/api/images/{task_id}/{filename}",
                                "phase": phase
                            }
                        }
                    else:
                        failed_pages.append(page)
                        self._task_states[task_id]["failed"][index] = error
                        yield {
                            "event": "error",
                            "data": {
                                "index": index,
                                "status": "error",
                                "message": error,
                                "retryable": True,
                                "phase": phase
                            }
                        }

        else:
            # ============ 封面优先模式：无用户参考图时保持原逻辑 ============
            # 没有用户参考图时，封面是唯一的风格参考来源，仍需先串行生成
            cover_page = None
            other_pages = []
            for page in pages:
                if page["type"] == "cover":
                    cover_page = page
                else:
                    other_pages.append(page)
            if cover_page is None and len(pages) > 0:
                cover_page = pages[0]
                other_pages = pages[1:]

            if cover_page:
                yield {
                    "event": "progress",
                    "data": {
                        "index": cover_page["index"],
                        "status": "generating",
                        "message": "正在生成封面...",
                        "current": 1,
                        "total": total,
                        "phase": "cover"
                    }
                }
                index, success, filename, error = self._generate_single_image(
                    cover_page, task_id, reference_image=None, full_outline=full_outline,
                    user_images=None, user_topic=user_topic,
                    image_size=image_size, aspect_ratio=aspect_ratio,
                    image_size_base=image_size_base
                )
                if success:
                    generated_images.append(filename)
                    self._task_states[task_id]["generated"][index] = filename
                    cover_path = os.path.join(self.current_task_dir, filename)
                    with open(cover_path, "rb") as f:
                        cover_image_data = f.read()
                    cover_image_data = compress_image(cover_image_data, max_size_kb=200)
                    self._task_states[task_id]["cover_image"] = cover_image_data
                    yield {
                        "event": "complete",
                        "data": {
                            "index": index,
                            "status": "done",
                            "image_url": f"/api/images/{task_id}/{filename}",
                            "phase": "cover"
                        }
                    }
                else:
                    failed_pages.append(cover_page)
                    self._task_states[task_id]["failed"][index] = error
                    yield {
                        "event": "error",
                        "data": {
                            "index": index,
                            "status": "error",
                            "message": error,
                            "retryable": True,
                            "phase": "cover"
                        }
                    }

            if other_pages:
                high_concurrency = self.provider_config.get('high_concurrency', False)
                if high_concurrency:
                    yield {
                        "event": "progress",
                        "data": {
                            "status": "batch_start",
                            "message": f"开始并发生成 {len(other_pages)} 页内容...",
                            "current": len(generated_images),
                            "total": total,
                            "phase": "content"
                        }
                    }
                    with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
                        future_to_page = {
                            executor.submit(
                                self._generate_single_image,
                                page, task_id, cover_image_data, 0,
                                full_outline, None, user_topic,
                                image_size, aspect_ratio, image_size_base
                            ): page
                            for page in other_pages
                        }
                        for page in other_pages:
                            yield {
                                "event": "progress",
                                "data": {
                                    "index": page["index"],
                                    "status": "generating",
                                    "current": len(generated_images) + 1,
                                    "total": total,
                                    "phase": "content"
                                }
                            }
                        for future in as_completed(future_to_page):
                            page = future_to_page[future]
                            try:
                                index, success, filename, error = future.result()
                                if success:
                                    generated_images.append(filename)
                                    self._task_states[task_id]["generated"][index] = filename
                                    yield {
                                        "event": "complete",
                                        "data": {
                                            "index": index,
                                            "status": "done",
                                            "image_url": f"/api/images/{task_id}/{filename}",
                                            "phase": "content"
                                        }
                                    }
                                else:
                                    failed_pages.append(page)
                                    self._task_states[task_id]["failed"][index] = error
                                    yield {
                                        "event": "error",
                                        "data": {
                                            "index": index,
                                            "status": "error",
                                            "message": error,
                                            "retryable": True,
                                            "phase": "content"
                                        }
                                    }
                            except Exception as e:
                                failed_pages.append(page)
                                error_msg = str(e)
                                self._task_states[task_id]["failed"][page["index"]] = error_msg
                                yield {
                                    "event": "error",
                                    "data": {
                                        "index": page["index"],
                                        "status": "error",
                                        "message": error_msg,
                                        "retryable": True,
                                        "phase": "content"
                                    }
                                }
                else:
                    for page in other_pages:
                        yield {
                            "event": "progress",
                            "data": {
                                "index": page["index"],
                                "status": "generating",
                                "current": len(generated_images) + 1,
                                "total": total,
                                "phase": "content"
                            }
                        }
                        index, success, filename, error = self._generate_single_image(
                            page, task_id, cover_image_data, 0,
                            full_outline, None, user_topic,
                            image_size, aspect_ratio, image_size_base
                        )
                        if success:
                            generated_images.append(filename)
                            self._task_states[task_id]["generated"][index] = filename
                            yield {
                                "event": "complete",
                                "data": {
                                    "index": index,
                                    "status": "done",
                                    "image_url": f"/api/images/{task_id}/{filename}",
                                    "phase": "content"
                                }
                            }
                        else:
                            failed_pages.append(page)
                            self._task_states[task_id]["failed"][index] = error
                            yield {
                                "event": "error",
                                "data": {
                                    "index": index,
                                    "status": "error",
                                    "message": error,
                                    "retryable": True,
                                    "phase": "content"
                                }
                            }

        # ==================== 完成 ====================
        yield {
            "event": "finish",
            "data": {
                "success": len(failed_pages) == 0,
                "task_id": task_id,
                "images": generated_images,
                "total": total,
                "completed": len(generated_images),
                "failed": len(failed_pages),
                "failed_indices": [p["index"] for p in failed_pages]
            }
        }

    def retry_single_image(
        self,
        task_id: str,
        page: Dict,
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = "",
        image_size: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        image_size_base: Optional[str] = None,
        sequential_reference: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        重试生成单张图片

        Args:
            task_id: 任务ID
            page: 页面数据
            use_reference: 是否使用封面作为参考
            full_outline: 完整大纲文本（从前端传入）
            user_topic: 用户原始输入（从前端传入）
            sequential_reference: 依次参考开关；为 None 时沿用任务状态中保存的值

        Returns:
            生成结果
        """
        self.current_task_dir = os.path.join(self.history_root_dir, task_id)
        os.makedirs(self.current_task_dir, exist_ok=True)

        reference_image = None
        user_images = None
        # 从任务状态中读取分辨率和宽高比（重试时复用首次生成的设置）
        task_image_size = None
        task_aspect_ratio = None
        task_image_size_base = None
        seq_ref_enabled = False

        # 首先尝试从任务状态中获取上下文
        if task_id in self._task_states:
            task_state = self._task_states[task_id]
            if use_reference:
                reference_image = task_state.get("cover_image")
            # 如果没有传入上下文，则使用任务状态中的
            if not full_outline:
                full_outline = task_state.get("full_outline", "")
            if not user_topic:
                user_topic = task_state.get("user_topic", "")
            user_images = task_state.get("user_images")
            task_image_size = task_state.get("image_size")
            task_aspect_ratio = task_state.get("aspect_ratio")
            task_image_size_base = task_state.get("image_size_base")
            seq_ref_enabled = bool(task_state.get("sequential_reference", False))

        # 显式传入的开关值覆盖任务状态；再次校验条件
        if sequential_reference is not None:
            seq_ref_enabled = bool(sequential_reference)
        if seq_ref_enabled:
            total_pages = None
            if task_id in self._task_states:
                total_pages = self._task_states[task_id].get("total_pages")
            if not user_images or total_pages is None or len(user_images) != total_pages:
                seq_ref_enabled = False

        # 调用方传入的优先，其次任务状态中的
        effective_size = image_size if image_size else task_image_size
        effective_aspect = aspect_ratio if aspect_ratio else task_aspect_ratio
        effective_size_base = image_size_base if image_size_base else task_image_size_base

        # 依次参考模式下不再叠加封面；仅在关闭时才拉取封面
        if seq_ref_enabled:
            reference_image = None

        # 如果任务状态中没有封面图，尝试从文件系统加载（依次参考模式跳过）
        if use_reference and reference_image is None and not seq_ref_enabled:
            cover_path = os.path.join(self.current_task_dir, "0.png")
            if os.path.exists(cover_path):
                with open(cover_path, "rb") as f:
                    cover_data = f.read()
                # 压缩封面图到 200KB
                reference_image = compress_image(cover_data, max_size_kb=200)

        # 「依次参考」开启时：只把该页对应的那张用户图作为参考
        effective_user_images = user_images
        if seq_ref_enabled and user_images:
            page_index = page.get("index", 0)
            if 0 <= page_index < len(user_images):
                effective_user_images = [user_images[page_index]]
            else:
                logger.warning(f"依次参考：页面索引 {page_index} 越界，回退到全部参考图")

        index, success, filename, error = self._generate_single_image(
            page,
            task_id,
            reference_image,
            0,
            full_outline,
            effective_user_images,
            user_topic,
            effective_size,
            effective_aspect,
            effective_size_base
        )

        if success:
            if task_id in self._task_states:
                self._task_states[task_id]["generated"][index] = filename
                if index in self._task_states[task_id]["failed"]:
                    del self._task_states[task_id]["failed"][index]

            return {
                "success": True,
                "index": index,
                "image_url": f"/api/images/{task_id}/{filename}"
            }
        else:
            return {
                "success": False,
                "index": index,
                "error": error,
                "retryable": True
            }

    def retry_failed_images(
        self,
        task_id: str,
        pages: List[Dict]
    ) -> Generator[Dict[str, Any], None, None]:
        """
        批量重试失败的图片

        Args:
            task_id: 任务ID
            pages: 需要重试的页面列表

        Yields:
            进度事件
        """
        # 获取参考图
        reference_image = None
        seq_ref_enabled = False
        task_user_images: Optional[List[bytes]] = None
        task_total_pages: Optional[int] = None
        if task_id in self._task_states:
            reference_image = self._task_states[task_id].get("cover_image")
            seq_ref_enabled = bool(self._task_states[task_id].get("sequential_reference", False))
            task_user_images = self._task_states[task_id].get("user_images")
            task_total_pages = self._task_states[task_id].get("total_pages")

        # 依次参考模式下：不再用封面做参考，并要求 user_images 数量与总页数一致
        if seq_ref_enabled:
            if not task_user_images or task_total_pages is None or len(task_user_images) != task_total_pages:
                logger.warning("批量重试：依次参考条件不满足，回退到常规参考图逻辑")
                seq_ref_enabled = False
            else:
                reference_image = None

        total = len(pages)
        success_count = 0
        failed_count = 0

        yield {
            "event": "retry_start",
            "data": {
                "total": total,
                "message": f"开始重试 {total} 张失败的图片"
            }
        }

        # 并发重试
        # 从任务状态中获取完整大纲
        full_outline = ""
        image_size = None
        aspect_ratio = None
        image_size_base = None
        if task_id in self._task_states:
            full_outline = self._task_states[task_id].get("full_outline", "")
            image_size = self._task_states[task_id].get("image_size")
            aspect_ratio = self._task_states[task_id].get("aspect_ratio")
            image_size_base = self._task_states[task_id].get("image_size_base")

        with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
            def _submit(page):
                if seq_ref_enabled and task_user_images:
                    idx = page.get("index", 0)
                    per_page_images = (
                        [task_user_images[idx]]
                        if 0 <= idx < len(task_user_images)
                        else None
                    )
                else:
                    per_page_images = None  # 保持既有行为：批量重试不再合并用户图
                return executor.submit(
                    self._generate_single_image,
                    page,
                    task_id,
                    reference_image,
                    0,  # retry_count
                    full_outline,  # 传入完整大纲
                    per_page_images,
                    "",    # user_topic
                    image_size,
                    aspect_ratio,
                    image_size_base
                )

            future_to_page = {_submit(page): page for page in pages}

            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    index, success, filename, error = future.result()

                    if success:
                        success_count += 1
                        if task_id in self._task_states:
                            self._task_states[task_id]["generated"][index] = filename
                            if index in self._task_states[task_id]["failed"]:
                                del self._task_states[task_id]["failed"][index]

                        yield {
                            "event": "complete",
                            "data": {
                                "index": index,
                                "status": "done",
                                "image_url": f"/api/images/{task_id}/{filename}"
                            }
                        }
                    else:
                        failed_count += 1
                        yield {
                            "event": "error",
                            "data": {
                                "index": index,
                                "status": "error",
                                "message": error,
                                "retryable": True
                            }
                        }

                except Exception as e:
                    failed_count += 1
                    yield {
                        "event": "error",
                        "data": {
                            "index": page["index"],
                            "status": "error",
                            "message": str(e),
                            "retryable": True
                        }
                    }

        yield {
            "event": "retry_finish",
            "data": {
                "success": failed_count == 0,
                "total": total,
                "completed": success_count,
                "failed": failed_count
            }
        }

    def regenerate_image(
        self,
        task_id: str,
        page: Dict,
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = "",
        image_size: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        image_size_base: Optional[str] = None,
        sequential_reference: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        重新生成图片（用户手动触发，即使成功的也可以重新生成）

        Args:
            task_id: 任务ID
            page: 页面数据
            use_reference: 是否使用封面作为参考
            full_outline: 完整大纲文本
            user_topic: 用户原始输入

        Returns:
            生成结果
        """
        return self.retry_single_image(
            task_id, page, use_reference,
            full_outline=full_outline,
            user_topic=user_topic,
            image_size=image_size,
            aspect_ratio=aspect_ratio,
            image_size_base=image_size_base,
            sequential_reference=sequential_reference
        )

    def get_image_path(self, task_id: str, filename: str) -> str:
        """
        获取图片完整路径

        Args:
            task_id: 任务ID
            filename: 文件名

        Returns:
            完整路径
        """
        task_dir = os.path.join(self.history_root_dir, task_id)
        return os.path.join(task_dir, filename)

    def get_task_state(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self._task_states.get(task_id)

    def cleanup_task(self, task_id: str):
        """清理任务状态（释放内存）"""
        if task_id in self._task_states:
            del self._task_states[task_id]


# 全局服务实例
_service_instance = None

def get_image_service() -> ImageService:
    """获取全局图片生成服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ImageService()
    return _service_instance

def reset_image_service():
    """重置全局服务实例（配置更新后调用）"""
    global _service_instance
    _service_instance = None
