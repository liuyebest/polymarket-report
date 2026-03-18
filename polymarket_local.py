# Polymarket 每日报告 - HTML完整版

import requests
from datetime import datetime, timedelta
import os
import json

# ============= 配置 =============
# 敏感信息必须通过环境变量传入，不要在代码中硬编码
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 历史数据存储文件
HISTORY_FILE = "market_history.json"

# 白名单:只包含这些主题的市场
# 如果市场不包含这些关键词,将被过滤掉
ALLOWED_KEYWORDS = [
    # 政治
    'trump', 'biden', 'election', 'president', 'congress', 'senate', 'political', 'politics',
    'government', 'war', 'ukraine', 'russia', 'china', 'geopolitics', 'policy',
    # 金融/经济
    'crypto', 'bitcoin', 'eth', 'ethereum', 'btc', 'inflation', 'fed', 'interest rate',
    'recession', 'stock', 'market', 'financial', 'economy', 'bank', 'finance', 'trading',
    'gdp', 'economy', 'treasury', 'federal reserve', 'inflation', 'deflation',
    # 科技
    'tech', 'technology', 'ai', 'artificial intelligence', 'gpt', 'chatgpt', 'llm',
    'apple', 'google', 'microsoft', 'nvidia', 'tesla', 'spacex', 'elon', 'startup',
    'openai', 'anthropic', 'meta', 'amazon', 'software', 'internet', 'cyber'
]

# 黑名单:排除这些内容
EXCLUDED = [
    # 体育
    'world cup', 'football', 'soccer', 'nba', 'nfl', 'nhl', 'mlb', 'ufc',
    'tennis', 'golf', 'boxing', 'mma', 'olympics', 'super bowl', 'nascar',
    'formula 1', 'f1', 'fifa', 'champions league', 'premier league',
    # 游戏/娱乐
    'game', 'gaming', 'esports', 'lol', 'dota', 'csgo', 'valorant', 'playstation',
    'xbox', 'nintendo', 'switch', 'movie', 'film', 'album', 'song', 'concert',
    'music', 'entertainment', 'actor', 'actress', 'celebrity', 'awards', 'oscar',
    'grammy', 'festival', 'concert', 'tour', 'band', 'artist', 'spotify', 'netflix',
    # 其他
    'gta', 'grand theft auto', 'call of duty', 'fortnite', 'minecraft'
]

def get_markets():
    url = "https://gamma-api.polymarket.com/markets?closed=false&limit=500"
    r = requests.get(url, timeout=30)
    return r.json() if r.status_code == 200 else []

def is_filtered(m):
    question = m.get('question', '').lower()
    category = m.get('category', '').lower() if m.get('category') else ''
    text = question + ' ' + category

    # 黑名单:如果包含排除的关键词,直接过滤
    if any(kw in text for kw in EXCLUDED):
        return True

    # 白名单:必须包含至少一个允许的关键词
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
    """检查日期是否在未来一周到一年之间"""
    if not end_date: return False
    try:
        d = end_date.replace('Z','').split('+')[0]
        end_dt = datetime.fromisoformat(d) + timedelta(hours=8)
        now = datetime.now()
        days_until = (end_dt - now).days
        return days_min <= days_until <= days_max
    except: return False

def format_vol(v): v = float(v or 0); return f"${v/1e6:.2f}M" if v>=1e6 else f"${v/1e3:.1f}K" if v>=1e3 else f"${v:.0f}"
def format_pct(p): return f"{float(p or 0)*100:.1f}%" if p else "N/A"
def format_end(d): return d[:10] if d else "N/A"

def load_history():
    """加载历史数据"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
    except: pass
    return {}

def save_history(data):
    """保存历史数据"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")
        pass

def calculate_changes(current_price, history):
    """计算概率变化"""
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

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, json=data, timeout=30)
    return r.json().get('ok', False)

