"""全局常量定义：URL、Headers、GraphQL查询等"""

# 通用 User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# DMM GraphQL 请求头
DMM_HEADERS = {
    "accept": "application/graphql-response+json, application/graphql+json, application/json, text/event-stream, multipart/mixed",
    "accept-language": "zh-CN",
    "content-type": "application/json",
    "fanza-device": "BROWSER",
    "origin": "https://video.dmm.co.jp",
    "referer": "https://video.dmm.co.jp/av/ranking/",
    "sec-ch-ua": '"Microsoft Edge";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# GraphQL 排名查询
RANKING_QUERY = """
query ContentRankingPage($limit: Int!, $offset: Int!, $filter: PPVContentRankingFilterInput, $isAmateur: Boolean = false) {
  ppvContentRanking(limit: $limit, offset: $offset, filter: $filter) {
    items {
      id
      rank
      content {
        title
        releaseStatus
        packageImage {
          mediumUrl
          largeUrl
          __typename
        }
        wishlistCount
        isExclusiveDelivery
        actresses @skip(if: $isAmateur) {
          id
          name
          __typename
        }
        sampleImages {
          number
          largeImageUrl
          __typename
        }
        hasSampleMovie
        review {
          average
          total
          __typename
        }
        __typename
      }
      __typename
    }
    ... on PPVContentTrendingRanking {
      targetWindowEndAt
      __typename
    }
    __typename
  }
}
"""

# API 配置常量
# viki.moe 系官方源（60s-api.viki.moe / 60s.viki.moe / b23.run）均在 Cloudflare 后，
# 部分服务器 IP 会被盾拦截，故改用官方公共实例列表中的社区实例，按序尝试：
# https://docs.60s-api.viki.moe/7306811m0
NEWS_60S_API_URLS = [
    "https://60s.crystelf.top/v2/60s",
    "https://api.elysiayanyu.top/v2/60s",
    "https://60s.7se.cn/v2/60s",
]
# 官方静态托管（jsDelivr CDN），路径需日期，作为全部实例失败后的兜底
NEWS_60S_STATIC_URL = "https://cdn.jsdelivr.net/gh/vikiboss/60s-static-host@main/static/60s/{}.json"
# 多源重试总时限（秒）：每次请求的超时会压到此剩余时间内，防止全部源超时时逐源等待拖慢整份日报
NEWS_60S_RETRY_DEADLINE = 60
ITHOME_RANK_URL = "https://www.ithome.com/block/rank.html"
DRAM_PRICE_URL = "https://www.dramx.com/Price/DSD.html"
BANGUMI_CALENDAR_URL = "https://bgm.tv/calendar"
DOUBAN_MOVIE_URL = "https://movie.douban.com/cinema/later/beijing/"
DMM_RANKING_URL = "https://api.video.dmm.co.jp/graphql"
FUEL_PRICE_URL = "https://60s.crystelf.top/v2/fuel-price"
GOLD_PRICE_URL = "https://60s.crystelf.top/v2/gold-price"

# DMM 排名术语过滤映射
TERM_FILTER_MAP = {
    "daily": {"daily": {"floor": "AV"}},
    "weekly": {"weekly": {"floor": "AV"}},
    "monthly": {"monthly": {"floor": "AV"}},
}

# 模板文件映射
TEMPLATE_FILES = {
    "main": "report.html",
    "animation": "report_animation.html",
    "movie": "report_movie.html",
    "dmm": "report_dmm.html",
}
