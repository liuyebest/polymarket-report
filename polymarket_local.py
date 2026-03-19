"""
Polymarket 每日报告生成器 - V2

5 个维度 TOP10，全部直接使用 Gamma API 内置字段，无需本地历史数据：
  oneDayPriceChange   — 24h 概率变化
  oneWeekPriceChange  — 7d  概率变化
  volumeNum           — 历史总交易量
  volume24hr          — 24h 交易量
  lastTradePrice      — 当前概率
"""

import requests
from datetime import datetime, timezone

# ── 配置 ──────────────────────────────────────────────────
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"
FETCH_LIMIT   = 500

EXCLUDED = [
    # 体育赛事
    'world cup', 'football', 'soccer', 'nba', 'nfl', 'nhl', 'mlb', 'ufc',
    'tennis', 'golf', 'boxing', 'mma', 'olympics', 'super bowl', 'nascar',
    'formula 1', ' f1 ', 'fifa', 'champions league', 'premier league',
    'nba finals', 'world series', 'stanley cup', 'championship', 'tournament',
    'qualify for the 2026', 'nhl stanley cup', 'fifa world cup',
    # 体育俱乐部
    'borussia dortmund', 'napoli', 'manchester', 'arsenal', 'liverpool',
    'real madrid', 'barcelona', 'bayern munich', 'juventus', 'inter milan',
    'ac milan', 'bundesliga', 'serie a', 'la liga',
    'carolina hurricanes', 'florida panthers', 'edmonton oilers', 'dallas stars',
    'colorado avalanche', 'vegas golden knights', 'tampa bay lightning',
    # 游戏/电竞
    'gaming', 'esports', 'league of legends', 'dota', 'csgo', 'valorant',
    'playstation', 'xbox', 'nintendo', 'video game', 'gamer',
    'pubg', 'overwatch', 'roblox', 'grand theft auto', 'call of duty',
    'fortnite', 'minecraft', 'gta vi',
    # 娱乐/电影/音乐
    'movie', 'film', 'album', 'song', 'concert', 'music award',
    'actor', 'actress', 'celebrity', 'oscar', 'grammy', 'emmy',
    'box office', 'playboi carti', 'rihanna',
]

# ── 工具函数 ──────────────────────────────────────────────

def is_excluded(text: str) -> bool:
    t = (text or '').lower()
    return any(kw in t for kw in EXCLUDED)

def is_expired(end_date: str) -> bool:
    if not end_date:
        return False
    try:
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        return end < datetime.now(timezone.utc)
    except Exception:
        return False

def f(val) -> float:
    try:
        return float(val) if val is not None else 0.0
    except Exception:
        return 0.0

def pct(val: float, sign=True) -> str:
    s = '+' if (sign and val >= 0) else ''
    return f"{s}{val*100:.2f}%"

def money(val: float) -> str:
    if val >= 1_000_000:
        return f"${val/1_000_000:.2f}M"
    if val >= 1_000:
        return f"${val/1_000:.1f}K"
    return f"${val:.0f}"

# ── 数据获取 ──────────────────────────────────────────────

def fetch_markets():
    print("正在从 Gamma API 获取市场数据...")
    r = requests.get(GAMMA_API_URL, params={'closed': 'false', 'limit': FETCH_LIMIT})
    r.raise_for_status()
    data = r.json()
    print(f"  获取到 {len(data)} 个市场")
    return data

def filter_markets(markets):
    out = []
    for m in markets:
        if is_excluded(m.get('question', '')) or is_excluded(m.get('description', '')):
            continue
        if is_expired(m.get('endDate')):
            continue
        out.append(m)
    print(f"  过滤后剩余: {len(out)} 个有效市场")
    return out

# ── 排序函数 ──────────────────────────────────────────────

def rank_24h_rise(markets, n=10):
    valid = [m for m in markets if m.get('oneDayPriceChange') is not None]
    return sorted(valid, key=lambda x: x['oneDayPriceChange'], reverse=True)[:n]

def rank_24h_fall(markets, n=10):
    valid = [m for m in markets if m.get('oneDayPriceChange') is not None]
    return sorted(valid, key=lambda x: x['oneDayPriceChange'])[:n]

def rank_total_volume(markets, n=10):
    return sorted(markets, key=lambda x: f(x.get('volumeNum')), reverse=True)[:n]

def rank_24h_volume(markets, n=10):
    return sorted(markets, key=lambda x: f(x.get('volume24hr')), reverse=True)[:n]