def send_document(html_content, date_str, max_retries=3):
    """发送HTML文件到Telegram,带重试机制"""
    filename = f"polymarket_report_{date_str}.html"

    # 保存HTML文件
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 发送到Telegram (带重试)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"

    for attempt in range(max_retries):
        try:
            with open(filename, 'rb') as f:
                files = {'document': (filename, f, 'text/html')}
                data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': f"📊 Polymarket Daily Report - {date_str}"}
                # 增加超时时间到 120 秒
                r = requests.post(url, data=data, files=files, timeout=(30, 120))

            # 打印详细响应用于调试
            print(f"Telegram API Response: {r.status_code}")
            print(f"Response body: {r.text}")

            return r.json().get('ok', False)

        except requests.exceptions.Timeout as e:
            print(f"Timeout on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                import time
                print(f"Waiting 5 seconds before retry...")
                time.sleep(5)
            else:
                print(f"All {max_retries} attempts failed.")
                return False
        except Exception as e:
            print(f"Error sending document: {e}")
            return False

    return False

def generate_html_report(markets, report_date, history):
    rd = report_date.strftime("%Y-%m-%d")
    now = datetime.now()

    # 调试：打印总数据量
    print(f"Total markets from API: {len(markets)}")
    filtered_count = 0
    expired_count = 0

    # 处理数据
    data = []
    error_count = 0

    # 打印前 5 个市场的分类信息用于调试
    print("\n=== Sample markets for debugging ===")
    for i, m in enumerate(markets[:5]):
        print(f"Market {i}: category='{m.get('category', '')}', question='{m.get('question', '')[:50]}...'")
    print("=== End sample ===\n")

    for m in markets:
        if is_filtered(m):
            filtered_count += 1
            continue
        if is_expired(m.get('endDate')):
            expired_count += 1
            continue
        try:
            prices = m.get('outcomePrices', [])
            # 处理 prices 可能是字符串化的数组的情况
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices)
                except Exception as parse_error:
                    print(f"Failed to parse prices string: {parse_error}, prices value: {prices[:100]}")
                    prices = []
            price = float(prices[0]) if prices and len(prices) > 0 else 0
            market_id = m.get('id', m.get('conditionId', ''))

            changes = calculate_changes(price, history.get(market_id, {}))

            data.append({
                'q': m.get('question','')[:70],
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
            print(f"Error processing market {m.get('id', 'unknown')}: {e}")
            print(f"Market data - question: {m.get('question', 'N/A')[:50]}, outcomePrices: {m.get('outcomePrices', 'N/A')[:100]}")
            continue

    print(f"Filtered by category: {filtered_count}")
    print(f"Expired: {expired_count}")
    print(f"Errors during processing: {error_count}")
    print(f"Valid markets in data: {len(data)}")

    # 打印第一个有效市场作为样本
    if data:
        print(f"Sample valid market: {data[0]}")

    # 更新历史数据 - 保留现有数据,正确更新价格
    new_history = history.copy()
    updated_count = 0
    new_markets_count = 0

    for m in markets:
        if is_filtered(m) or is_expired(m.get('endDate')): continue
        try:
            market_id = m.get('id', m.get('conditionId', ''))
            prices = m.get('outcomePrices', [])
            # 处理 prices 可能是字符串化的数组的情况
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices)
                except:
                    prices = []
            price = float(prices[0]) if prices and len(prices) > 0 else 0

            if market_id in new_history:
                # 已存在的市场:更新价格,保留旧的7d数据作为新的7d数据
                old_24h = new_history[market_id].get('price_24h', price)
                new_history[market_id]['price_7d'] = old_24h
                new_history[market_id]['price_24h'] = price
                new_history[market_id]['timestamp'] = now.isoformat()
                updated_count += 1
            else:
                # 新市场:初始化
                new_history[market_id] = {
                    'price_24h': price,
                    'price_7d': price,
                    'timestamp': now.isoformat()
                }
                new_markets_count += 1
        except Exception as e:
            print(f"Error updating history for market {m.get('id', 'unknown')}: {e}")
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

    # 生成HTML (简化样式以减小文件大小)
    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body{{font-family:sans-serif;background:#1a1a2e;color:#e4e4e4;padding:10px}}
.container{{max-width:800px;margin:0 auto}}
h1{{color:#00d4ff;text-align:center;padding:10px 0}}
.info{{text-align:center;gap:10px;display:flex;justify-content:center;margin:10px 0}}
.info span{{background:#1e3a5a;padding:5px 10px;border-radius:5px}}
.note{{background:#2d2d44;padding:10px;border-radius:5px;margin:10px 0;font-size:12px}}
.section{{background:#252538;padding:15px;margin:10px 0;border-radius:5px}}
.section h2{{color:#fff;margin:0 0 10px 0}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#1e3a5a;color:#00d4ff;padding:5px;text-align:left}}
td{{padding:5px;border-bottom:1px solid #333}}
.rank{{color:#00d4ff;font-weight:bold;text-align:center}}
.title{{color:#fff;max-width:300px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cat{{color:#888;font-size:10px}}
.prob{{padding:2px 6px;border-radius:3px;font-weight:bold}}
.high{{background:#004d26;color:#00ff88}}
.mid{{background:#4d3d00;color:#ffc107}}
.low{{background:#4d1a1a;color:#ff5252}}
.up{{color:#00ff88}}
.down{{color:#ff5252}}
.vol{{color:#ffc107}}
.date{{color:#888}}
</style>
</head>
<body>
<div class="container">
<h1>📊 Polymarket Daily Report - {rd}</h1>
<div class="info">
<span>📅 {rd}</span>
<span>⏰ 08:00 Beijing</span>
</div>
<div class="note">
ℹ️ Filtered: Sports/Entertainment/Gaming/Esports | Comparing: {by_rise[0]['comparing_time'] if by_rise else 'No historical data'}
</div>
'''

    def build_table(rows, title, rise=True, show_change=True):
        nonlocal html
        html += f'''<div class="section">
<h2>{'📈' if rise else '📉'} {title}</h2>
<table><tr><th>#</th><th>Event</th><th>Current</th><th>24h Δ</th><th>7d Δ</th><th>End Date</th><th>24h Vol</th><th>Total Vol</th></tr>'''
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
<td><div class='title'>{x['q']}</div><div class='cat'>{x['c']}</div></td>
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
    build_table(by_vt, "Top Total Volume (Historical)", True)
    build_table(by_v24, "Top 24h Volume", True)
    build_table(by_future, "Top Future High Probability (7d-1y)", True)

    html += f'''
<footer style="text-align:center;padding:10px;color:#666;font-size:10px">
<p>Generated: {rd} 08:00 Beijing | {by_rise[0]['comparing_time'] if by_rise else 'N/A'}</p>
</footer>
</div>
</body>
</html>'''

    return html

def main():
    print(f"Running at {datetime.now()}")

    # 打印环境变量用于调试
    print(f"TELEGRAM_TOKEN set: {bool(TELEGRAM_TOKEN)}")
    print(f"TELEGRAM_CHAT_ID set: {bool(TELEGRAM_CHAT_ID)}")

    # 打印所有环境变量（调试用）
    print("All environment variables:")
    for key, value in os.environ.items():
        if 'TELEGRAM' in key.upper():
            print(f"  {key}: {'***' if 'TOKEN' in key.upper() else value}")

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID is missing!")
        return

    history = load_history()
    print(f"Loaded history: {len(history)} markets")

    # 打印历史数据样本
    if history:
        sample_ids = list(history.keys())[:3]
        print(f"Sample history entries:")
        for mid in sample_ids:
            print(f"  {mid}: 24h={history[mid].get('price_24h')}, 7d={history[mid].get('price_7d')}")
    else:
        print("No history data found (first run)")

    markets = get_markets()
    print(f"Got {len(markets)} markets")

    report_date = datetime.now()
    date_str = report_date.strftime("%Y%m%d")

    # 生成HTML报告
    html = generate_html_report(markets, report_date, history)

    # 发送HTML文件到Telegram
    success = send_document(html, date_str)
    print(f"Document sent: {success}")

    if not success:
        # 如果文件发送失败，发送文本摘要
        summary = f"📊 Polymarket Report {date_str}\n\nMarkets: {len(markets)}\nHistory: {len(history)}\n\nReport file sent: {success}"
        send_telegram(summary)

if __name__ == "__main__":
    main()
