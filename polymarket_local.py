# Polymarket 每日报告 - 修复版
# 放宽过滤条件,获取更多数据

import requests
from datetime import datetime, timedelta
import os
import json

# ============= 配置 =============
HISTORY_FILE = "market_history.json"

# ============= 过滤配置 =============
# 改为:只排除黑名单,不强制要求白名单
USE_WHITELIST = False  # 设为False,不强制匹配白名单

# ============= 黑名单关键词 =============
EXCLUDED = [
    # 体育赛事/比赛
    'world cup', 'football', 'soccer', 'nba', 'nfl', 'nhl', 'mlb', 'ufc',
    'tennis', 'golf', 'boxing', 'mma', 'olympics', 'super bowl', 'nascar',
    'formula 1', 'f1', 'fifa', 'champions league', 'premier league',
    'nba finals', 'world series', 'stanley cup', 'championship', 'tournament',
    # 游戏/电竞
    'gaming', 'esports', 'lol', 'dota', 'csgo', 'valorant', 'playstation',
    'xbox', 'nintendo', 'switch', 'video game', 'gamer', 'stream',
    'e-sports', 'esport', 'pubg', 'overwatch', 'roblox',
    'gta', 'grand theft auto', 'call of duty', 'fortnite', 'minecraft',
    'league of legends',
    # 娱乐/电影/音乐
    'movie', 'film', 'album', 'song', 'concert', 'music', 'entertainment',
    'actor', 'actress', 'celebrity', 'awards', 'oscar', 'grammy', 'emmy',
    'festival', 'tour', 'band', 'artist', 'spotify', 'netflix', 'disney',
    'hulu', 'hbo', 'prime video', 'streaming', 'tv show', 'series',
    'box office', 'release', 'premiere', 'director', 'producer',
    'kanye', 'west', 'singles', 'music video',
    'rihanna', 'playboi carti', 'album',
]

# ============= 白名单关键词(仅用于标注优先级,不过滤) =============
ALLOWED_KEYWORDS = [
    'trump', 'biden', 'election', 'president', 'congress', 'senate', 'political', 'politics',
    'government', 'democrat', 'republican', 'vote', 'campaign', 'candidate', 'ballot',
    'kamala', 'harris', 'donald', 'joe',
    'iran', 'israel', 'palestine', 'hamas', 'middle east',
    'geopolitics', 'policy', 'sanction', 'conflict', 'military',
    'nuclear', 'missile', 'attack', 'invasion', 'war', 'ukraine', 'russia', 'china', 'taiwan',
    'tension', 'diplomatic', 'border', 'trade war',
    'crypto', 'bitcoin', 'btc', 'eth', 'ethereum', 'solana', 'doge', 'altcoin', 'defi',
    'blockchain', 'nft', 'web3', 'token', 'coin', 'cryptocurrency', 'exchange',
    'inflation', 'fed', 'interest rate', 'federal reserve', 'recession', 'economy',
    'stock', 'market', 's&p 500', 'nasdaq', 'dow', 'wall street', 'financial', 'finance',
    'trading', 'invest', 'investment', 'fund', 'etf', 'dividend', 'bond', 'treasury',
    'gdp', 'economic', 'bank', 'credit', 'debt', 'loan', 'banking', 'crash', 'bull', 'bear',
    'forex', 'currency', 'dollar', 'euro', 'yen', 'yuan', 'commodity', 'gold', 'silver', 'oil',
    'tech', 'technology', 'ai', 'artificial intelligence', 'gpt', 'chatgpt', 'llm',
    'apple', 'google', 'microsoft', 'nvidia', 'tesla', 'spacex', 'elon', 'startup',
    'openai', 'anthropic', 'meta', 'amazon', 'software', 'internet', 'cyber',
    'machine learning',
]

# ============= 获取市场数据 =============
def get_markets():
    url = "https://gamma-api.polymarket.com/markets?closed=false&limit=500"
    try:
        r = requests.get(url, timeout=30)
        return r.json() if r.status_code == 200 else []
    except:
        return []

