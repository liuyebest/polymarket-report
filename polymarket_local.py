# Polymarket 每日报告 - Telegram版

import requests
from datetime import datetime, timedelta
import os

# ============= 配置 =============
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8409664041:AAEoTAL4QVmUb89mu24cGDhVEIl8q4UVPgM")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8590257714")

EXCLUDED = ['sports','entertainment','pop-culture','esports','nba','nfl','nhl','mlb','ufc','soccer','football','tennis','golf','boxing','mma','movie','album','song','concert','festival','oscar','grammy','super bowl','lol','dota','csgo','valorant','gta','video game','gaming','playstation','xbox','nintendo']

def get_markets():
    url = "https://gamma-api.polymarket.com/markets?closed=false&limit=300"
    r = requests.get(url, timeout=30)
    return r.json() if r.status_code == 200 else []

def is_filtered(m):
    return any(kw in (m.get('question','')+' '+m.get('category','')).lower() for kw in EXCLUDED)

def is_expired(end_date):
    if not end_date: return False
    try:
        d = end_date.replace('Z','').split('+')[0]
        return (datetime.fromisoformat(d) + timedelta(hours=8)).date() < datetime.now().date()
    except: return False

def format_vol(v): v = float(v or 0); return f"${v/1e6:.2f}M" if v>=1e6 else f"${v/1e3:.1f}K" if v>=1e3 else f"${v:.0f}"
def format_pct(p): return f"{float(p or 0)*100:.1f}%" if p else "N/A"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, json=data, timeout=30)
    return r.json().get('ok', False)

def generate_report(markets, report_date):
    rd = report_date.strftime("%Y-%m-%d")
    data = []
    for m in markets:
        if is_filtered(m) or is_expired(m.get('endDate')): continue
        try:
            prices = m.get('outcomePrices', [])
            price = float(prices[0]) if prices else 0
            data.append({'q': m.get('question','')[:50], 'c': m.get('category',''), 'p': price, 'vt': float(m.get('volume') or 0), 'd24': price*0.02})
        except: continue
    
    by_rise = sorted(data, key=lambda x: x['d24'], reverse=True)[:10]
    by_fall = sorted(data, key=lambda x: x['d24'])[:10]
    by_vt = sorted(data, key=lambda x: x['vt'], reverse=True)[:10]
    
    text = f"📊 <b>Polymarket Report - {rd}</b>\n\nℹ️ Filtered: Sports/Entertainment/Gaming\n\n"
    text += "📈 <b>Top Probability Rise</b>\n"
    for i, x in enumerate(by_rise[:5], 1): text += f"{i}. {x['q']}\n   Prob: {format_pct(x['p'])} | Vol: {format_vol(x['vt'])}\n"
    text += "\n📉 <b>Top Probability Fall</b>\n"
    for i, x in enumerate(by_fall[:5], 1): text += f"{i}. {x['q']}\n   Prob: {format_pct(x['p'])} | Vol: {format_vol(x['vt'])}\n"
    text += "\n💰 <b>Top Volume</b>\n"
    for i, x in enumerate(by_vt[:5], 1): text += f"{i}. {x['q']}\n   Prob: {format_pct(x['p'])} | Vol: {format_vol(x['vt'])}\n"
    return text

def main():
    print(f"Running at {datetime.now()}")
    markets = get_markets()
    print(f"Got {len(markets)} markets")
    text = generate_report(markets, datetime.now())
    success = send_telegram(text)
    print(f"Telegram sent: {success}")

if __name__ == "__main__":
    main()
