"""构建标签分类系统"""
import requests
from collections import Counter

# 定义主要分类和对应的标签关键词
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

print("获取所有标签...")

# 获取所有标签
all_tags = []
offset = 0
limit = 500

while True:
    params = {
        'closed': 'false',
        'limit': limit,
        'offset': offset
    }
    
    r = requests.get('https://gamma-api.polymarket.com/events', params=params, timeout=30)
    events = r.json()
    
    if not events:
        break
    
    for event in events:
        tags = event.get('tags', [])
        all_tags.extend([tag.get('label', '') for tag in tags if tag.get('label')])
    
    if len(events) < limit:
        break
    
    offset += limit

print(f"获取到 {len(set(all_tags))} 个唯一标签")

# 分类标签
tag_to_category = {}
category_to_tags = {cat: set() for cat in CATEGORIES}

for tag in all_tags:
    tag_lower = tag.lower()
    matched_categories = []
    
    for cat_id, cat_info in CATEGORIES.items():
        for keyword in cat_info['keywords']:
            if keyword in tag_lower:
                matched_categories.append(cat_id)
                break
    
    if matched_categories:
        # 优先匹配第一个分类
        primary_cat = matched_categories[0]
        tag_to_category[tag] = primary_cat
        category_to_tags[primary_cat].add(tag)

# 统计
print(f"\n{'='*80}")
print("分类统计:")
print(f"{'='*80}")

for cat_id, cat_info in CATEGORIES.items():
    tags = category_to_tags[cat_id]
    print(f"[{cat_info['emoji']}] {cat_info['display_name']:12s}: {len(tags):3d} 个标签")
    if len(tags) > 0:
        sample_tags = sorted(tags)[:5]
        print(f"   示例: {', '.join(sample_tags)}")

# 未分类的标签
all_tag_set = set(all_tags)
classified_tags = set(tag_to_category.keys())
unclassified = all_tag_set - classified_tags

print(f"\n{'='*80}")
print(f"未分类标签: {len(unclassified)} 个")
print(f"{'='*80}")
if unclassified:
    sample_unclassified = sorted(list(unclassified))[:20]
    print("示例:", ', '.join(sample_unclassified))

# 构建标签到市场的映射（通过事件）
print(f"\n构建标签到市场的映射...")

tag_to_markets = {}
event_to_tags = {}

offset = 0
limit = 500

while True:
    params = {
        'closed': 'false',
        'limit': limit,
        'offset': offset
    }
    
    r = requests.get('https://gamma-api.polymarket.com/events', params=params, timeout=30)
    events = r.json()
    
    if not events:
        break
    
    for event in events:
        event_id = event.get('id')
        tags = event.get('tags', [])
        tag_labels = [tag.get('label', '') for tag in tags if tag.get('label')]
        
        # 保存事件到标签的映射
        for tag in tag_labels:
            if tag not in tag_to_markets:
                tag_to_markets[tag] = set()
            
            # 添加该事件的所有市场ID
            markets = event.get('markets', [])
            for market in markets:
                market_id = market.get('id')
                if market_id:
                    tag_to_markets[tag].add(market_id)
    
    if len(events) < limit:
        break
    
    offset += limit
    print(f"已处理 {offset + len(events)} 个事件")

# 转换 set 为 list
tag_to_markets = {k: list(v) for k, v in tag_to_markets.items()}

# 保存分类结果
import json

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
        'total_tags': len(set(all_tags)),
        'classified_tags': len(tag_to_category),
        'unclassified_tags': len(unclassified),
        'total_markets': sum(len(m) for m in tag_to_markets.values())
    }
}

with open('tag_classification.json', 'w', encoding='utf-8') as f:
    json.dump(classification, f, ensure_ascii=False, indent=2)

print(f"\n分类结果已保存到: tag_classification.json")
print(f"完成!")
