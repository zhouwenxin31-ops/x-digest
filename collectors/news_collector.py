"""
collectors/news_collector.py
────────────────────────────
按 watchlist.yaml 用 yfinance 拉每个标的过去 N 小时的 Yahoo Finance 新闻。
免费、无需 API key。Yahoo 对美股/日股覆盖好，港/台覆盖弱、A股基本没有。
yfinance 延迟导入：未安装时不影响大V日报。

输出: list[{name,ticker,sector,yahoo, articles:[{title,summary,publisher,url,published_local,published_utc}]}]
"""
from __future__ import annotations
import datetime as dt, pathlib
import yaml
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _parse(it: dict) -> dict:
    c = it.get("content", it) or {}
    prov = c.get("provider") or {}
    url = (c.get("canonicalUrl") or {}).get("url") \
        or (c.get("clickThroughUrl") or {}).get("url") or ""
    return {
        "title": c.get("title", ""),
        "summary": c.get("summary") or c.get("description") or "",
        "publisher": prov.get("displayName", "") if isinstance(prov, dict) else "",
        "url": url,
        "pubDate": c.get("pubDate") or "",
    }


def collect_news(hours: int = 24, tz_name: str = "Asia/Shanghai") -> list[dict]:
    import yfinance as yf  # 延迟导入
    cfg = yaml.safe_load((ROOT / "watchlist.yaml").read_text())
    hours = cfg.get("window_hours", hours)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    tz = ZoneInfo(tz_name)
    print(f"Yahoo 新闻窗口: 过去 {hours}h（截止 {cutoff:%Y-%m-%d %H:%M} UTC）")

    groups = []
    for w in cfg["watchlist"]:
        arts = []
        try:
            raw = yf.Ticker(w["yahoo"]).news or []
            for it in raw:
                a = _parse(it)
                if not a["title"] or not a["pubDate"]:
                    continue
                try:
                    pub = dt.datetime.fromisoformat(a["pubDate"].replace("Z", "+00:00"))
                except Exception:
                    continue
                if pub < cutoff:
                    continue
                a["published_local"] = pub.astimezone(tz).strftime("%m/%d %H:%M")
                a["published_utc"] = pub.isoformat()
                arts.append(a)
            arts.sort(key=lambda x: x["published_utc"], reverse=True)
        except Exception as e:
            print(f"  ⚠️ 拉取 {w['name']}（{w['yahoo']}）失败: {e}")
        groups.append({**w, "articles": arts})
        print(f"{w['name']}（{w['yahoo']}）: 24h 内 {len(arts)} 条")
    return groups


if __name__ == "__main__":
    import json
    g = collect_news()
    (ROOT / ".cache").mkdir(exist_ok=True)
    (ROOT / ".cache" / "news_raw.json").write_text(
        json.dumps(g, ensure_ascii=False, indent=2))
    print(f"\n共 {len(g)} 个标的，已写入 .cache/news_raw.json")
