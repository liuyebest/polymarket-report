"""
构建标签分类系统
从 Polymarket events API 获取所有事件的标签，
将标签映射到预定义分类，并建立标签→市场ID的映射。
输出: tag_classification.json
"""
import requests
import json
import time
import sys

# ── 分类定义 ──────────────────────────────────────────────
CATEGORIES = {
    'politics': {
        'keywords': ['politics', 'election', 'president', 'trump', 'biden', 'congress', 'senate',
                    'republican', 'democratic', 'primary', 'midterm', 'midterms', 'house', 'governor',
                    'world elections', 'global elections', 'us election', 'democrat', 'republicans',
                    'democrats', 'mag election', 'mayor', 'mayoral', 'referendum', 'parliament',
                    'supreme court', 'scotus', 'inauguration', 'cabinet', 'impeach', 'gerrymander',
                    'voter','courts', 'epstein'],
        'display_name': '政治',
        'emoji': '[POL]'
    },
    'crypto': {
        'keywords': ['crypto', 'bitcoin', 'ethereum', 'btc', 'eth', 'crypto prices',
                    'xrp', 'solana', 'ripple', 'bnb', 'dogecoin', 'ada', 'polygon',
                    'chainlink', 'uniswap', 'defi', 'token launch', 'token', 'fdv',
                    'memecoin', 'stablecoin', 'airdrop', 'binance', 'coinbase', 'nft',
                    'hyperliquid', 'usdt'],
        'display_name': '加密货币',
        'emoji': '[CRY]'
    },
    'sports': {
        'keywords': ['sports', 'soccer', 'basketball', 'football', 'hockey', 'tennis',
                    'cricket', 'esports', 'nfl', 'nba', 'nhl', 'mlb', 'ncaa',
                    'epl', 'la liga', 'bundesliga', 'rugby', 'golf', 'nba', 'mls',
                    'premier league', 'serie a', 'ligue 1', 'champions league', 'europa',
                    'fifa', 'world cup', 'ufc', 'mma', 'boxing', 'f1', 'formula 1',
                    'nfl draft', 'super bowl', 'world series', 'stanley cup','games'],
        'display_name': '体育',
        'emoji': '[SPO]'
    },
    'culture': {
        'keywords': ['culture', 'music', 'movie', 'celebrity', 'entertainment', 'awards',
                    'oscars', 'grammys', 'fashion', 'eurovision', 'kpop', 'k-pop',
                    'taylor swift', 'reality tv', 'coachella'],
        'display_name': '文化娱乐',
        'emoji': '[CUL]'
    },
    'business': {
        'keywords': ['business', 'finance', 'economy', 'stock', 'equities', 'markets',
                    'big tech', 'tech', 'stocks', 'pre-market', 'premarket', 'ipo',
                    'ipos', 'earnings', 'acquisition', 'merger', 'fed', 'interest rate',
                    'inflation', 'gdp', 'sp500', 's&p', 'treasur', 'commodit',
                    'forex', 'exchange rate', 'dollar', 'jobs report', 'fed rate',
                    'fomc', 'housing', 'real estate', 'gold', 'oil', 'silver',
                    'bitcoin dominance', 'economic policy','macro', 'indicies', 'powell', 'cpi', 'apple'],
        'display_name': '商业经济',
        'emoji': '[BUS]'
    },
    'geopolitics': {
        'keywords': ['geopolitics', 'war', 'ukraine', 'middle east', 'iran', 'israel',
                    'russia', 'china', 'world', 'nato', 'nuclear', 'military',
                    'ceasefire', 'sanction', 'tariff', 'trade war', 'palestine',
                    'gaza', 'hamas', 'putin', 'xi jinping', 'sudan', 'yemen',
                    'north korea', 'korea', 'diplomacy', 'foreign policy', 'refugee',
                    'terror', 'isis', 'migration', 'border','venezuela', 'canada', 'greenland', 'uk', 'europe', 'france', 
                     'brazil', 'spillover', 'unrest'],
        'display_name': '地缘政治',
        'emoji': '[GEO]'
    },
    'science': {
        'keywords': ['science', 'ai', 'artificial intelligence', 'technology',
                    'space', 'weather', 'climate', 'openai', 'chatgpt', 'gpt',
                    'spacex', 'nasa', 'elon musk', 'robot', 'quantum',
                    'earthquake', 'hurricane', 'natural disaster', 'disease',
                    'pandemic', 'nuclear', 'energy', 'anthropic', 'claude',
                    'deepseek', 'grok', 'llm','sam altman'],
        'display_name': '科学技术',
        'emoji': '[SCI]'
    }
}

# ── 工具函数 ──────────────────────────────────────────────

def fetch_with_retry(url, params, max_retries=3, backoff=5):
    """带重试机制的 GET 请求"""
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"  [重试 {attempt}/{max_retries}] 请求失败: {e}")
            if attempt < max_retries:
                time.sleep(backoff * attempt)
            else:
                raise
    return []