def rank_future_prob(markets, n=10):
    now = datetime.now(timezone.utc)
    future = []
    for m in markets:
        ed = m.get('endDate')
        if not ed:
            continue
        try:
            end = datetime.fromisoformat(ed.replace('Z', '+00:00'))
            days = (end - now).days
            if 7 <= days <= 365:
                future.append(m)
        except Exception:
            continue
    return sorted(future, key=lambda x: f(x.get('lastTradePrice')), reverse=True)[:n]

# ── HTML 生成 ─────────────────────────────────────────────

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: #0d1117;
    color: #c9d1d9;
    padding: 28px 16px;
    line-height: 1.5;
}

.page-header {
    text-align: center;
    margin-bottom: 32px;
}
.page-header h1 {
    font-size: 2rem;
    color: #e6edf3;
    letter-spacing: 1px;
}
.page-header .sub {
    margin-top: 6px;
    color: #8b949e;
    font-size: .9rem;
}

.meta-bar {
    display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
    margin-bottom: 32px;
}
.chip {
    background: #21262d; border: 1px solid #30363d;
    border-radius: 20px; padding: 4px 14px;
    font-size: .82rem; color: #8b949e;
}

/* ── 单个 section ── */
.section {
    margin-bottom: 36px;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    overflow: hidden;
}

