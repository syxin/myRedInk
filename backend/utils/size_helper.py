"""图像尺寸归一化工具。

前端可能传几种格式：
- "1024x768" / "2400x3200" —— 已经是具体像素串，直接使用
- "1K" / "2K" / "4K" —— 档位名，需要结合宽高比换算成像素串
- None / 空串 —— 表示使用默认值

所有生图 generator 期望 `size` 字段为 "WxH" 形式的像素串，
本工具负责把上述任意输入归一化为像素串。
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 档位名 -> 长边像素，跟前端 ComposerInput.vue 的 baseSizePixelMap 保持一致
_BASE_PIXEL_MAP = {
    "1K": 1024,
    "2K": 2048,
    "4K": 3200,
}

# 形如 "1024x768"、"1024X768" 都接受
_PIXEL_PATTERN = re.compile(r"^\s*(\d{3,5})\s*[xX×]\s*(\d{3,5})\s*$")
# 形如 "3:4"、"16:9"
_RATIO_PATTERN = re.compile(r"^\s*(\d{1,3})\s*:\s*(\d{1,3})\s*$")

# 默认值
DEFAULT_BASE = "2K"
DEFAULT_ASPECT_RATIO = "3:4"


def parse_aspect_ratio(aspect_ratio: Optional[str]) -> Optional[tuple]:
    """将 "3:4" 这样的字符串解析为 (3, 4)，无效返回 None"""
    if not aspect_ratio:
        return None
    m = _RATIO_PATTERN.match(aspect_ratio)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def compute_pixel_size(
    image_size: Optional[str],
    aspect_ratio: Optional[str] = None,
    *,
    default_base: str = DEFAULT_BASE,
    default_aspect_ratio: str = DEFAULT_ASPECT_RATIO,
) -> str:
    """
    将任意形式的 image_size / aspect_ratio 归一化为 "WxH" 像素串。

    Args:
        image_size: "1K"/"2K"/"4K" 档位、"1024x768" 像素串，或 None
        aspect_ratio: 宽高比字符串，仅在 image_size 是档位名或 None 时生效
        default_base: 当 image_size 为 None / 不合法时使用的档位
        default_aspect_ratio: 当 aspect_ratio 为 None / 不合法时使用的比例

    Returns:
        像素串，例如 "2048x1536"。永远返回非空字符串。
    """
    # 1) 已经是像素串：直接返回
    if image_size:
        m = _PIXEL_PATTERN.match(image_size)
        if m:
            return f"{int(m.group(1))}x{int(m.group(2))}"

    # 2) 档位 + 比例：按"长边对齐基准"换算
    base_key = (image_size or "").upper() if image_size else ""
    if base_key not in _BASE_PIXEL_MAP:
        base_key = default_base.upper()

    ratio = parse_aspect_ratio(aspect_ratio) or parse_aspect_ratio(default_aspect_ratio)
    if ratio is None:
        # 极端兜底
        ratio = (3, 4)

    long_edge = _BASE_PIXEL_MAP.get(base_key, _BASE_PIXEL_MAP[default_base.upper()])
    w_r, h_r = ratio

    if w_r >= h_r:
        # 横图或正方形：宽是长边
        width = long_edge
        height = round(long_edge * h_r / w_r)
    else:
        # 竖图：高是长边
        height = long_edge
        width = round(long_edge * w_r / h_r)

    pixel_str = f"{int(width)}x{int(height)}"
    logger.debug(
        f"尺寸归一化: image_size={image_size!r} + aspect_ratio={aspect_ratio!r} "
        f"-> base={base_key}, ratio={ratio}, pixel={pixel_str}"
    )
    return pixel_str
