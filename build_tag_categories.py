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

CATEGORIES = {
    'politics': {
        'keywords': ['politics', 'election', 'president', 'trump', 'biden', 'congress', 'senate',
                    'republican', 'democratic', 'primary', 'midterm', 'house', 'governor',
                    'world elections', 'global elections', 'us election'],
        'display_name': '政治',
        'emoji': '[POL]'
    },
    'crypto': {
        'keywords': ['crypto', 'bitcoin', 'ethereum', 'btc', 'eth', 'crypto prices',
                    'xrp', 'solana', 'ripple', 'bnb', 'dogecoin', 'ada', 'polygon',
                    'chainlink', 'uniswap', 'defi'],
        'display_name': '加密货币',
        'emoji': '[CRY]'
    },
    'sports': {
        'keywords': ['sports', 'soccer', 'basketball', 'football', 'hockey', 'tennis',
                    'cricket', 'esports', 'nfl', 'nba', 'nhl', 'mlb', 'ncaa',
                    'epl', 'la liga', 'bundesliga', 'rugby', 'golf'],
        'display_name': '体育',
        'emoji': '[SPO]'
    },
    'culture': {
        'keywords': ['culture', 'music', 'movie', 'celebrity', 'entertainment', 'awards',
                    'oscars', 'grammys', 'fashion'],
        'display_name': '文化娱乐',
        'emoji': '[CUL]'
    },
    'business': {
        'keywords': ['business', 'finance', 'economy', 'stock', 'equities', 'markets',
                    'economy', 'big tech', 'tech', 'stocks'],
        'display_name': '商业经济',
        'emoji': '[BUS]'
    },
    'geopolitics': {
        'keywords': ['geopolitics', 'war', 'ukraine', 'middle east', 'iran', 'israel',
                    'russia', 'china', 'world'],
        'display_name': '地缘政治',
        'emoji': '[GEO]'
    },
    'science': {
        'keywords': ['science', 'ai', 'artificial intelligence', 'technology',
                    'space', 'weather', 'climate'],
        'display_name': '科学技术',
        'emoji': '[SCI]'
    }
}

def fetch_with_retry(url, params, max_retries=3, backoff=5):
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
    print("获取所有事件数据...")
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
            print(f"  [错误] 获取失败，停止: {e}")
            break

        if not events:
            break

        all_events.extend(events)
        print(f"  已累积 {len(all_events)} 个事件")

        if len(events) < limit:
            break

        offset += limit

        if offset > 50000:
            print("  [警告] offset 超过安全上限，停止")
            break

    print(f"共获取到 {len(all_events)} 个事件")
    return all_events

def classify_tags(all_events):
    all_tags = []
    tag_to_markets = {}

    for event in all_events:
        tags = event.get('tags', [])
        tag_labels = [tag.get('label', '') for tag in tags if tag.get('label')]
        markets = event.get('markets', [])
        market_ids = [str(m.get('id')) for m in markets if m.get('id') is not None]

        for tag in tag_labels:
            all_tags.append(tag)
            if tag not in tag_to_markets:
                tag_to_markets[tag] = set()
            tag_to_markets[tag].update(market_ids)

    all_tags_unique = list(set(all_tags))
    print(f"获取到 {len(all_tags_unique)} 个唯一标签")

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
                break

    return all_tags_unique, tag_to_category, category_to_tags, tag_to_markets

def main():
    print("=" * 60)
    print("构建标签分类系统")
    print("=" * 60)

    try:
        all_events = fetch_all_events()
    except Exception as e:
        print(f"[FATAL] 获取事件数据失败: {e}")
        sys.exit(1)

    if not all_events:
        print("[FATAL] 未获取到任何事件，退出")
        sys.exit(1)

    all_tags, tag_to_category, category_to_tags, tag_to_markets_sets = classify_tags(all_events)

    print(f"\n分类统计:")
    for cat_id, cat_info in CATEGORIES.items():
        tags = category_to_tags[cat_id]
        market_count = sum(len(tag_to_markets_sets.get(t, set())) for t in tags)
        print(f"  {cat_info['display_name']}: {len(tags)} 个标签, {market_count} 个市场ID")

    unclassified = set(all_tags) - set(tag_to_category.keys())
    print(f"未分类标签: {len(unclassified)} 个")

    tag_to_markets = {k: list(v) for k, v in tag_to_markets_sets.items()}

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
    print(f"\n分类结果已保存: {output_file} ({file_size / 1024:.1f} KB)")
    print("完成!")

if __name__ == '__main__':
    main()

