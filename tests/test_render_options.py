"""日报 T2I 画布参数的无依赖回归测试。"""

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "render_options.py"
SPEC = importlib.util.spec_from_file_location("render_options", MODULE_PATH)
render_options = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(render_options)


class RenderOptionsTests(unittest.TestCase):
    """确保 T2I 服务收到能够实际生效的成对视口尺寸。"""

    def test_build_report_render_options_uses_template_canvas(self):
        options = render_options.build_report_render_options(86)

        self.assertTrue(options["full_page"])
        self.assertEqual(options["type"], "jpeg")
        self.assertEqual(options["quality"], 86)
        self.assertEqual(options["device_scale_factor_level"], "normal")
        self.assertEqual(options["viewport_width"], 640)
        self.assertEqual(options["viewport_height"], 720)
