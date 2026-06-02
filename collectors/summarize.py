"""
collectors/summarize.py
───────────────────────
把抓到的推文交给 Claude API，逐条产出结构化分析:
  关键信息 / 提及标的 / 方向，并在最后给出标的汇总 + 核心主题。
输出格式对齐用户 Word 模板。

环境变量:
  ANTHROPIC_API_KEY
"""
from __future__ import annotations
import os, json, pathlib
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ENDPOINT = "https://api.anthropic.com/v1/messages"

SYSTEM = """你是一位买方投研助理，为基金经理整理隔夜美股/港股/科技 KOL 推文。
针对每条推文，输出严格的 JSON，字段:
  "summary":   一句话中文关键信息（提炼事实/观点，不要复述原文）
  "tickers":   提及标的数组，格式如 ["$NVDA","台积电"]，无则 []
  "direction": 一句话方向判断（看多/看空/中性 + 理由），无明确观点则填 "短评/无明确方向"
  "noise":     true/false —— 纯短评、emoji、无信息量的填 true
只输出 JSON 数组，顺序与输入一致，不要任何额外文字、不要 markdown 围栏。"""

THEME_SYSTEM = """你是买方投研主管。基于以下隔夜推文摘要，输出一个 JSON:
  "themes":  3-6 条隔夜核心主题数组，每条一句话中文
  "hot_tickers": 高频提及标的数组，按提及次数降序，格式 [{"ticker":"$NVDA","count":3}]
只输出 JSON，不要 markdown 围栏、不要多余文字。"""


def _call(system: str, user_content: str, model: str) -> str:
    if not API_KEY:
        raise RuntimeError("缺少 ANTHROPIC_API_KEY 环境变量")
    r = requests.post(ENDPOINT, headers={
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }, json={
        "model": model,
        "max_tokens": 4000,
        "system": system,
        "messages": [{"role": "user", "content": user_content}],
    }, timeout=120)
    r.raise_for_status()
    blocks = r.json().get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def _parse_json(s: str):
    s = s.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1].lstrip("json").strip() if "```" in s else s
    return json.loads(s)


def analyze_posts(items: list[dict], model: str, max_per: int) -> list[dict]:
    # 按账号截断，控制 token
    by_acct: dict[str, int] = {}
    trimmed = []
    for it in items:
        k = it["account_handle"]
        by_acct[k] = by_acct.get(k, 0) + 1
        if by_acct[k] <= max_per:
            trimmed.append(it)

    if not trimmed:
        return []

    payload = [{"i": idx, "account": it["account_display"], "text": it["text"]}
               for idx, it in enumerate(trimmed)]
    raw = _call(SYSTEM, json.dumps(payload, ensure_ascii=False), model)
    try:
        analyses = _parse_json(raw)
    except Exception as e:
        print(f"⚠️ 摘要 JSON 解析失败: {e}\n原始: {raw[:500]}")
        analyses = [{"summary": "(解析失败)", "tickers": [], "direction": "", "noise": False}
                    for _ in trimmed]

    for it, a in zip(trimmed, analyses):
        it["summary"] = a.get("summary", "")
        it["tickers"] = a.get("tickers", [])
        it["direction"] = a.get("direction", "")
        it["noise"] = a.get("noise", False)
    return trimmed


def derive_themes(items: list[dict], model: str) -> dict:
    digest = [{"account": it["account_display"],
               "summary": it.get("summary", ""),
               "tickers": it.get("tickers", [])}
              for it in items if not it.get("noise")]
    if not digest:
        return {"themes": [], "hot_tickers": []}
    raw = _call(THEME_SYSTEM, json.dumps(digest, ensure_ascii=False), model)
    try:
        return _parse_json(raw)
    except Exception as e:
        print(f"⚠️ 主题 JSON 解析失败: {e}")
        return {"themes": [], "hot_tickers": []}


if __name__ == "__main__":
    import yaml
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    items = json.loads((ROOT / ".cache" / "raw_tweets.json").read_text())
    model = cfg["summarize"]["model"]
    items = analyze_posts(items, model, cfg["summarize"]["max_posts_per_account"])
    themes = derive_themes(items, model)
    (ROOT / ".cache" / "analyzed.json").write_text(
        json.dumps({"items": items, "themes": themes}, ensure_ascii=False, indent=2))
    print(f"分析完成: {len(items)} 条, {len(themes.get('themes', []))} 主题")
