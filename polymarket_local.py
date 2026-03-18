# Polymarket 每日报告 - 改进版（支持多个 API + 官方分类）

import requests
from datetime import datetime, timedelta
import os
import json

# ============= 配置 =============
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 历史数据存储文件
HISTORY_FILE = "market_history.json"

# ============= 官方分类映射 =============
# 用户选择的分类：保留 6 个核心分类 + 其他
OFFICIAL_CATEGORIES = {
    'politics': True,      # 保留 - 政治
    'economy': True,       # 保留 - 经济
    'finance': True,       # 保留 - 金融
    'crypto': True,        # 保留 - 加密货币
    'tech': True,          # 保留 - 技术
    'mentions': True,      # 保留 - 提及
    'other': True,         # 保留 - 其他
    'climate-science': False,  # 排除
    'culture': False,      # 排除
    'sports': False,       # 排除
}

# CLOB API 中要保留的 Tags
# 只保留与政治、经济、金融、加密、科技、地缘政治、选举、伊朗相关的
KEEP_CLOB_TAGS = [
    # 政治 & 选举
    'politics', 'elections', 'u.s. politics', 'usa election', '2024 election',
    'presidential election', 'u.s. election', 'us elections', 'us presidency',
    'trump', 'biden', 'donald trump', 'joe biden', 'kamala harris',
    'presidential nomination', 'democratic party', 'republican party',
    'u.s. government', 'us government', 'presidency', 'potus',
    
    # 经济 & 金融
    'finance', 'federal reserve', 'interest rates', 'monetary policy',
    'economy', 'monetary policy', 'economic policy', 'trading',
    
    # 加密货币
    'crypto', 'blockchain', 'token launch', 'fdv',
    
    # 科技
    'ai', 'technology', 'machine learning', 'gpt-4',
    
    # 地缘政治
    'geopolitics', 'iran', 'israel', 'military', 'nuclear weapons',
    'international relations', 'global security', 'middle east',
    
    # 其他保留
    'breaking news', 'predictions', 'future events', 'security',
]

# CLOB API 中要排除的 Tags
EXCLUDE_CLOB_TAGS = [
    'sports', 'awards', 'culture', 'entertainment', 'games', 'gaming'
]

# 白名单：必须包含的关键词
ALLOWED_KEYWORDS = [
    # 政治/选举
    'trump', 'biden', 'election', 'president', 'congress', 'senate', 'political', 'politics',
    'government', 'democrat', 'republican', 'vote', 'campaign', 'candidate', 'ballot',
    'kamala', 'harris', 'donald', 'joe',
    # 地缘政治
    'iran', 'israel', 'palestine', 'hamas', 'middle east',
    'geopolitics', 'policy', 'sanction', 'conflict', 'military',
    'nuclear', 'missile', 'attack', 'invasion', 'war', 'ukraine', 'russia', 'china', 'taiwan',
    'tension', 'diplomatic', 'border', 'trade war',
    # 金融/经济/市场
    'crypto', 'bitcoin', 'btc', 'eth', 'ethereum', 'solana', 'doge', 'altcoin', 'defi',
    'blockchain', 'nft', 'web3', 'token', 'coin', 'cryptocurrency', 'exchange',
    'inflation', 'fed', 'interest rate', 'federal reserve', 'recession', 'economy',
    'stock', 'market', 's&p 500', 'nasdaq', 'dow', 'wall street', 'financial', 'finance',
    'trading', 'invest', 'investment', 'fund', 'etf', 'dividend', 'bond', 'treasury',
    'gdp', 'economic', 'bank', 'credit', 'debt', 'loan', 'banking', 'crash', 'bull', 'bear',
    'forex', 'currency', 'dollar', 'euro', 'yen', 'yuan', 'commodity', 'gold', 'silver', 'oil',
    # 科技
    'tech', 'technology', 'ai', 'artificial intelligence', 'gpt', 'chatgpt', 'llm',
    'apple', 'google', 'microsoft', 'nvidia', 'tesla', 'spacex', 'elon', 'startup',
    'openai', 'anthropic', 'meta', 'amazon', 'software', 'internet', 'cyber',
    'machine learning',
]

