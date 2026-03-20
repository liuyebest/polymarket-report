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
import os
import json

# ── 配置 ──────────────────────────────────────────────────
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"
TAG_CLASSIFICATION_FILE = "tag_classification.json"

# 需要保留的分类（使用标签分类系统）
ALLOWED_CATEGORIES = ['politics', 'crypto', 'business', 'geopolitics', 'science']

# ── 工具函数 ──────────────────────────────────────────────

def load_tag_classification():
    """加载标签分类数据"""
    import os
    cwd = os.getcwd()
    abs_path = os.path.abspath(TAG_CLASSIFICATION_FILE)
    print(f"  当前工作目录: {cwd}")
    print(f"  标签分类文件路径: {abs_path}")
    print(f"  文件是否存在: {os.path.exists(abs_path)}")

    try:
        with open(TAG_CLASSIFICATION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        file_size = os.path.getsize(abs_path)
        print(f"  文件大小: {file_size} bytes")
        cats = data.get('categories', {})
        tag_to_markets = data.get('tag_to_markets', {})
        total_market_ids = sum(len(v) for v in tag_to_markets.values())
        print(f"  分类数量: {len(cats)}, 标签数量: {len(tag_to_markets)}, 市场ID总数: {total_market_ids}")
        for cat_id, cat_info in cats.items():
            print(f"    [{cat_id}] 标签数: {len(cat_info.get('tags', []))}")
        return data
    except FileNotFoundError:
        print(f"  [警告] 未找到标签分类文件: {TAG_CLASSIFICATION_FILE}")
        print(f"  [提示] 请先运行: python build_tag_categories.py")
        return None
    except Exception as e:
        print(f"  [错误] 加载标签分类文件失败: {e}")
        return None


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
    """
    从 Gamma API 获取所有市场数据（使用分页）
    API 限制每次最多返回 500 条，使用 offset 分页获取全部数据
    """
    print("正在从 Gamma API 获取市场数据...")
    
    all_markets = []
    offset = 0
    limit = 500
    
    while True:
        params = {'closed': 'false', 'limit': limit, 'offset': offset}
        r = requests.get(GAMMA_API_URL, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        
        print(f"  获取 offset={offset}: {len(data)} 个市场")
        
        if not data:
            break
        
        all_markets.extend(data)
        offset += limit
        
        # 如果返回数量少于limit，说明是最后一页
        if len(data) < limit:
            break
        
        # 安全限制，防止无限循环
        if offset > 20000:
            print(f"  [警告] offset 超过安全限制，停止获取")
            break
    
    print(f"  总计获取到 {len(all_markets)} 个市场")
    return all_markets

def filter_markets(markets, classification=None):
    """过滤市场：使用标签分类筛选、过滤已过期、交易量低于10000的"""
    out = []
    excluded_count = 0
    low_volume_count = 0
    expired_count = 0

    # 如果有标签分类数据，使用标签筛选
    if classification is not None:
        # 收集所有允许的分类标签
        allowed_tags = set()
        for cat_id in ALLOWED_CATEGORIES:
            cat_tags = classification['categories'].get(cat_id, {}).get('tags', [])
            allowed_tags.update(cat_tags)

        # 收集所有允许的市场ID
        allowed_market_ids = set()
        for tag in allowed_tags:
            market_ids = classification['tag_to_markets'].get(tag, [])
            allowed_market_ids.update(market_ids)

        for m in markets:
            # 使用标签分类筛选
            market_id = str(m.get('id', ''))
            if market_id not in allowed_market_ids:
                excluded_count += 1
                continue

            # 过滤已过期
            if is_expired(m.get('endDate')):
                expired_count += 1
                continue

            # 过滤低交易量（总交易量 < 10,000 USD）
            volume = f(m.get('volumeNum'))
            if volume < 10000:
                low_volume_count += 1
                continue

            out.append(m)
    else:
        # 如果没有标签分类数据，跳过分类筛选（仅过滤过期和低交易量）
        print("  [警告] 标签分类数据不可用，跳过分类筛选")
        for m in markets:
            # 过滤已过期
            if is_expired(m.get('endDate')):
                expired_count += 1
                continue

            # 过滤低交易量（总交易量 < 10,000 USD）
            volume = f(m.get('volumeNum'))
            if volume < 10000:
                low_volume_count += 1
                continue

            out.append(m)

    print(f"  过滤详情:")
    if classification is not None:
        print(f"    - 分类不符合: {excluded_count} 个")
    print(f"    - 已过期: {expired_count} 个")
    print(f"    - 低交易量(<10K): {low_volume_count} 个")
    print(f"  过滤后剩余: {len(out)} 个有效市场")
    return out

# ── 排序函数 ──────────────────────────────────────────────

def rank_24h_rise(markets, n=10):
    """按24h绝对值变化降序排序（概率上涨最快）"""
    def calc_abs_change(m):
        ch = m.get('oneDayPriceChange')
        if ch is None or ch <= -1:
            return -999  # 无效值排到最后
        price = f(m.get('lastTradePrice'))
        historical_price = price / (1 + ch)
        # 检查历史价格是否合理（应该在 0 到 1 之间）
        if historical_price < 0 or historical_price > 1:
            return -999  # 无效值排到最后
        return price - historical_price  # 返回绝对值变化

    valid = [m for m in markets if m.get('oneDayPriceChange') is not None]
    return sorted(valid, key=calc_abs_change, reverse=True)[:n]

def rank_24h_fall(markets, n=10):
    """按24h绝对值变化升序排序（概率下降最快）"""
    def calc_abs_change(m):
        ch = m.get('oneDayPriceChange')
        if ch is None or ch <= -1:
            return 999  # 无效值排到最后
        price = f(m.get('lastTradePrice'))
        historical_price = price / (1 + ch)
        # 检查历史价格是否合理（应该在 0 到 1 之间）
        if historical_price < 0 or historical_price > 1:
            return 999  # 无效值排到最后
        return price - historical_price  # 返回绝对值变化

    valid = [m for m in markets if m.get('oneDayPriceChange') is not None]
    return sorted(valid, key=calc_abs_change)[:n]

def rank_total_volume(markets, n=10):
    return sorted(markets, key=lambda x: f(x.get('volumeNum')), reverse=True)[:n]

def rank_24h_volume(markets, n=10):
    return sorted(markets, key=lambda x: f(x.get('volume24hr')), reverse=True)[:n]

def rank_24h_volume_excluding(markets, exclude_ids=None, n=10):
    """按24h交易量排序，排除指定的市场ID"""
    if exclude_ids is None:
        exclude_ids = set()
    else:
        exclude_ids = set(exclude_ids)

    filtered = [m for m in markets if str(m.get('id', '')) not in exclude_ids]
    return sorted(filtered, key=lambda x: f(x.get('volume24hr')), reverse=True)[:n]

def rank_total_volume_excluding(markets, exclude_ids=None, n=10):
    """按总交易量排序，排除指定的市场ID"""
    if exclude_ids is None:
        exclude_ids = set()
    else:
        exclude_ids = set(exclude_ids)

    filtered = [m for m in markets if str(m.get('id', '')) not in exclude_ids]
    return sorted(filtered, key=lambda x: f(x.get('volumeNum')), reverse=True)[:n]

def rank_24h_rise_excluding(markets, exclude_ids=None, n=10):
    """按24h绝对值变化降序排序（概率上涨最快），排除指定的市场ID"""
    if exclude_ids is None:
        exclude_ids = set()
    else:
        exclude_ids = set(exclude_ids)

    filtered = [m for m in markets if str(m.get('id', '')) not in exclude_ids]

    def calc_abs_change(m):
        ch = m.get('oneDayPriceChange')
        if ch is None or ch <= -1:
            return -999  # 无效值排到最后
        price = f(m.get('lastTradePrice'))
        historical_price = price / (1 + ch)
        if historical_price < 0 or historical_price > 1:
            return -999  # 无效值排到最后
        return price - historical_price  # 返回绝对值变化

    valid = [m for m in filtered if m.get('oneDayPriceChange') is not None]
    return sorted(valid, key=calc_abs_change, reverse=True)[:n]

def rank_24h_fall_excluding(markets, exclude_ids=None, n=10):
    """按24h绝对值变化升序排序（概率下降最快），排除指定的市场ID"""
    if exclude_ids is None:
        exclude_ids = set()
    else:
        exclude_ids = set(exclude_ids)

    filtered = [m for m in markets if str(m.get('id', '')) not in exclude_ids]

    def calc_abs_change(m):
        ch = m.get('oneDayPriceChange')
        if ch is None or ch <= -1:
            return 999  # 无效值排到最后
        price = f(m.get('lastTradePrice'))
        historical_price = price / (1 + ch)
        if historical_price < 0 or historical_price > 1:
            return 999  # 无效值排到最后
        return price - historical_price  # 返回绝对值变化

    valid = [m for m in filtered if m.get('oneDayPriceChange') is not None]
    return sorted(valid, key=calc_abs_change)[:n]

def rank_future_prob_excluding(markets, exclude_ids=None, n=10):
    """筛选未来1个月到1年的高概率事件，排除指定的市场ID"""
    if exclude_ids is None:
        exclude_ids = set()
    else:
        exclude_ids = set(exclude_ids)

    filtered = [m for m in markets if str(m.get('id', '')) not in exclude_ids]

    now = datetime.now(timezone.utc)
    future = []
    for m in filtered:
        ed = m.get('endDate')
        if not ed:
            continue
        try:
            end = datetime.fromisoformat(ed.replace('Z', '+00:00'))
            days = (end - now).days
            if 30 <= days <= 365:  # 1个月到1年
                future.append(m)
        except Exception:
            continue
    return sorted(future, key=lambda x: f(x.get('lastTradePrice')), reverse=True)[:n]

def rank_future_prob(markets, n=10):
    """筛选未来1个月到1年的高概率事件"""
    now = datetime.now(timezone.utc)
    future = []
    for m in markets:
        ed = m.get('endDate')
        if not ed:
            continue
        try:
            end = datetime.fromisoformat(ed.replace('Z', '+00:00'))
            days = (end - now).days
            if 30 <= days <= 365:  # 1个月到1年
                future.append(m)
        except Exception:
            continue
    return sorted(future, key=lambda x: f(x.get('lastTradePrice')), reverse=True)[:n]

def rank_by_category_24h_volume(markets, classification, category_id, n=5):
    """按分类筛选市场，并按24h交易量排序"""
    if classification is None:
        return []

    # 获取该分类的标签
    cat_tags = classification['categories'].get(category_id, {}).get('tags', [])
    if not cat_tags:
        return []

    # 收集该分类下的市场ID
    allowed_market_ids = set()
    for tag in cat_tags:
        market_ids = classification['tag_to_markets'].get(tag, [])
        allowed_market_ids.update(market_ids)

    # 筛选该分类的市场
    category_markets = []
    for m in markets:
        market_id = str(m.get('id', ''))
        if market_id in allowed_market_ids:
            category_markets.append(m)

    # 按24h交易量排序
    return sorted(category_markets, key=lambda x: f(x.get('volume24hr')), reverse=True)[:n]

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

def change_cell(val, current_price, css_class):
    """
    渲染变化值单元格
    val 是相对值变化（百分比，如 0.015 表示 +1.5%）
    需要计算绝对值变化 = 当前价格 - 推算的历史价格
    """
    if val is None:
        return f'<td class="{css_class}"><span class="flat">—</span></td>'

    # 避免除零错误和异常值
    if val <= -1:
        return f'<td class="{css_class}"><span class="flat">N/A</span></td>'

    # 计算历史价格（相对值公式）
    historical_price = current_price / (1 + val)

    # 检查历史价格是否合理（应该在 0 到 1 之间）
    if historical_price < 0 or historical_price > 1:
        return f'<td class="{css_class}"><span class="flat">N/A</span></td>'

    # 计算绝对值变化
    absolute_change = current_price - historical_price

    # 判断涨跌
    cls = 'up' if absolute_change > 0 else ('dn' if absolute_change < 0 else 'flat')
    sign = '+' if absolute_change > 0 else ''

    return f'<td class="{css_class}"><span class="{cls}">{sign}{absolute_change*100:.2f}%</span></td>'

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

        # 变化列（传入当前价格用于计算绝对值变化）
        td_1d = change_cell(ch_1d, price, 'col-d1')
        td_7d = change_cell(ch_7d, price, 'col-d7')

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

def generate_html(markets, classification=None):
    now     = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    date_str= now.strftime('%Y-%m-%d')

    # 生成分类主题榜单，并收集已在分类榜单中的市场ID
    category_sections = []
    category_market_ids = set()  # 收集所有分类榜单中的市场ID
    if classification is not None:
        categories_info = {
            'politics': {'icon': '🏛️', 'name': '政治'},
            'crypto': {'icon': '₿', 'name': '加密货币'},
            'business': {'icon': '💼', 'name': '商业经济'},
            'geopolitics': {'icon': '🌍', 'name': '地缘政治'},
            'science': {'icon': '🔬', 'name': '科学技术'},
        }

        for cat_id, cat_info in categories_info.items():
            cat_markets = rank_by_category_24h_volume(markets, classification, cat_id, n=5)
            if cat_markets:
                # 收集这些市场的ID，用于后续去重
                for m in cat_markets:
                    category_market_ids.add(str(m.get('id', '')))
                section_html = section(
                    cat_info['icon'],
                    f'{cat_info["name"]} TOP5',
                    '24h 交易量（降序）',
                    build_table(cat_markets, show_end_date=True)
                )
                category_sections.append(section_html)

    # 生成其他榜单，排除已在分类榜单中出现的市场（全局去重）
    r1 = rank_24h_rise_excluding(markets, exclude_ids=category_market_ids, n=10)
    r2 = rank_24h_fall_excluding(markets, exclude_ids=category_market_ids, n=10)
    r3 = rank_total_volume_excluding(markets, exclude_ids=category_market_ids, n=10)
    r4 = rank_24h_volume_excluding(markets, exclude_ids=category_market_ids, n=10)
    r5 = rank_future_prob_excluding(markets, exclude_ids=category_market_ids, n=10)

    # 汇总所有榜单
    sections_html = ''.join(category_sections + [
        section('📈', '概率上涨最快 TOP10',
                '24h 概率变化（降序）',
                build_table(r1, show_end_date=True)),
        section('📉', '概率下降最快 TOP10',
                '24h 概率变化（升序）',
                build_table(r2, show_end_date=True)),
        section('💰', '历史交易量最大 TOP10 (已剔除前面重复项)',
                '历史总交易量（已剔除分类榜单中的市场）',
                build_table(r3, show_end_date=True)),
        section('🔥', '24h 交易量最大 TOP10 (已剔除前面重复项)',
                '24h 新增交易量（已剔除分类榜单中的市场）',
                build_table(r4, show_end_date=True)),
        section('🎯', '未来高概率事件 TOP10 (已剔除前面重复项)',
                '当前概率（已剔除分类榜单中的市场）（截止日期: 未来 1 个月 ~ 1 年）',
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

# ── Telegram 发送 ───────────────────────────────────────────

def send_telegram_document(html_content, date_str, cat_status=""):
    """发送HTML文件到Telegram"""
    telegram_token = os.environ.get('TELEGRAM_TOKEN')
    telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not telegram_token or not telegram_chat_id:
        print("[ERROR] TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set, skipping Telegram send")
        return False
    
    filename = f"polymarket_report_{date_str}.html"
    
    # 保存HTML文件
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[SENDING] Sending to Telegram: {filename}")
    
    # 发送到Telegram
    url = f"https://api.telegram.org/bot{telegram_token}/sendDocument"
    
    try:
        with open(filename, 'rb') as f:
            files = {'document': (filename, f, 'text/html')}
            caption = f"📊 Polymarket Daily Report - {date_str}"
            if cat_status:
              caption += f"\n{cat_status}"
            data = {'chat_id': telegram_chat_id, 'caption': caption}

            r = requests.post(url, data=data, files=files, timeout=(30, 120))
        
        print(f"[RESPONSE] Telegram API Status: {r.status_code}")
        print(f"[RESPONSE] Response body: {r.text[:200]}...")
        
        return r.json().get('ok', False)
    except Exception as e:
        print(f"[ERROR] Telegram send error: {e}")
        return False

# ── 主程序 ────────────────────────────────────────────────

def main():
    print("=" * 56)
    print("Polymarket 每日报告生成器 V2  (标签分类筛选)")
    print("=" * 56)

    # 加载标签分类数据
    print("\n加载标签分类数据...")
    classification = load_tag_classification()
    if classification is None:
        print("  [警告] 标签分类数据不可用，将跳过分类筛选")
    else:
        print(f"  分类数据加载成功!")
        print(f"  允许的分类: {ALLOWED_CATEGORIES}")

    markets_raw = fetch_markets()
    markets     = filter_markets(markets_raw, classification)

    if not markets:
        print("没有找到有效市场数据，退出。")
        return

    html     = generate_html(markets, classification)
    filename = f"polymarket_report_{datetime.now().strftime('%Y%m%d')}.html"

    with open(filename, 'w', encoding='utf-8') as fh:
        fh.write(html)

    print(f"\n报告已生成: {filename}")
    print("5 个维度 TOP10 + 5 个分类主题 TOP5 全部使用 Gamma API 内置字段，无需本地历史数据。")

    # 发送到 Telegram
    date_str = datetime.now().strftime('%Y%m%d')
    cat_status = "✅ 含5个分类TOP5" if classification is not None else "⚠️ 无分类TOP5（tag_classification.json未找到）"
    print(f"\n报告状态: {cat_status}")
    success = send_telegram_document(html, date_str, cat_status)

    print(f"[RESULT] Telegram send: {'SUCCESS' if success else 'FAILED'}")

if __name__ == '__main__':
    main()