def fetch_all_events():
    """
    分页获取所有未关闭的事件（只请求一次，同时收集标签和市场ID）
    返回: events 列表
    """
    print("获取所有事件数据（标签 + 市场映射）...")
    all_events = []
    offset = 0
    limit = 500
    url = 'https://gamma-api.polymarket.com/events'

    while True:
        params = {'closed': 'false', 'limit': limit, 'offset': offset}
        print(f"  获取 offset={offset} ...")
        try:
            events = fetch_with_retry(url, params)
        except Exception as e:
            print(f"  [错误] 获取 offset={offset} 失败，停止: {e}")
            break

        if not events:
            break

        all_events.extend(events)
        print(f"  已累积 {len(all_events)} 个事件")

        if len(events) < limit:
            break

        offset += limit

        # 安全上限
        if offset > 50000:
            print("  [警告] offset 超过安全上限，停止")
            break

    print(f"共获取到 {len(all_events)} 个事件")
    return all_events


def classify_tags(all_events):
    """从事件列表中提取标签，并进行分类"""
    # 收集所有标签
    all_tags = []
    tag_to_markets = {}

    for event in all_events:
        tags = event.get('tags', [])
        tag_labels = [tag.get('label', '') for tag in tags if tag.get('label')]

        # 收集该事件下的所有市场ID
        markets = event.get('markets', [])
        market_ids = [str(m.get('id')) for m in markets if m.get('id') is not None]

        for tag in tag_labels:
            all_tags.append(tag)
            if tag not in tag_to_markets:
                tag_to_markets[tag] = set()
            tag_to_markets[tag].update(market_ids)

    # 去重
    all_tags_unique = list(set(all_tags))
    print(f"获取到 {len(all_tags_unique)} 个唯一标签")

    # 分类标签
    tag_to_category = {}
    category_to_tags = {cat: set() for cat in CATEGORIES}

    for tag in all_tags_unique:
        tag_lower = tag.lower()
        for cat_id, cat_info in CATEGORIES.items():
            matched = False
            for keyword in cat_info['keywords']:
                if keyword in tag_lower:
                    tag_to_category[tag] = cat_id
                    category_to_tags[cat_id].add(tag)
                    matched = True
                    break
            if matched:
                break  # 只归入第一个匹配的分类

    return all_tags_unique, tag_to_category, category_to_tags, tag_to_markets


def main():
    print("=" * 60)
    print("构建标签分类系统")
    print("=" * 60)

    # 1. 获取所有事件（一次性）
    try:
        all_events = fetch_all_events()
    except Exception as e:
        print(f"[FATAL] 获取事件数据失败: {e}")
        sys.exit(1)

    if not all_events:
        print("[FATAL] 未获取到任何事件，退出")
        sys.exit(1)

    # 2. 分类处理
    all_tags, tag_to_category, category_to_tags, tag_to_markets_sets = classify_tags(all_events)

    # 3. 打印统计
    print(f"\n{'='*60}")
    print("分类统计:")
    print(f"{'='*60}")
    for cat_id, cat_info in CATEGORIES.items():
        tags = category_to_tags[cat_id]
        market_count = sum(len(tag_to_markets_sets.get(t, set())) for t in tags)
        print(f"  [{cat_info['emoji']}] {cat_info['display_name']:12s}: {len(tags):3d} 个标签, 约 {market_count} 个市场ID")
        if tags:
            sample = sorted(tags)[:3]
            print(f"     示例标签: {', '.join(sample)}")

    unclassified = set(all_tags) - set(tag_to_category.keys())
    print(f"\n未分类标签: {len(unclassified)} 个")

    # 4. 转换 set → list（JSON 可序列化）
    tag_to_markets = {k: list(v) for k, v in tag_to_markets_sets.items()}

    # 5. 构建并保存分类结果
    classification = {
        'categories': {
            cat_id: {
                'display_name': cat_info['display_name'],
                'emoji': cat_info['emoji'],
                'keywords': cat_info['keywords'],
                'tags': sorted(list(category_to_tags[cat_id])),
                'tag_count': len(category_to_tags[cat_id])
            }
            for cat_id, cat_info in CATEGORIES.items()
        },
        'tag_to_category': tag_to_category,
        'tag_to_markets': tag_to_markets,
        'stats': {
            'total_tags': len(all_tags),
            'classified_tags': len(tag_to_category),
            'unclassified_tags': len(unclassified),
            'total_market_ids': sum(len(v) for v in tag_to_markets.values())
        }
    }

    output_file = 'tag_classification.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(classification, f, ensure_ascii=False, indent=2)

    import os
    file_size = os.path.getsize(output_file)
    print(f"\n✅ 分类结果已保存到: {output_file} ({file_size / 1024:.1f} KB)")
    print("完成!")


if __name__ == '__main__':
    main()

