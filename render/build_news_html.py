"""
render/build_news_html.py
─────────────────────────
把 news_analyzed.json 渲染成「隔夜新闻流追踪」单页 docs/news.html。
数据源 Yahoo Finance（yfinance）。按行业二级分组，每个标的只显示一段 ~100字 AI 总结
+ 情绪标签，不展示新闻原文。与 build_html.py 共用同一套深色视觉。
"""
from __future__ import annotations
import json, pathlib, datetime as dt, html
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)


def esc(s: str) -> str:
    return html.escape(s or "")


def _senti_class(s: str) -> str:
    if "多" in (s or ""):
        return "long"
    if "空" in (s or ""):
        return "short"
    return "neu"


def _company_card(g: dict) -> str:
    a = g.get("analysis") or {}
    n = len(g.get("articles") or [])
    summary = a.get("summary", "")
    if n and summary:
        senti = a.get("sentiment", "中性")
        badge = f'<span class="senti {_senti_class(senti)}">{esc(senti)}</span>'
        body = f'<div class="nsum">{esc(summary)}</div>' \
               f'<div class="src">来源 Yahoo Finance · 基于 {n} 条 24h 新闻</div>'
    else:
        badge = '<span class="senti neu dim">无新闻</span>'
        body = '<div class="nsum dim">过去 24h 内 Yahoo 无相关新闻。</div>'
    return f"""
      <article class="ncard{'' if (n and summary) else ' empty'}">
        <div class="ncard-head">
          <span class="cname">{esc(g.get('name',''))}</span>
          <span class="cticker">{esc(g.get('ticker',''))}</span>
          {badge}
        </div>
        {body}
      </article>"""


def render(data: dict, tz_name: str = "Asia/Shanghai") -> str:
    groups = data.get("groups", [])
    now = dt.datetime.now(ZoneInfo(tz_name))
    win_start = now - dt.timedelta(hours=24)
    total = len(groups)
    active = sum(1 for g in groups if (g.get("articles") and (g.get("analysis") or {}).get("summary")))

    order, by_sec = [], {}
    for g in groups:
        sec = g.get("sector", "其他")
        if sec not in by_sec:
            by_sec[sec] = []
            order.append(sec)
        by_sec[sec].append(g)

    sections = ""
    for sec in order:
        cards = "".join(_company_card(g) for g in by_sec[sec])
        sections += f"""
      <section class="sec">
        <h2><span class="anum">{esc(sec)}</span>
          <span class="count">{len(by_sec[sec])} 个标的</span></h2>
        {cards}
      </section>"""

    return f"""<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>隔夜新闻流追踪 · {now.strftime('%Y-%m-%d')}</title>
<style>
  :root{{
    --bg:#0b0e14; --panel:#141925; --panel2:#1b2230; --line:#2a3344;
    --ink:#e8ecf4; --dim:#8a94a8; --accent:#5eead4; --accent2:#fbbf24;
    --long:#34d399; --short:#f87171; --neu:#94a3b8; --quote:#aeb8cc;
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
  .nav{{display:flex;gap:10px;margin:18px 0 6px}}
  .nav a{{padding:7px 14px;border:1px solid var(--line);border-radius:20px;
    color:var(--dim);text-decoration:none;font-size:13px}}
  .nav a.on{{background:var(--accent);color:#04201b;border-color:var(--accent);font-weight:600}}
  section.sec{{margin-top:30px}}
  section.sec>h2{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
    font-size:19px;margin:0 0 14px;padding-bottom:10px;border-bottom:1px dashed var(--line)}}
  .anum{{display:inline-flex;padding:3px 12px;border-radius:8px;
    background:var(--accent);color:#04201b;font-weight:700;font-size:14px}}
  .count{{margin-left:auto;font-size:12px;color:var(--dim);font-weight:400}}
  .ncard{{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:16px 18px;margin-bottom:12px}}
  .ncard.empty{{opacity:.5}}
  .ncard-head{{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}}
  .cname{{font-weight:600;font-size:16px}}
  .cticker{{background:var(--panel2);border:1px solid var(--line);color:var(--accent2);
    font-size:12px;padding:2px 8px;border-radius:6px;font-weight:600}}
  .senti{{font-size:12px;padding:2px 10px;border-radius:20px;font-weight:600;border:1px solid var(--line)}}
  .senti.long{{color:#04201b;background:var(--long)}}
  .senti.short{{color:#2a0b0b;background:var(--short)}}
  .senti.neu{{color:var(--ink);background:var(--panel2)}}
  .nsum{{color:var(--quote);font-size:14.5px;line-height:1.9;text-align:justify}}
  .src{{margin-top:8px;font-size:11.5px;color:var(--dim)}}
  .dim{{color:var(--dim)}}
  footer{{margin-top:50px;padding-top:18px;border-top:1px solid var(--line);
    color:var(--dim);font-size:12px;text-align:center;line-height:1.8}}
  a{{color:var(--accent)}}
</style></head>
<body><div class="wrap">
  <header class="top">
    <h1>📰 隔夜新闻流追踪</h1>
    <div class="sub">
      监控时段：<b>{win_start.strftime('%Y-%m-%d %H:%M')} — {now.strftime('%m-%d %H:%M')}</b>（北京时间）· 数据源 Yahoo Finance<br>
      覆盖 <b>{total}</b> 个标的 · 其中 <b>{active}</b> 个有 24h 新闻 · 报告生成 {now.strftime('%Y-%m-%d %H:%M')}
    </div>
    <nav class="nav"><a href="index.html">🌙 大V动态</a><a class="on" href="news.html">📰 新闻流追踪</a></nav>
  </header>

  {sections if sections else '<p class="dim" style="margin-top:40px">名单内暂无数据。</p>'}

  <footer>
    自动生成 · 数据源 Yahoo Finance · 仅供内部研究参考，非投资建议<br>
    内容为公开新闻的机器摘要，可能有误或遗漏，决策前请核对原始信息
  </footer>
</div></body></html>"""


def main():
    path = ROOT / ".cache" / "news_analyzed.json"
    data = json.loads(path.read_text()) if path.exists() else {"groups": []}
    (DOCS / "news.html").write_text(render(data), encoding="utf-8")
    print("已生成 docs/news.html")


if __name__ == "__main__":
    main()
