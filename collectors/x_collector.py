"""
collectors/x_collector.py
─────────────────────────
用 X API v2 (pay-per-use) 拉取名单内账号过去 N 小时的推文。

环境变量:
  X_BEARER_TOKEN   X 开发者后台 App 的 Bearer Token (OAuth2 app-only)

读取 config.yaml 的 accounts / window。
handle->user_id 解析结果缓存在 .cache/user_ids.json，避免每次重复付费。

输出: 标准化后的 list[dict]，字段见 normalize()。
"""
from __future__ import annotations
import os, json, time, pathlib, datetime as dt
import requests
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
ID_CACHE = CACHE_DIR / "user_ids.json"

API = "https://api.x.com/2"
BEARER = os.environ.get("X_BEARER_TOKEN", "")


def _headers():
    if not BEARER:
        raise RuntimeError("缺少 X_BEARER_TOKEN 环境变量")
    return {"Authorization": f"Bearer {BEARER}"}


def _get(url, params, max_retry=4):
    """带 429 退避的 GET。"""
    for attempt in range(max_retry):
        r = requests.get(url, headers=_headers(), params=params, timeout=30)
        if r.status_code == 429:
            wait = int(r.headers.get("x-rate-limit-reset", 0)) - int(time.time())
            wait = max(wait, 5) if wait < 120 else 60
            print(f"  429 限频，等 {wait}s 重试…")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"重试 {max_retry} 次仍失败: {url}")


def load_id_cache() -> dict:
    if ID_CACHE.exists():
        return json.loads(ID_CACHE.read_text())
    return {}


def save_id_cache(cache: dict):
    ID_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


def resolve_user_ids(handles: list[str]) -> dict:
    """handle -> {id, name, username}。命中缓存的不再请求（省钱）。"""
    cache = load_id_cache()
    missing = [h for h in handles if h.lower() not in cache]
    # X 支持一次最多 100 个 username 批量查
    for i in range(0, len(missing), 100):
        batch = missing[i:i + 100]
        data = _get(f"{API}/users/by",
                    {"usernames": ",".join(batch),
                     "user.fields": "name,username"})
        for u in data.get("data", []):
            cache[u["username"].lower()] = {
                "id": u["id"], "name": u["name"], "username": u["username"],
            }
        # 查不到的账号（handle 写错/账号不存在）记下来
        for err in data.get("errors", []):
            bad = err.get("value", "?")
            print(f"  ⚠️ 无法解析账号: @{bad}（handle 可能写错或账号不存在）")
    save_id_cache(cache)
    return cache


def fetch_user_tweets(user_id: str, start_iso: str) -> list[dict]:
    """拉单个用户 start_iso 之后的原创+回复推文（不含纯转推内容体）。"""
    params = {
        "max_results": 100,
        "start_time": start_iso,
        "tweet.fields": "created_at,public_metrics,referenced_tweets,lang,entities",
        "exclude": "retweets",  # 转推没正文，排除；引用推/回复保留
    }
    out, token = [], None
    while True:
        if token:
            params["pagination_token"] = token
        data = _get(f"{API}/users/{user_id}/tweets", params)
        out.extend(data.get("data", []))
        token = data.get("meta", {}).get("next_token")
        if not token:
            break
        time.sleep(1)  # 温和分页
    return out


def normalize(tweet: dict, acct: dict, tz_name: str) -> dict:
    """统一 schema，时间转成目标时区显示。"""
    from zoneinfo import ZoneInfo
    created = dt.datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
    local = created.astimezone(ZoneInfo(tz_name))
    m = tweet.get("public_metrics", {})
    return {
        "account_display": acct["display"],
        "account_handle": acct["username"],
        "tweet_id": tweet["id"],
        "url": f"https://x.com/{acct['username']}/status/{tweet['id']}",
        "created_utc": created.isoformat(),
        "created_local": local.strftime("%m/%d %H:%M"),
        "text": tweet.get("text", ""),
        "lang": tweet.get("lang", ""),
        "likes": m.get("like_count", 0),
        "retweets": m.get("retweet_count", 0),
        "replies": m.get("reply_count", 0),
    }


def collect(config: dict) -> list[dict]:
    accounts = config["accounts"]
    hours = config["window"]["hours"]
    tz_name = config["window"]["timezone"]

    start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"窗口起点 (UTC): {start_iso}")

    handles = [a["handle"] for a in accounts]
    id_map = resolve_user_ids(handles)

    items = []
    for a in accounts:
        h = a["handle"].lower()
        if h not in id_map:
            print(f"跳过 @{a['handle']}（未解析到 user_id）")
            continue
        u = id_map[h]
        acct = {"display": a["display"], "username": u["username"]}
        try:
            tweets = fetch_user_tweets(u["id"], start_iso)
        except Exception as e:
            print(f"  ⚠️ 拉取 @{a['handle']} 失败: {e}")
            continue
        for t in tweets:
            items.append(normalize(t, acct, tz_name))
        print(f"@{a['handle']}: {len(tweets)} 条")
        time.sleep(1)

    items.sort(key=lambda x: x["created_utc"], reverse=True)
    return items


if __name__ == "__main__":
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    data = collect(cfg)
    out = ROOT / ".cache" / "raw_tweets.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\n共 {len(data)} 条，已写入 {out}")
