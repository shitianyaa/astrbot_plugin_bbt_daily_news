"""报告渲染器：模板加载、缓存管理、数据聚合、HTML渲染"""

import datetime
import os
from typing import Any, Callable, Dict, List

from astrbot.api import logger

from .cache import CacheEntry
from .config import PluginConfig
from .constants import TEMPLATE_FILES
from .fetchers import DataFetcherManager
from .render_options import build_report_render_options


def sanitize_for_log(value: Any, max_len: int = 64) -> Any:
    """递归截断日志数据中的长字符串，base64 图片数据以占位符表示，避免日志刷屏"""
    if isinstance(value, str):
        if value.startswith(("data:", "base64://")):
            return f"<图片数据: {len(value)} 字符>"
        if len(value) > max_len:
            return f"{value[:max_len]}...<{len(value)} 字符>"
        return value
    if isinstance(value, dict):
        return {k: sanitize_for_log(v, max_len) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_for_log(v, max_len) for v in value]
    return value


def summarize_context_data(data: Dict[str, Any]) -> str:
    """渲染数据的单行摘要：只输出条目数与成功/失败标志，不打印具体内容。

    封面图等 base64 数据都在列表字段内部，按计数输出后不会进入日志。
    """
    parts = []
    for key, value in data.items():
        if isinstance(value, list):
            parts.append(f"{key}={len(value)}")
        elif isinstance(value, dict):
            parts.append(f"{key}={'error' if value.get('error') else 'ok'}")
        elif isinstance(value, str) and len(value) > 24:
            parts.append(f"{key}=<长文本>")
        else:
            parts.append(f"{key}={value}")
    return " ".join(parts)


class ReportRenderer:
    """报告渲染器，负责模板加载、缓存管理和HTML渲染"""

    def __init__(
        self,
        config: PluginConfig,
        fetcher_manager: DataFetcherManager,
        render_func: Callable,
        cache: dict,
    ):
        self.config = config
        self.fetcher_manager = fetcher_manager
        self.render_func = render_func
        self.cache = cache
        self.html_templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """加载所有HTML模板文件"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        templates = {}
        for name, filename in TEMPLATE_FILES.items():
            template_path = os.path.join(current_dir, "templates", filename)
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    templates[name] = f.read()
                logger.info(f"棒棒糖的每日晨报：成功加载模板: {template_path}")
            except FileNotFoundError:
                logger.error(f"棒棒糖的每日晨报：未找到模板文件: {template_path}")
                templates[name] = "<h1>Template Not Found</h1>"
        return templates

    async def generate(self) -> List[str]:
        """
        聚合数据并渲染HTML，使用缓存机制

        Returns:
            image_paths: 渲染产出的临时图片文件路径列表
        """
        # 尝试从缓存获取常规数据
        cache_key = "daily_report_data"
        cached_entry = self.cache.get(cache_key)

        if cached_entry and not cached_entry.is_expired(self.config.cache_ttl_minutes):
            logger.info("棒棒糖的每日晨报：使用缓存数据生成HTML")
            results_dict = cached_entry.data
        else:
            logger.info("棒棒糖的每日晨报：缓存未命中或已过期，开始获取最新数据")
            results_dict = await self.fetcher_manager.fetch_all_data()
            # 将结果存入缓存
            self.cache[cache_key] = CacheEntry(
                data=results_dict, timestamp=datetime.datetime.now()
            )
            logger.info("棒棒糖的每日晨报：数据已存入缓存")

        # DMM数据单独获取（不放入缓存）
        dmm_top_list = await self.fetcher_manager.fetch_dmm_data()

        # 整理 AI 余额数据
        ai_balances = {
            "OpenRouter": results_dict["openrouter_credits"],
            "DeepSeek": results_dict["deepseek_balance"],
            "MoonShot": results_dict["moonshot_balance"],
            "SiliconFlow": results_dict["siliconflow_balance"],
        }
        show_adult = "1" if self.config.r18_mode else "0"

        # 整理常规数据
        context_data = {
            "animation_mode": "1" if self.config.animation_mode else "0",
            "movie_mode": "1" if self.config.movie_mode else "0",
            "dram_mode": "1" if self.config.dram_mode else "0",
            "r18_mode": show_adult,
            "fuel_mode": "1" if self.config.fuel_mode else "0",
            "gold_mode": "1" if self.config.gold_mode else "0",
            "date": datetime.datetime.now().strftime("%Y-%m-%d %A"),
            "news_60s": results_dict["news_60s"].get("news", []) if isinstance(results_dict["news_60s"], dict) else [],
            "news_ithome": results_dict["ithome_news"],
            "dram_prices": results_dict["dram_price"],
            "bangumi_list": results_dict["bangumi_today"],
            "ai_balances": ai_balances,
            "dmm_top_list": dmm_top_list,
            "toutiao_hot": results_dict["toutiao_hot"],
            "weibo_hot": results_dict["weibo_hot"],
            "exchange_rates": results_dict["exchange_rates"],
            "movie_list": results_dict["douban_movies"],
            "game_list": results_dict["rawg_games"],
            "fuel_price": results_dict["fuel_price"],
            "gold_price": results_dict["gold_price"],
        }
        logger.info(f"棒棒糖的每日晨报：渲染数据概况: {summarize_context_data(context_data)}")
        logger.debug(f"棒棒糖的每日晨报：渲染数据: {sanitize_for_log(context_data)}")

        # 服务端仅在宽高同时指定时才会应用自定义视口，避免回退到 1280px 默认画布。
        options = build_report_render_options(
            self.config.report_jpeg_quality,
            self.config.device_scale_factor_level,
        )
        image_paths = []

        # 渲染主报告（return_url=False 返回临时文件路径，避免把图片 URL/base64 暴露到日志）
        try:
            main_path = await self.render_func(
                self.html_templates["main"], context_data, return_url=False, options=options
            )
            image_paths.append(main_path)
            logger.info("棒棒糖的每日晨报：主报告 HTML 生成完成")
        except Exception as e:
            logger.error(f"棒棒糖的每日晨报：主报告渲染失败: {e}", exc_info=True)

        # 渲染动画子报告
        if self.config.animation_mode:
            try:
                anim_path = await self.render_func(
                    self.html_templates["animation"], context_data, return_url=False, options=options
                )
                image_paths.append(anim_path)
                logger.info("棒棒糖的每日晨报：动画报告 HTML 生成完成")
            except Exception as e:
                logger.error(f"棒棒糖的每日晨报：动画报告渲染失败: {e}", exc_info=True)

        # 渲染电影子报告
        if self.config.movie_mode:
            try:
                movie_path = await self.render_func(
                    self.html_templates["movie"], context_data, return_url=False, options=options
                )
                image_paths.append(movie_path)
                logger.info("棒棒糖的每日晨报：电影报告 HTML 生成完成")
            except Exception as e:
                logger.error(f"棒棒糖的每日晨报：电影报告渲染失败: {e}", exc_info=True)

        # 渲染DMM子报告
        if self.config.r18_mode:
            try:
                dmm_path = await self.render_func(
                    self.html_templates["dmm"], context_data, return_url=False, options=options
                )
                image_paths.append(dmm_path)
                logger.info("棒棒糖的每日晨报：DMM报告 HTML 生成完成")
            except Exception as e:
                logger.error(f"棒棒糖的每日晨报：DMM报告渲染失败: {e}", exc_info=True)

        logger.info(f"棒棒糖的每日晨报：全部 HTML 生成完成，共 {len(image_paths)} 张图片")
        return image_paths
