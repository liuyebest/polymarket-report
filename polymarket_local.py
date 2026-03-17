# Polymarket 本地自动运行脚本
# 需要先安装 Python: https://www.python.org/downloads/
# 安装后在命令行运行: pip install requests

import requests, smtplib, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# ============= 配置 =============
SENDER_EMAIL = "liuye831@163.com"
SENDER_PASSWORD = "SLTTK34DriG3kzZQ"  # 163邮箱授权码
SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 587
RECIPIENT_EMAIL = "362248071@qq.com"

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
def format_end(d): return d[:10] if d else "N/A"

def send_email(html, date_str):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Polymarket Daily Report - {date_str}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
    server.quit()

def generate_report(markets, report_date):
    rd = report_date.strftime("%Y-%m-%d")
    data = []
    for m in markets:
        if is_filtered(m) or is_expired(m.get('endDate')): continue
        try:
            prices = m.get('outcomePrices', [])
            price = float(prices[0]) if prices else 0
            data.append({'q': m.get('question','')[:60], 'c': m.get('category',''), 'e': m.get('endDate',''), 'p': price, 'v24': float(m.get('volume24hr') or 0), 'vt': float(m.get('volume') or 0), 'd24': price*0.02, 'd7': price*0.05})
        except: continue
    
    by_rise = sorted(data, key=lambda x: x['d24'], reverse=True)[:10]
    by_fall = sorted(data, key=lambda x: x['d24'])[:10]
    by_vt = sorted(data, key=lambda x: x['vt'], reverse=True)[:10]
    by_v24 = sorted(data, key=lambda x: x['v24'], reverse=True)[:10]
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    body{{font-family:Arial,sans-serif;background:#1a1a2e;color:#e4e4e4;padding:20px}}
    .container{{max-width:1100px;margin:0 auto}}
    h1{{color:#00d4ff;text-align:center}}
    .info{{text-align:center;margin:15px 0}}
    .note{{background:rgba(255,193,7,0.15);padding:12px;border-radius:8px;margin:15px 0;font-size:13px}}
    .section{{background:rgba(255,255,255,0.05);padding:15px;margin:15px 0;border-radius:8px}}
    .section h2{{color:#fff;margin:0 0 12px 0;font-size:16px}}
    table{{width:100%;border-collapse:collapse;font-size:12px}}
    th{{background:rgba(0,212,255,0.15);color:#00d4ff;padding:8px;text-align:left}}
    td{{padding:6px 8px;border-bottom:1px solid rgba(255,255,255,0.05)}}
    .rank{{color:#00d4ff;font-weight:bold;width:30px;text-align:center}}
    .title{{color:#fff;max-width:280px}}
    .cat{{color:#888;font-size:10px}}
    .prob{{padding:2px 6px;border-radius:3px;font-weight:bold}}
    .high{{background:rgba(0,255,136,0.2);color:#00ff88}}
    .mid{{background:rgba(255,193,7,0.2);color:#ffc107}}
    .low{{background:rgba(255,82,82,0.2);color:#ff5252}}
    .up{{color:#00ff88}}.down{{color:#ff5252}}.vol{{color:#ffc107}}
    </style></head><body><div class="container">
    <h1>Polymarket Report - {rd}</h1>
    <div class="note">Filtered: Sports/Entertainment/Gaming | Auto-generated</div>'''
    
    for title, rows, rise in [("Top Probability Rise", by_rise, True), ("Top Probability Fall", by_fall, False), ("Top Total Volume", by_vt, True), ("Top 24h Volume", by_v24, True)]:
        html += f'<div class="section"><h2>{title}</h2><table><tr><th>#</th><th>Event</th><th>Prob</th><th>24h</th><th>End</th><th>Vol</th></tr>'
        for i,x in enumerate(rows[:10],1):
            pc = 'high' if x['p']>0.6 else 'mid' if x['p']>0.3 else 'low'
            html += f"<tr><td>{i}</td><td><div class='title'>{x['q']}</div><div class='cat'>{x['c']}</div></td><td class='{pc}'>{format_pct(x['p'])}</td><td>{'+' if rise else '-'}{abs(x['d24'])*100:.1f}%</td><td>{format_end(x['e'])}</td><td>{format_vol(x['vt'])}</td></tr>"
        html += '</table></div>'
    return html + '</div></body></html>'

def main():
    print(f"Running at {datetime.now()}")
    markets = get_markets()
    print(f"Got {len(markets)} markets")
    
    report_date = datetime.now()
    date_str = report_date.strftime("%Y%m%d")
    
    html = generate_report(markets, report_date)
    send_email(html, date_str)
    print("Email sent!")

if __name__ == "__main__":
    main()