# 黑名单：排除的关键词
EXCLUDED = [
    # 体育赛事/比赛
    'world cup', 'football', 'soccer', 'nba', 'nfl', 'nhl', 'mlb', 'ufc',
    'tennis', 'golf', 'boxing', 'mma', 'olympics', 'super bowl', 'nascar',
    'formula 1', 'f1', 'fifa', 'champions league', 'premier league',
    'nba finals', 'world series', 'stanley cup', 'championship', 'tournament',
    'match', 'game', 'team', 'player', 'coach', 'score', 'win', 'lose', 'winner',
    'finals', 'quarterfinal', 'semifinal', 'bracket', 'season', 'league',
    'basketball', 'baseball', 'hockey', 'volleyball',
    # 游戏/电竞
    'gaming', 'esports', 'lol', 'dota', 'csgo', 'valorant', 'playstation',
    'xbox', 'nintendo', 'switch', 'game', 'video game', 'gamer', 'stream',
    'e-sports', 'esport', 'tournament game', 'pubg', 'overwatch', 'roblox',
    'gta', 'grand theft auto', 'call of duty', 'fortnite', 'minecraft',
    'league of legends', 'csgo', 'valorant',
    # 娱乐/电影/音乐
    'movie', 'film', 'album', 'song', 'concert', 'music', 'entertainment',
    'actor', 'actress', 'celebrity', 'awards', 'oscar', 'grammy', 'emmy',
    'festival', 'tour', 'band', 'artist', 'spotify', 'netflix', 'disney',
    'hulu', 'hbo', 'prime video', 'streaming', 'tv show', 'series',
    'box office', 'release', 'premiere', 'director', 'producer',
    'kanye', 'west', 'album', 'singles', 'music video',
]

# ============= 获取市场数据 =============
def get_markets_from_gamma():
    """从 Gamma API 获取市场"""
    url = "https://gamma-api.polymarket.com/markets?closed=false&limit=500"
    try:
        r = requests.get(url, timeout=30)
        return r.json() if r.status_code == 200 else []
    except:
        return []

def get_markets_from_clob():
    """从 CLOB API 获取市场（包含 tags）"""
    url = "https://clob.polymarket.com/markets?limit=1000"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data.get('data', [])
        return []
    except:
        return []

# ============= 过滤函数 =============
def is_filtered_by_category(market_category):
    """根据官方分类判断是否过滤
    
    Returns:
        None - 分类未知，继续其他过滤
        True - 应该保留
        False - 应该排除
    """
    if not market_category:
        return None
    
    category_lower = market_category.lower()
    if category_lower in OFFICIAL_CATEGORIES:
        should_keep = OFFICIAL_CATEGORIES[category_lower]
        return should_keep
    
    return None

def is_filtered_by_tags(tags):
    """根据 CLOB API 的 tags 判断是否过滤
    
    Returns:
        True - 应该保留
        False - 应该排除
        None - 无法判断，继续其他过滤
    """
    if not tags or not isinstance(tags, list):
        return None
    
    # 转换为小写便于匹配
    tags_lower = [t.lower() if isinstance(t, str) else t for t in tags]
    
    # 第一优先级：排除明确的体育、娱乐标签
    if any(tag in EXCLUDE_CLOB_TAGS for tag in tags_lower):
        return False
    
    # 第二优先级：包含保留的标签 → 保留
    if any(keep_tag in tags_lower for keep_tag in KEEP_CLOB_TAGS):
        return True
    
    # 如果只有 'All' 标签，无法判断，继续其他过滤
    if tags_lower == ['all']:
        return None
    
    # 其他未知标签，无法判断，继续其他过滤
    return None

def is_filtered_by_keywords(question, description='', category=''):
    """根据关键词过滤"""
    text = f"{question} {description} {category}".lower()
    
    # 黑名单：如果包含排除的关键词，直接过滤
    if any(kw in text for kw in EXCLUDED):
        return True
    
    # 白名单：必须包含至少一个允许的关键词
    if not any(kw in text for kw in ALLOWED_KEYWORDS):
        return True
    
    return False