# ============= 过滤函数 =============
def is_filtered(m):
    question = m.get('question', '').lower()
    description = m.get('description', '').lower() if m.get('description') else ''
    text = question + ' ' + description

    # 黑名单:如果包含排除的关键词,直接过滤
    if any(kw in text for kw in EXCLUDED):
        return True

    # 白名单:可选,如果启用则必须包含至少一个允许的关键词
    if USE_WHITELIST:
        if not any(kw in text for kw in ALLOWED_KEYWORDS):
            return True

    return False

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

# ============= 报告生成 =============
def generate_html_report(markets, report_date, history):
    rd = report_date.strftime("%Y-%m-%d")
    now = datetime.now()

    print(f"Total markets from API: {len(markets)}")
    filtered_count = 0
    expired_count = 0

    data = []
    error_count = 0

    for m in markets:
        if is_filtered(m):
            filtered_count += 1
            continue
        if is_expired(m.get('endDate')):
            expired_count += 1
            continue
        try:
            prices = m.get('outcomePrices', [])
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices)
                except Exception as parse_error:
                    print(f"Failed to parse prices: {parse_error}")
                    prices = []
            price = float(prices[0]) if prices and len(prices) > 0 else 0
            market_id = m.get('id', m.get('conditionId', ''))

            changes = calculate_changes(price, history.get(market_id, {}))

            data.append({
                'q': m.get('question',''),
                'c': m.get('category',''),
                'e': m.get('endDate',''),
                'p': price,
                'v24': float(m.get('volume24hr') or 0),
                'vt': float(m.get('volume') or 0),
                'change_24h': changes['change_24h_abs'],
                'change_7d': changes['change_7d_abs'],
                'comparing_time': changes['comparing_time']
            })
        except Exception as e:
            error_count += 1
            print(f"Error processing market: {e}")
            continue

    print(f"Filtered: {filtered_count}, Expired: {expired_count}, Errors: {error_count}, Valid: {len(data)}")

    # 更新历史数据
    new_history = history.copy()
    updated_count = 0
    new_markets_count = 0

    for m in markets:
        if is_filtered(m) or is_expired(m.get('endDate')): continue
        try:
            market_id = m.get('id', m.get('conditionId', ''))
            prices = m.get('outcomePrices', [])
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices)
                except:
                    prices = []
            price = float(prices[0]) if prices and len(prices) > 0 else 0

            if market_id in new_history:
                old_24h = new_history[market_id].get('price_24h', price)
                new_history[market_id]['price_7d'] = old_24h
                new_history[market_id]['price_24h'] = price
                new_history[market_id]['timestamp'] = now.isoformat()
                updated_count += 1
            else:
                new_history[market_id] = {
                    'price_24h': price,
                    'price_7d': price,
                    'timestamp': now.isoformat()
                }
                new_markets_count += 1
        except Exception as e:
            print(f"Error updating history: {e}")
            continue

    print(f"History updated: {updated_count} existing, {new_markets_count} new markets")
    save_history(new_history)

    # 排序 - Top10
    by_rise = sorted(data, key=lambda x: x['change_24h'], reverse=True)[:10]
    by_fall = sorted(data, key=lambda x: x['change_24h'])[:10]
    by_vt = sorted(data, key=lambda x: x['vt'], reverse=True)[:10]
    by_v24 = sorted(data, key=lambda x: x['v24'], reverse=True)[:10]
    by_future = [x for x in data if is_within_range(x['e'])][:10]
    by_future = sorted(by_future, key=lambda x: x['p'], reverse=True)[:10]

    # 生成HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body{{font-family:sans-serif;background:#1a1a2e;color:#e4e4e4;padding:10px}}
