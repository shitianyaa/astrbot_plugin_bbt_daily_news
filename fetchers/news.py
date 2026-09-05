"""新闻和热榜数据抓取：60秒读懂世界、IT之家热榜、微博热榜、今日头条热榜"""

import asyncio
import datetime
from typing import Dict, List

import aiohttp
from bs4 import BeautifulSoup

from astrbot.api import logger

from ..constants import (
    USER_AGENT,
    NEWS_60S_API_URLS,
    NEWS_60S_STATIC_URL,
    ITHOME_RANK_URL,
)
from ..config import PluginConfig


async def _fetch_news_list(session, url: str) -> List[str]:
    """请求单个60s源并提取新闻字符串列表，格式异常或无数据时抛出"""
    async with session.get(url) as resp:
        if resp.status != 200:
            raise aiohttp.ClientResponseError(
                resp.request_info, resp.history, status=resp.status, message=str(resp.status)
            )
        # content_type=None 兼容 jsDelivr 静态源的响应头
        data = await resp.json(content_type=None)

    # v2 实例格式为 data.news，静态托管为顶层 news
    news = data.get("data", {}).get("news") or data.get("news") or []
    if not isinstance(news, list) or not news:
        raise ValueError("响应中无新闻数据")
    return [str(item) for item in news]


async def fetch_60s_news(session, semaphore: asyncio.Semaphore) -> Dict:
    """获取60秒读懂世界：依次尝试社区实例，全部失败后回退 jsDelivr 静态源"""
    try:
        async with semaphore:  # 限制并发
            for url in NEWS_60S_API_URLS:
                try:
                    news = await _fetch_news_list(session, url)
                    return {"news": news}
                except Exception as e:
                    logger.warning(f"棒棒糖的每日晨报：60s实例源 {url} 获取失败: {e}")

            # 静态兜底：当日文件未发布时回退昨日数据
            today = datetime.date.today()
            for date in (today, today - datetime.timedelta(days=1)):
                url = NEWS_60S_STATIC_URL.format(date.isoformat())
                try:
                    news = await _fetch_news_list(session, url)
                    if date != today:
                        logger.warning(f"棒棒糖的每日晨报：60s当日静态数据未发布，已回退至 {date} 数据")
                    return {"news": news}
                except Exception as e:
                    logger.warning(f"棒棒糖的每日晨报：60s静态源 {url} 获取失败: {e}")
    except asyncio.TimeoutError:
        logger.error("棒棒糖的每日晨报：获取60秒新闻超时")
        return {"news": ["获取失败 - 请求超时"]}
    except aiohttp.ClientError as e:
        logger.error(f"棒棒糖的每日晨报：获取60秒新闻网络错误: {e}")
        return {"news": ["获取失败 - 网络错误"]}
    except Exception as e:
        logger.error(f"棒棒糖的每日晨报：获取60秒新闻失败: {e}")

    logger.warning("棒棒糖的每日晨报：60s全部数据源均获取失败")
    return {"news": ["获取失败"]}


async def fetch_ithome_news(session, semaphore: asyncio.Semaphore, config: PluginConfig) -> List[str]:
    """抓取IT之家热榜"""
    if not config.ithome_mode:
        return []

    headers = {
        "User-Agent": USER_AGENT
    }
    news_list = []
    try:
        async with semaphore:  # 限制并发
            async with session.get(ITHOME_RANK_URL, headers=headers) as resp:
                text = await resp.text()
                soup = BeautifulSoup(text, 'lxml')

                # 日榜在 id="d-1" 的 ul 标签下
                daily_list = soup.select_one("ul#d-1")

                if daily_list:
                    links = daily_list.select("li a")

                    for link in links:
                        title = link.get_text(strip=True)
                        if title:
                            news_list.append(title)
                else:
                    logger.warning("棒棒糖的每日晨报：未找到IT之家热榜容器(ul#d-1)")

    except asyncio.TimeoutError:
        logger.error("棒棒糖的每日晨报：获取IT之家热榜超时")
        news_list.append("获取失败 - 请求超时")
    except aiohttp.ClientError as e:
        logger.error(f"棒棒糖的每日晨报：获取IT之家热榜网络错误: {e}")
        news_list.append("获取失败 - 网络错误")
    except Exception as e:
        logger.error(f"棒棒糖的每日晨报：抓取IT之家热榜失败: {e}")
        news_list.append("获取失败 - 未知错误")

    # 返回前 10 条，避免太长
    return news_list[:10]


async def fetch_weibo_hot(session, semaphore: asyncio.Semaphore, config: PluginConfig) -> List[str]:
    """获取微博热榜"""
    if not config.yuafeng_key:
        return []

    results = []
    url = "https://api-v2.yuafeng.cn/API/jinri_hot.php"
    params = {
        'apikey': config.yuafeng_key,
        'action': '微博热榜',
        'page': '1',
    }
    try:
        async with semaphore:  # 限制并发
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    info = data.get("data", [])
                    for item in info:
                        results.append(item["title"])
                    return results
                else:
                    logger.warning(f"棒棒糖的每日晨报：获取微博热榜API返回非200状态码: {resp.status}")
                    return []

    except asyncio.TimeoutError:
        logger.error("棒棒糖的每日晨报：获取微博热榜超时")
    except aiohttp.ClientError as e:
        logger.error(f"棒棒糖的每日晨报：获取微博热榜网络错误: {e}")
    except Exception as e:
        logger.error(f"棒棒糖的每日晨报：获取微博热榜失败: {e}")
    return []


async def fetch_toutiao_hot(session, semaphore: asyncio.Semaphore, config: PluginConfig) -> List[str]:
    """获取今日头条热榜"""
    if not config.yuafeng_key:
        return []

    results = []
    url = "https://api-v2.yuafeng.cn/API/jinri_hot.php"
    params = {
        'apikey': config.yuafeng_key,
        'action': '今日头条热榜',
        'page': '1',
    }
    try:
        async with semaphore:  # 限制并发
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    info = data.get("data", [])
                    for item in info:
                        results.append(item["title"])
                    return results
                else:
                    logger.warning(f"棒棒糖的每日晨报：获取今日头条热榜API返回非200状态码: {resp.status}")
                    return []
    except asyncio.TimeoutError:
        logger.error("棒棒糖的每日晨报：获取今日头条热榜超时")
    except aiohttp.ClientError as e:
        logger.error(f"棒棒糖的每日晨报：获取今日头条热榜网络错误: {e}")
    except Exception as e:
        logger.error(f"棒棒糖的每日晨报：获取今日头条热榜失败: {e}")
    return []