def should_include_market(market, use_clob=False):
    """判断是否应该包含市场
    
    Args:
        market: 市场数据对象
        use_clob: 是否使用 CLOB API 的数据（包含 tags）
    
    Returns:
        True - 包含，False - 排除
    """
    
    # 获取市场信息
    if use_clob:
        question = market.get('question', '')
        description = market.get('description', '')
        category = None  # CLOB API 没有 category 字段
        tags = market.get('tags', [])
    else:
        question = market.get('question', '')
        description = market.get('description', '')
        category = market.get('category', '')
        tags = []
    
    # 第一层：官方分类过滤（仅 Gamma API）
    if not use_clob and category:
        result = is_filtered_by_category(category)
        if result is not None:
            return result
    
    # 第二层：Tags 过滤（仅 CLOB API）
    if use_clob and tags:
        result = is_filtered_by_tags(tags)
        if result is not None:
            return result
    
    # 第三层：关键词过滤（备选方案）
    return not is_filtered_by_keywords(question, description, category or '')

# ============= 工具函数 =============
def is_expired(end_date):
    if not end_date: return False
    try:
        d = end_date.replace('Z','').split('+')[0]
        return (datetime.fromisoformat(d) + timedelta(hours=8)).date() < datetime.now().date()
    except: return False

def is_within_range(end_date, days_min=7, days_max=365):
    if not end_date: return False
    try:
        d = end_date.replace('Z','').split('+')[0]
        end_dt = datetime.fromisoformat(d) + timedelta(hours=8)
        now = datetime.now()
        days_until = (end_dt - now).days
        return days_min <= days_until <= days_max
    except: return False

def format_vol(v): 
    v = float(v or 0)
    return f"${v/1e6:.2f}M" if v>=1e6 else f"${v/1e3:.1f}K" if v>=1e3 else f"${v:.0f}"

def format_pct(p): 
    return f"{float(p or 0)*100:.1f}%" if p else "N/A"

def format_end(d): 
    return d[:10] if d else "N/A"

# ============= 历史数据管理 =============
def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
    except: pass
    return {}

def save_history(data):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def calculate_changes(current_price, history):
    changes = {
        "change_24h_abs": 0,
        "change_7d_abs": 0,
        "change_24h_pct": 0,
        "change_7d_pct": 0,
        "comparing_time": "No historical data"
    }
    
    if history:
        h = history
        if 'price_24h' in h and h['price_24h']:
            changes["change_24h_abs"] = current_price - h['price_24h']
            changes["comparing_time"] = "vs 24h ago"
        if 'price_7d' in h and h['price_7d']:
            changes["change_7d_abs"] = current_price - h['price_7d']
            if "24h" in changes["comparing_time"]:
                changes["comparing_time"] = "vs 24h & 7d ago"
            else:
                changes["comparing_time"] = "vs 7d ago"
    
    return changes

# ============= Telegram 发送 =============
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, json=data, timeout=30)
    return r.json().get('ok', False)

