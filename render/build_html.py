"""
render/build_html.py
────────────────────
把 analyzed.json 渲染成单页 HTML 日报，写到 docs/ 下（GitHub Pages 根目录）。
生成:
  docs/index.html              最新一期（群里发这个链接）
  docs/archive/YYYY-MM-DD.html 当日归档
"""
from __future__ import annotations
import json, pathlib, datetime as dt, html
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ARCH = DOCS / "archive"
ARCH.mkdir(parents=True, exist_ok=True)

NUM = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def esc(s: str) -> str:
    return html.escape(s or "")


def group_by_account(items):
    groups = {}
    for it in items:
        groups.setdefault(it["account_display"], []).append(it)
    # 每组内按时间倒序
    for v in groups.values():
        v.sort(key=lambda x: x["created_utc"], reverse=True)
    # 组按最新帖时间排序
    return sorted(groups.items(),
                  key=lambda kv: kv[1][0]["created_utc"], reverse=True)


def render(data: dict, tz_name="Asia/Shanghai") -> str:
    items = data["items"]
    themes = data.get("themes", {})
    now = dt.datetime.now(ZoneInfo(tz_name))
    win_end = now
    win_start = now - dt.timedelta(hours=24)
    groups = group_by_account(items)
    total = len(items)

    # ── 账号区块 ──
    sections = []
    for gi, (acct, posts) in enumerate(groups, 1):
        cards = []
        for pi, p in enumerate(posts):
            badge = NUM[pi] if pi < len(NUM) else f"{pi+1}"
            tickers = "".join(
                f'<span class="ticker">{esc(t)}</span>' for t in p.get("tickers", []))
            noise = p.get("noise")
            direction = "" if noise else f"""
              <div class="meta"><span class="ico">📊</span><span>{esc(p.get('direction',''))}</span></div>"""
            tick_row = f"""
              <div class="meta"><span class="ico">🏷️</span><span class="tickers">{tickers}</span></div>""" if tickers else ""
            cards.append(f"""
        <article class="card{' noise' if noise else ''}">
          <div class="card-head">
            <span class="badge">帖子{badge}</span>
            <span class="time">🕗 北京时间 {esc(p['created_local'])}</span>
            <a class="src" href="{esc(p['url'])}" target="_blank" rel="noopener">原帖 ↗</a>
          </div>
          <blockquote>{esc(p['text'])}</blockquote>
          <div class="meta"><span class="ico">📌</span><span>{esc(p.get('summary',''))}</span></div>
          {tick_row}{direction}
        </article>""")
        sections.append(f"""
      <section class="account">
        <h2><span class="anum">{gi}</span>{esc(acct)}
          <span class="count">窗口内新帖 {len(posts)} 条</span></h2>
        {''.join(cards)}
      </section>""")

    # ── 标的汇总 ──
    hot = themes.get("hot_tickers", [])
    hot_html = "".join(
        f'<span class="hot"><b>{esc(h.get("ticker",""))}</b><i>{h.get("count","")}</i></span>'
        for h in hot) or '<span class="dim">（无）</span>'

    # ── 核心主题 ──
    theme_list = themes.get("themes", [])
    themes_html = "".join(f"<li>{esc(t)}</li>" for t in theme_list) \
        or "<li class='dim'>（无）</li>"

    # ── 隔夜综述（约 500 字）──
    overview_html = esc(themes.get("overview", "")) or "（无）"

    return f"""<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>隔夜推特大V动态 · {now.strftime('%Y-%m-%d')}</title>
<style>
  :root{{
    --bg:#0b0e14; --panel:#141925; --panel2:#1b2230; --line:#2a3344;
    --ink:#e8ecf4; --dim:#8a94a8; --accent:#5eead4; --accent2:#fbbf24;
    --long:#34d399; --short:#f87171; --quote:#aeb8cc;
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);
    font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif;
    line-height:1.6;font-size:15px}}
  .wrap{{max-width:860px;margin:0 auto;padding:32px 20px 80px}}
  header.top{{border-bottom:1px solid var(--line);padding-bottom:20px;margin-bottom:8px}}
  h1{{font-size:26px;margin:0 0 10px;letter-spacing:.5px}}
  .sub{{color:var(--dim);font-size:13px;line-height:1.9}}
  .sub b{{color:var(--ink);font-weight:600}}
  section.account{{margin-top:34px}}
  section.account>h2{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
    font-size:19px;margin:0 0 14px;padding-bottom:10px;border-bottom:1px dashed var(--line)}}
  .anum{{display:inline-flex;width:26px;height:26px;border-radius:8px;
    background:var(--accent);color:#04201b;font-weight:700;align-items:center;
    justify-content:center;font-size:14px}}
  .count{{margin-left:auto;font-size:12px;color:var(--dim);font-weight:400}}
  .card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:16px 18px;margin-bottom:12px}}
  .card.noise{{opacity:.6}}
  .card-head{{display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap}}
  .badge{{background:var(--panel2);color:var(--accent);font-weight:600;font-size:12px;
    padding:3px 9px;border-radius:6px}}
  .time{{font-size:12px;color:var(--dim)}}
  .src{{margin-left:auto;font-size:12px;color:var(--accent);text-decoration:none}}
  .src:hover{{text-decoration:underline}}
  blockquote{{margin:0 0 12px;padding:10px 14px;background:#0e1320;border-left:3px solid var(--accent);
    border-radius:0 8px 8px 0;color:var(--quote);font-size:14px;white-space:pre-wrap;word-break:break-word}}
  .meta{{display:flex;gap:8px;align-items:flex-start;font-size:13.5px;margin:6px 0}}
  .meta .ico{{flex:none;opacity:.9}}
  .tickers{{display:flex;flex-wrap:wrap;gap:6px}}
  .ticker{{background:var(--panel2);border:1px solid var(--line);color:var(--accent2);
    font-size:12px;padding:2px 8px;border-radius:20px;font-weight:600}}
  .summary-block{{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:18px 20px;margin-top:34px}}
  .summary-block h2{{font-size:18px;margin:0 0 14px}}
  .overview{{margin:0;color:var(--quote);font-size:14.5px;line-height:1.95;text-align:justify}}
  .summary-top{{margin-top:18px}}
  .hots{{display:flex;flex-wrap:wrap;gap:8px}}
  .hot{{display:inline-flex;align-items:center;gap:6px;background:var(--panel2);
    border:1px solid var(--line);border-radius:8px;padding:5px 10px}}
  .hot b{{color:var(--accent2);font-size:13px}}
  .hot i{{font-style:normal;background:var(--accent);color:#04201b;border-radius:10px;
    padding:0 7px;font-size:11px;font-weight:700}}
  ol.themes{{margin:0;padding-left:20px}}
  ol.themes li{{margin:7px 0}}
  .dim{{color:var(--dim)}}
  footer{{margin-top:50px;padding-top:18px;border-top:1px solid var(--line);
    color:var(--dim);font-size:12px;text-align:center;line-height:1.8}}
  a{{color:var(--accent)}}
</style></head>
<body><div class="wrap">
  <header class="top">
    <h1>🌙 隔夜推特大V动态</h1>
    <div class="sub">
      监控时段：<b>{win_start.strftime('%Y-%m-%d %H:%M')} — {win_end.strftime('%m-%d %H:%M')}</b>（北京时间）<br>
      共 <b>{total}</b> 条新帖 · 覆盖 <b>{len(groups)}</b> 个账号 · 报告生成 {now.strftime('%Y-%m-%d %H:%M')}
    </div>
  </header>

  <div class="summary-block summary-top">
    <h2>📝 隔夜综述</h2>
    <p class="overview">{overview_html}</p>
  </div>
  <div class="summary-block">
    <h2>📊 隔夜高频提及标的</h2>
    <div class="hots">{hot_html}</div>
  </div>
  <div class="summary-block">
    <h2>🔑 隔夜核心主题</h2>
    <ol class="themes">{themes_html}</ol>
  </div>

  {''.join(sections) if sections else '<p class="dim" style="margin-top:40px">窗口内无新帖。</p>'}

  <footer>
    自动生成 · 数据源 X API · 仅供内部研究参考，非投资建议<br>
    内容为 KOL 个人观点的机器摘要，可能有误，决策前请核对原帖
  </footer>
</div></body></html>"""


def main():
    data = json.loads((ROOT / ".cache" / "analyzed.json").read_text())
    out = render(data)
    (DOCS / "index.html").write_text(out, encoding="utf-8")
    today = dt.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    (ARCH / f"{today}.html").write_text(out, encoding="utf-8")
    print(f"已生成 docs/index.html 和 archive/{today}.html")


if __name__ == "__main__":
    main()
