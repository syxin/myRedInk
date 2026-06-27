"""图像尺寸归一化工具。

前端可能传几种格式：
- "1024x768" / "2400x3200" —— 已经是具体像素串，直接使用（仍会做 16 倍数对齐）
- "1K" / "2K" / "4K" —— 档位名，需要结合宽高比换算成像素串
- None / 空串 —— 表示使用默认值

gpt-image 系列要求宽、高均为 16 的倍数，本工具统一在这里做对齐，
避免任何调用方都得自己处理 alignment。
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 档位名 -> 长边像素，跟前端 ComposerInput.vue 的 baseSizePixelMap 保持一致
# 注意：这里所有值已经是 16 的倍数，避免长边自身被对齐时再偏一格
_BASE_PIXEL_MAP = {
    "1K": 1024,   # 1024 / 16 = 64
    "2K": 2048,   # 2048 / 16 = 128
    "4K": 3200,   # 3200 / 16 = 200
}

# 形如 "1024x768"、"1024X768"、"1024×768" 都接受
_PIXEL_PATTERN = re.compile(r"^\s*(\d{3,5})\s*[xX×]\s*(\d{3,5})\s*$")
# 形如 "3:4"、"16:9"
_RATIO_PATTERN = re.compile(r"^\s*(\d{1,3})\s*:\s*(\d{1,3})\s*$")

# 默认值
DEFAULT_BASE = "2K"
DEFAULT_ASPECT_RATIO = "3:4"

# gpt-image / 主流扩散模型对宽高的对齐要求
# 16 是 gpt-image-2 的硬约束（错误码 invalid_size 即来自这里），
# 同时也兼容 64/32 倍数要求的模型
ALIGNMENT = 16

# 安全上下限（避免不小心传出极端值）
MIN_PIXEL = 256
MAX_PIXEL = 4096


def _align_to(value: int, step: int = ALIGNMENT) -> int:
    """把数值四舍五入到 step 的整数倍。"""
    aligned = round(value / step) * step
    if aligned < step:
        aligned = step
    return int(aligned)


def _clamp(value: int, lo: int = MIN_PIXEL, hi: int = MAX_PIXEL) -> int:
    return max(lo, min(hi, value))


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
    将任意形式的 image_size / aspect_ratio 归一化为 "WxH" 像素串，
    并保证宽高都是 16 的倍数（gpt-image 等模型的硬约束）。

    Args:
        image_size: "1K"/"2K"/"4K" 档位、"1024x768" 像素串，或 None
        aspect_ratio: 宽高比字符串，仅在 image_size 是档位名或 None 时生效
        default_base: 当 image_size 为 None / 不合法时使用的档位
        default_aspect_ratio: 当 aspect_ratio 为 None / 不合法时使用的比例

    Returns:
        像素串，例如 "2048x1536"，宽高均为 16 的倍数。
    """
    width: int
    height: int

    # 1) 已经是像素串：直接对齐返回
    if image_size:
        m = _PIXEL_PATTERN.match(image_size)
        if m:
            width = _clamp(_align_to(int(m.group(1))))
            height = _clamp(_align_to(int(m.group(2))))
            return f"{width}x{height}"

    # 2) 档位 + 比例：按"长边对齐基准"换算
    base_key = (image_size or "").upper() if image_size else ""
    if base_key not in _BASE_PIXEL_MAP:
        base_key = default_base.upper()

    ratio = parse_aspect_ratio(aspect_ratio) or parse_aspect_ratio(default_aspect_ratio)
    if ratio is None:
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

    # 两边都对齐到 16 的倍数，并钳到合理区间
    width = _clamp(_align_to(width))
    height = _clamp(_align_to(height))

    pixel_str = f"{width}x{height}"
    logger.debug(
        f"尺寸归一化: image_size={image_size!r} + aspect_ratio={aspect_ratio!r} "
        f"-> base={base_key}, ratio={ratio}, pixel={pixel_str}"
    )
    return pixel_str
