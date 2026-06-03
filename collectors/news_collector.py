"""
collectors/news_collector.py
────────────────────────────
按 watchlist.yaml 用 X API v2 recent-search 搜每个标的过去 N 小时的讨论/新闻。
复用 x_collector 的鉴权 (_headers) 与 429 退避 (_get)。

注意：recent-search 端点需 X API Basic 档及以上（与拉用户时间线同档）。
若 token 档位不足会返回 403——已做单标的容错，不会拖垮整条流水线。

输出: list[{name,ticker,sector,query, tweets:[{text,author,url,created_local,likes,...}]}]
"""
from __future__ import annotations
import time, datetime as dt, pathlib
import yaml
from zoneinfo import ZoneInfo
from . import x_collector as xc   # 复用 API / _get / _headers

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEARCH_URL = f"{xc.API}/tweets/search/recent"


def _search(query: str, start_iso: str, max_results: int = 10) -> list[dict]:
    """调用 recent-search，返回标准化推文列表。"""
    params = {
        "query": query,
        "start_time": start_iso,
        "max_results": max(10, min(max_results, 100)),
        "tweet.fields": "created_at,public_metrics,lang",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    data = xc._get(SEARCH_URL, params)
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    out = []
    for t in data.get("data", []):
        u = users.get(t.get("author_id"), {})
        m = t.get("public_metrics", {})
        out.append({
            "text": t.get("text", ""),
            "lang": t.get("lang", ""),
            "author": u.get("username", ""),
            "url": f"https://x.com/{u.get('username','i')}/status/{t['id']}",
            "created_utc": t["created_at"],
            "likes": m.get("like_count", 0),
            "retweets": m.get("retweet_count", 0),
            "replies": m.get("reply_count", 0),
        })
    return out


def collect_news(hours: int = 24, tz_name: str = "Asia/Shanghai") -> list[dict]:
    cfg = yaml.safe_load((ROOT / "watchlist.yaml").read_text())
    hours = cfg.get("window_hours", hours)
    maxr = cfg.get("max_results", 10)
    start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"新闻流窗口起点 (UTC): {start_iso}")

    groups = []
    for w in cfg["watchlist"]:
        try:
            tw = _search(w["query"], start_iso, maxr)
        except Exception as e:
            print(f"  ⚠️ 搜索 {w['name']}（{w['ticker']}）失败: {e}")
            tw = []
        for t in tw:
            c = dt.datetime.fromisoformat(t["created_utc"].replace("Z", "+00:00"))
            t["created_local"] = c.astimezone(ZoneInfo(tz_name)).strftime("%m/%d %H:%M")
        tw.sort(key=lambda x: (x["likes"] + x["retweets"]), reverse=True)
        groups.append({**w, "tweets": tw})
        print(f"{w['name']}（{w['ticker']}）: {len(tw)} 条")
        time.sleep(1)
    return groups


if __name__ == "__main__":
    import json
    g = collect_news()
    (ROOT / ".cache").mkdir(exist_ok=True)
    (ROOT / ".cache" / "news_raw.json").write_text(
        json.dumps(g, ensure_ascii=False, indent=2))
    print(f"\n共 {len(g)} 个标的，已写入 .cache/news_raw.json")