.section-header {
    padding: 14px 20px;
    background: #1c2128;
    border-bottom: 1px solid #30363d;
    display: flex; align-items: center; gap: 10px;
}
.section-header .icon { font-size: 1.3rem; }
.section-header .title { font-size: 1.05rem; font-weight: 700; color: #e6edf3; }
.section-header .sort-key {
    margin-left: auto;
    font-size: .78rem; color: #8b949e;
    background: #21262d; border: 1px solid #30363d;
    border-radius: 12px; padding: 2px 10px;
}

/* ── 表格 ── */
table {
    width: 100%;
    border-collapse: collapse;
    font-size: .88rem;
}
thead th {
    background: #1c2128;
    color: #8b949e;
    font-weight: 600;
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid #30363d;
    white-space: nowrap;
}
tbody tr {
    border-bottom: 1px solid #21262d;
    transition: background .15s;
}
tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: #1c2128; }
td {
    padding: 10px 14px;
    vertical-align: middle;
}

/* 列宽 */
.col-rank  { width: 36px; text-align: center; color: #8b949e; font-weight: 600; }
.col-q     { min-width: 220px; color: #c9d1d9; line-height: 1.4; }
.col-prob  { width: 90px;  text-align: right; white-space: nowrap; }
.col-d1    { width: 110px; text-align: right; white-space: nowrap; }
.col-d7    { width: 110px; text-align: right; white-space: nowrap; }
.col-vol   { width: 120px; text-align: right; white-space: nowrap; }
.col-vol24 { width: 120px; text-align: right; white-space: nowrap; }
.col-date  { width: 100px; text-align: right; white-space: nowrap; color: #8b949e; }

/* 数值样式 */
.prob-val  { color: #58a6ff; font-weight: 700; }
.up        { color: #f85149; font-weight: 700; }   /* 上升 = 红色 */
.dn        { color: #3fb950; font-weight: 700; }   /* 下降 = 绿色 */
.flat      { color: #8b949e; }
.vol-val   { color: #bc8cff; }
.rank-num  { font-size: .8rem; color: #6e7681; }

/* 响应式 */
@media (max-width: 700px) {
    .col-d7, .col-vol, .col-date { display: none; }
    table { font-size: .8rem; }
}

.footer {
    text-align: center; color: #484f58;
    margin-top: 40px; font-size: .8rem;
}
"""

def change_cell(val, css_class):
    """渲染变化值单元格"""
    if val is None:
        return f'<td class="{css_class}"><span class="flat">—</span></td>'
    cls = 'up' if val > 0 else ('dn' if val < 0 else 'flat')
    sign = '+' if val > 0 else ''
    return f'<td class="{css_class}"><span class="{cls}">{sign}{val*100:.2f}%</span></td>'

def build_table(markets, *, show_end_date=False):
    """生成统一格式的表格（所有榜单都展示：当前概率、较前一天、较7天前、总交易量、24h交易量）"""
    extra_th = '<th class="col-date">截止日期</th>' if show_end_date else ''

    rows = []
    for i, m in enumerate(markets, 1):
        q       = m.get('question', 'N/A')
        price   = f(m.get('lastTradePrice'))
        ch_1d   = m.get('oneDayPriceChange')
        ch_7d   = m.get('oneWeekPriceChange')
        vol_all = f(m.get('volumeNum'))
        vol_24h = f(m.get('volume24hr'))

        # 排名高亮
        rank_style = ''
        if i == 1:   rank_style = 'style="color:#ffd700"'
        elif i == 2: rank_style = 'style="color:#c0c0c0"'
        elif i == 3: rank_style = 'style="color:#cd7f32"'

        # 概率
        prob_html = f'<span class="prob-val">{price*100:.1f}%</span>'

        # 变化列
        td_1d = change_cell(ch_1d, 'col-d1')
        td_7d = change_cell(ch_7d, 'col-d7')

        # 交易量
        vol_all_html = f'<span class="vol-val">{money(vol_all)}</span>'
        vol_24h_html = f'<span class="vol-val">{money(vol_24h)}</span>'

        # 截止日期
        extra_td = ''
        if show_end_date:
            ed = m.get('endDate', '')
            date_str = '—'
            if ed:
                try:
                    dt = datetime.fromisoformat(ed.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d')
                except Exception:
                    pass
            extra_td = f'<td class="col-date">{date_str}</td>'

        rows.append(f"""
        <tr>
          <td class="col-rank"><span {rank_style}>{i}</span></td>
          <td class="col-q">{q}</td>
          <td class="col-prob">{prob_html}</td>
          {td_1d}
          {td_7d}
          <td class="col-vol">{vol_all_html}</td>
          <td class="col-vol24">{vol_24h_html}</td>
          {extra_td}
        </tr>""")

    rows_html = '\n'.join(rows)
    return f"""
    <table>
      <thead>
        <tr>
          <th class="col-rank">#</th>
          <th class="col-q">事件</th>
          <th class="col-prob">当前概率</th>
          <th class="col-d1">较前一天</th>
          <th class="col-d7">较7天前</th>
          <th class="col-vol">总交易量</th>
          <th class="col-vol24">24h交易量</th>
          {extra_th}
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>"""

def section(icon, title, sort_key_label, table_html):
    return f"""
  <div class="section">
    <div class="section-header">
      <span class="icon">{icon}</span>
      <span class="title">{title}</span>
      <span class="sort-key">排序依据: {sort_key_label}</span>
    </div>
    {table_html}
  </div>"""

def generate_html(markets):
    now     = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    date_str= now.strftime('%Y-%m-%d')

    r1 = rank_24h_rise(markets)
    r2 = rank_24h_fall(markets)
    r3 = rank_total_volume(markets)
    r4 = rank_24h_volume(markets)
    r5 = rank_future_prob(markets)

    sections_html = ''.join([
        section('📈', '概率上涨最快 TOP10',
                '24h 概率变化（降序）',
                build_table(r1, show_end_date=True)),
        section('📉', '概率下降最快 TOP10',
                '24h 概率变化（升序）',
                build_table(r2, show_end_date=True)),
        section('💰', '历史交易量最大 TOP10',
                '历史总交易量',
                build_table(r3, show_end_date=True)),
        section('🔥', '24h 交易量最大 TOP10',
                '24h 新增交易量',
                build_table(r4, show_end_date=True)),
        section('🎯', '未来高概率事件 TOP10',
                '当前概率（截止日期: 未来 7 天 ~ 1 年）',
                build_table(r5, show_end_date=True)),
    ])

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Polymarket 每日报告 {date_str}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="page-header">
    <h1>Polymarket 每日报告</h1>
    <p class="sub">生成时间: {now_str} &nbsp;|&nbsp; 数据来源: gamma-api.polymarket.com</p>
  </div>

  <div class="meta-bar">
    <span class="chip">有效市场: {len(markets)} 个</span>
    <span class="chip">「较前一天」= oneDayPriceChange</span>
    <span class="chip">「较前一周」= oneWeekPriceChange</span>
    <span class="chip">「历史总交易量」= volumeNum</span>
    <span class="chip">「24h交易量」= volume24hr</span>
  </div>

  {sections_html}

  <div class="footer">
    数据来源: polymarket.com &nbsp;|&nbsp; 生成时间: {now_str}
  </div>
</body>
</html>"""

# ── 主程序 ────────────────────────────────────────────────

def main():
    print("=" * 56)
    print("Polymarket 每日报告生成器 V2  (无历史数据)")
    print("=" * 56)

    markets_raw = fetch_markets()
    markets     = filter_markets(markets_raw)

    if not markets:
        print("没有找到有效市场数据，退出。")
        return

    html     = generate_html(markets)
    filename = f"polymarket_report_{datetime.now().strftime('%Y%m%d')}.html"

    with open(filename, 'w', encoding='utf-8') as fh:
        fh.write(html)

    print(f"\n报告已生成: {filename}")
    print("5 个维度 TOP10 全部使用 Gamma API 内置字段，无需本地历史数据。")

if __name__ == '__main__':
    main()


