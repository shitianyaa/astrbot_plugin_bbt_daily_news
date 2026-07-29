"""日报 T2I 渲染参数。"""

from typing import Any


# 日报模板的 body 内容宽 600px，左右各有 20px 内边距，因此完整可见画布为 640px。
REPORT_VIEWPORT_WIDTH = 640

# astrbot-t2i-service 文档规定的默认视口高度。其当前实现只有在宽高同时传入时
# 才应用自定义视口；显式传入该服务默认值可避免回退至 1280px 的默认画布。
T2I_DEFAULT_VIEWPORT_HEIGHT = 720


def build_report_render_options(jpeg_quality: int) -> dict[str, Any]:
    """构造日报 T2I 参数，确保服务按模板实际画布截图。

    ``type`` 与 ``full_page`` 显式沿用 AstrBot ``html_render`` 的默认值，使 JPEG
    质量参数在直连 T2I 服务时同样有效，并保留完整日报的自然高度。
    """
    return {
        "full_page": True,
        "type": "jpeg",
        "quality": jpeg_quality,
        "device_scale_factor_level": "normal",
        "viewport_width": REPORT_VIEWPORT_WIDTH,
        "viewport_height": T2I_DEFAULT_VIEWPORT_HEIGHT,
    }