.container{{max-width:900px;margin:0 auto}}
h1{{color:#00d4ff;text-align:center;padding:10px 0}}
.info{{text-align:center;gap:10px;display:flex;justify-content:center;margin:10px 0}}
.info span{{background:#1e3a5a;padding:5px 10px;border-radius:5px}}
.note{{background:#2d2d44;padding:10px;border-radius:5px;margin:10px 0;font-size:12px}}
.section{{background:#252538;padding:15px;margin:10px 0;border-radius:5px}}
.section h2{{color:#fff;margin:0 0 10px 0}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#1e3a5a;color:#00d4ff;padding:5px;text-align:left}}
td{{padding:8px;border-bottom:1px solid #333;vertical-align:top}}
.rank{{color:#00d4ff;font-weight:bold;text-align:center;width:30px}}
.title{{color:#fff;font-size:13px;line-height:1.4;max-width:350px;word-wrap:break-word;word-break:break-word}}
.cat{{color:#888;font-size:10px;margin-top:3px}}
.prob{{padding:2px 6px;border-radius:3px;font-weight:bold}}
.high{{background:#004d26;color:#00ff88}}
.mid{{background:#4d3d00;color:#ffc107}}
.low{{background:#4d1a1a;color:#ff5252}}
.up{{color:#00ff88}}
.down{{color:#ff5252}}
.vol{{color:#ffc107}}
.date{{color:#888;font-size:11px}}
</style>
</head>
<body>
<div class="container">
<h1>Polymarket Daily Report - {rd}</h1>
<div class="info">
<span>Date: {rd}</span>
<span>Beijing Time: {now.strftime('%H:%M')}</span>
</div>
<div class="note">
Filtered: Sports/Gaming/Entertainment | Valid Markets: {len(data)} | Comparing: {by_rise[0]['comparing_time'] if by_rise else 'No historical data'}
</div>
'''

    def build_table(rows, title, rise=True, show_change=True):
        nonlocal html
        html += f'''<div class="section">
<h2>{'📈' if rise else '📉'} {title}</h2>
<table><tr><th>#</th><th>Event</th><th>Current</th><th>24h Change</th><th>7d Change</th><th>End Date</th><th>24h Vol</th><th>Total Vol</th></tr>'''
        for i, x in enumerate(rows[:10], 1):
            pc = 'high' if x['p']>0.6 else 'mid' if x['p']>0.3 else 'low'
            change_24h = x['change_24h'] * 100
            change_7d = x['change_7d'] * 100

            delta_24h = f"+{change_24h:.1f}%" if change_24h >= 0 else f"{change_24h:.1f}%"
            delta_7d = f"+{change_7d:.1f}%" if change_7d >= 0 else f"{change_7d:.1f}%"
            cls_24h = 'up' if change_24h >= 0 else 'down'
            cls_7d = 'up' if change_7d >= 0 else 'down'

            html += f'''<tr>
<td class='rank'>{i}</td>
<td><div class='title' title="{x['q']}">{x['q']}</div><div class='cat'>{x['c']}</div></td>
<td><span class='prob {pc}'>{format_pct(x['p'])}</span></td>
<td class='{cls_24h}'>{delta_24h}</td>
<td class='{cls_7d}'>{delta_7d}</td>
<td class='date'>{format_end(x['e'])}</td>
<td class='vol'>{format_vol(x['v24'])}</td>
<td class='vol'>{format_vol(x['vt'])}</td>
</tr>'''
        html += '</table></div>'

    # 5个分类
    build_table(by_rise, "Top Probability Rise", True)
    build_table(by_fall, "Top Probability Fall", False)
    build_table(by_vt, "Top Total Volume", True)
    build_table(by_v24, "Top 24h Volume", True)
    build_table(by_future, "Top Future High Probability", True)

    html += f'''
<footer style="text-align:center;padding:10px;color:#666;font-size:10px">
<p>Generated: {rd} {now.strftime('%H:%M')} | API: Gamma API | {by_rise[0]['comparing_time'] if by_rise else 'N/A'}</p>
</footer>
</div>
</body>
</html>'''

    return html

# ============= 主函数 =============
def main():
    print(f"Running at {datetime.now()}")

    history = load_history()
    print(f"Loaded history: {len(history)} markets")

    markets = get_markets()
    print(f"Got {len(markets)} markets from Gamma API")

    report_date = datetime.now()
    date_str = report_date.strftime("%Y%m%d")

    html = generate_html_report(markets, report_date, history)

    # 保存HTML文件
    filename = f"polymarket_report_{date_str}.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nReport generated successfully: {filename}")

if __name__ == "__main__":
    main()