def send_document(html_content, date_str, max_retries=3):
    filename = f"polymarket_report_{date_str}.html"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    
    for attempt in range(max_retries):
        try:
            with open(filename, 'rb') as f:
                files = {'document': (filename, f, 'text/html')}
                data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': f"📊 Polymarket Daily Report - {date_str}"}
                r = requests.post(url, data=data, files=files, timeout=(30, 120))
            
            print(f"Telegram API Response: {r.status_code}")
            return r.json().get('ok', False)
        
        except requests.exceptions.Timeout as e:
            print(f"Timeout on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(5)
            else:
                return False
        except Exception as e:
            print(f"Error sending document: {e}")
            return False
    
    return False

# ============= 报告生成 =============
def generate_html_report(markets, report_date, history, use_clob=False):
    rd = report_date.strftime("%Y-%m-%d")
    now = datetime.now()
    
    print(f"Total markets from API: {len(markets)}")
    filtered_count = 0
    expired_count = 0
    
    data = []
    error_count = 0
    
    for m in markets:
        if not should_include_market(m, use_clob=use_clob):
            filtered_count += 1
            continue
        
        if is_expired(m.get('endDate') or m.get('end_date_iso')):
            expired_count += 1
            continue
        
        try:
            # 处理不同 API 的字段差异
            if use_clob:
                question = m.get('question', '')
                end_date = m.get('end_date_iso', '')
                price = 0  # CLOB API 没有直接的价格，需要从 tokens 获取
                volume_24h = 0
                volume_total = 0
            else:
                prices = m.get('outcomePrices', [])
                if isinstance(prices, str):
                    try:
                        prices = json.loads(prices)
                    except:
                        prices = []
                price = float(prices[0]) if prices and len(prices) > 0 else 0
                question = m.get('question', '')[:200]
                end_date = m.get('endDate', '')
                volume_24h = float(m.get('volume24hr') or 0)
                volume_total = float(m.get('volume') or 0)
            
            market_id = m.get('id', m.get('condition_id', ''))
            
            changes = calculate_changes(price, history.get(market_id, {}))
            
            data.append({
                'q': question,
                'c': m.get('category', '') or m.get('market_slug', '')[:30],
                'e': end_date,
                'p': price,
                'v24': volume_24h,
                'vt': volume_total,
                'change_24h': changes['change_24h_abs'],
                'change_7d': changes['change_7d_abs'],
                'comparing_time': changes['comparing_time']
            })
        except Exception as e:
            error_count += 1
            print(f"Error processing market: {e}")
            continue
    
    print(f"Filtered: {filtered_count}, Expired: {expired_count}, Errors: {error_count}, Valid: {len(data)}")
    
    # 简化的 HTML 模板...（保持原有的 HTML 生成逻辑）
    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body{{font-family:sans-serif;background:#1a1a2e;color:#e4e4e4;padding:10px}}
.container{{max-width:900px;margin:0 auto}}
h1{{color:#00d4ff;text-align:center}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#1e3a5a;color:#00d4ff;padding:5px}}
td{{padding:8px;border-bottom:1px solid #333}}
.title{{color:#fff;max-width:350px;word-wrap:break-word;word-break:break-word}}
.high{{background:#004d26;color:#00ff88}}
.mid{{background:#4d3d00;color:#ffc107}}
.low{{background:#4d1a1a;color:#ff5252}}
.up{{color:#00ff88}}
.down{{color:#ff5252}}
</style>
</head>
<body>
<div class="container">
<h1>📊 Polymarket Daily Report - {rd}</h1>
<p>API Source: {"CLOB" if use_clob else "Gamma"} | Markets: {len(data)} | Filtered: {filtered_count}</p>
<p>Data Source: CLOB/Gamma API + Official Categories + Keyword Filtering</p>
<table>
<tr><th>#</th><th>Event</th><th>Current</th><th>24h Change</th><th>End Date</th><th>24h Volume</th></tr>
'''
    
    by_rise = sorted(data, key=lambda x: x['change_24h'], reverse=True)[:10]
    for i, x in enumerate(by_rise, 1):
        pc = 'high' if x['p']>0.6 else 'mid' if x['p']>0.3 else 'low'
        change_24h_pct = f"+{x['change_24h']*100:.1f}%" if x['change_24h'] >= 0 else f"{x['change_24h']*100:.1f}%"
        cls_24h = 'up' if x['change_24h'] >= 0 else 'down'
        
        html += f'''<tr>
<td>{i}</td>
<td><div class="title">{x['q']}</div></td>
<td><span class="{pc}">{format_pct(x['p'])}</span></td>
<td class="{cls_24h}">{change_24h_pct}</td>
<td>{format_end(x['e'])}</td>
<td>{format_vol(x['v24'])}</td>
</tr>'''
    
    html += '''</table>
</div>
</body>
</html>'''
    
    return html

# ============= 主函数 =============
def main():
    print(f"Running at {datetime.now()}")
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID is missing!")
        return
    
    history = load_history()
    print(f"Loaded history: {len(history)} markets")
    
    # 尝试 CLOB API（推荐）
    print("\n1. Trying CLOB API...")
    markets = get_markets_from_clob()
    use_clob = True
    
    if not markets:
        print("2. CLOB API failed, falling back to Gamma API...")
        markets = get_markets_from_gamma()
        use_clob = False
    
    print(f"Got {len(markets)} markets from {'CLOB' if use_clob else 'Gamma'} API")
    
    report_date = datetime.now()
    date_str = report_date.strftime("%Y%m%d")
    
    html = generate_html_report(markets, report_date, history, use_clob=use_clob)
    
    success = send_document(html, date_str)
    print(f"Document sent: {success}")

if __name__ == "__main__":
    main()

