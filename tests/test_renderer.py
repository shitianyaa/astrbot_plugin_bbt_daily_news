"""渲染器日志脱敏与文件路径渲染管线的单元测试（无需网络）"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT.parent))

from astrbot_plugin_bbt_daily_news.config import PluginConfig  # noqa: E402
from astrbot_plugin_bbt_daily_news.renderer import (  # noqa: E402
    ReportRenderer,
    sanitize_for_log,
    summarize_context_data,
)


def test_sanitize_for_log_masks_base64_and_long_strings():
    value = {
        "cover": "data:image/png;base64," + "A" * 500,
        "news": ["短新闻", "x" * 200],
        "nested": {"file": "base64://abcdef"},
        "plain": 42,
    }
    result = sanitize_for_log(value)
    assert result["cover"].startswith("<图片数据: ")
    assert "A" * 20 not in result["cover"]
    assert result["news"][0] == "短新闻"
    assert result["news"][1].endswith("字符>")
    assert result["nested"]["file"].startswith("<图片数据: ")
    assert result["plain"] == 42


def test_summarize_context_data_hides_content_and_base64():
    data = {
        "news_60s": ["新闻一", "新闻二"],
        "game_list": [
            {"cover": "data:image/png;base64," + "A" * 2000, "title": "t"}
        ],
        "fuel_price": {"error": None, "province": "北京"},
        "exchange_rates": {"error": "API请求失败"},
        "date": "2026-09-05 Saturday",
        "animation_mode": "1",
        "long_text": "x" * 40,
    }
    summary = summarize_context_data(data)
    assert "news_60s=2" in summary
    assert "game_list=1" in summary
    assert "fuel_price=ok" in summary
    assert "exchange_rates=error" in summary
    assert "animation_mode=1" in summary
    assert "date=2026-09-05 Saturday" in summary
    # 具体内容与 base64 一律不进摘要
    assert "base64" not in summary
    assert "新闻一" not in summary
    assert "北京" not in summary
    assert "x" * 40 not in summary
    assert "<长文本>" in summary


def test_generate_renders_via_file_path_pipeline():
    """generate() 必须以 return_url=False 调用渲染函数，产出临时文件路径。

    html_render 的默认值是 return_url=True（返回 URL），若回归为 URL 模式，
    Image.fromFileSystem 会收到 https 字符串导致发送失败，因此这里显式加回归保护。
    """
    captured = {}

    async def fake_render(tmpl, data, return_url=True, options=None):
        captured["return_url"] = return_url
        return "/tmp/report_main.jpg"

    class StubFetcherManager:
        async def fetch_all_data(self):
            return {
                "news_60s": {"news": ["新闻"]},
                "ithome_news": [],
                "dram_price": [],
                "bangumi_today": [],
                "openrouter_credits": {},
                "deepseek_balance": {},
                "moonshot_balance": {},
                "siliconflow_balance": {},
                "toutiao_hot": [],
                "weibo_hot": [],
                "exchange_rates": {},
                "douban_movies": [],
                "rawg_games": [],
                "fuel_price": {},
                "gold_price": {},
            }

        async def fetch_dmm_data(self):
            return []

    renderer = ReportRenderer(
        config=PluginConfig.from_dict({}),
        fetcher_manager=StubFetcherManager(),
        render_func=fake_render,
        cache={},
    )
    paths = asyncio.run(renderer.generate())

    assert captured["return_url"] is False
    # 默认配置下动画/电影/R18 子报告全部关闭，仅渲染主报告
    assert paths == ["/tmp/report_main.jpg"]
