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
import os, re, json, time, pathlib
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ENDPOINT = "https://api.anthropic.com/v1/messages"

# 一次最多送多少条进模型，控制输出 token，避免被 max_tokens 截断
BATCH_SIZE = 12
MAX_TOKENS = 8000

SYSTEM = """你是一位买方投研助理，为基金经理整理隔夜美股/港股/科技 KOL 推文。
针对每条推文，输出严格的 JSON，字段:
  "i":         回填输入里的 i（整数），用于对齐
  "summary":   一句话中文关键信息（提炼事实/观点，不要复述原文）
  "tickers":   提及标的数组，格式如 ["$NVDA","台积电"]，无则 []
  "direction": 一句话方向判断（看多/看空/中性 + 理由），无明确观点则填 "短评/无明确方向"
  "noise":     true/false —— 纯短评、emoji、无信息量的填 true
只输出 JSON 数组，顺序与输入一致，不要任何额外文字、不要 markdown 围栏。"""

THEME_SYSTEM = """你是买方投研主管。基于以下隔夜推文摘要，输出一个 JSON:
  "overview": 一段约 500 字的中文综述，面向基金经理：串联隔夜最重要的信息流与主线逻辑，点出潜在的交易/配置含义。叙事连贯成段，不分点、不罗列原文、不堆砌套话。
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
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user_content}],
    }, timeout=120)
    r.raise_for_status()
    body = r.json()
    if body.get("stop_reason") == "max_tokens":
        # 输出被截断——交给上层走重试逻辑，不要喂给 json.loads
        raise ValueError("响应因 max_tokens 截断，JSON 不完整")
    blocks = body.get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def _parse_json(s: str):
    """稳健提取首个 JSON 数组/对象：去围栏、剥前后夹带文字。"""
    s = s.strip()
    # 去 ```json ... ``` 或 ``` ... ``` 围栏
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", s, re.S)
    if m:
        s = m.group(1).strip()
    # 截取第一个 [ 或 { 到最后一个 ] 或 }，剥离前后多余文字
    cands = [p for p in (s.find("["), s.find("{")) if p != -1]
    if cands:
        s = s[min(cands):]
    end = max(s.rfind("]"), s.rfind("}"))
    if end != -1:
        s = s[:end + 1]
    return json.loads(s)


def _analyze_batch(batch: list[dict], model: str):
    """单批分析；失败重试一次，仍失败返回 None 交调用方按批回退。"""
    payload = [{"i": it["_i"], "account": it["account_display"], "text": it["text"]}
               for it in batch]
    raw_body = json.dumps(payload, ensure_ascii=False)
    last_err = None
    for attempt in range(2):
        try:
            raw = _call(SYSTEM, raw_body, model)
            arr = _parse_json(raw)
            if not isinstance(arr, list):
                raise ValueError(f"期望数组，得到 {type(arr).__name__}")
            return arr
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    print(f"⚠️ 批次解析失败（{len(batch)} 条）: {last_err}")
    return None


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

    # 全局索引，便于按 i 对齐回填
    for idx, it in enumerate(trimmed):
        it["_i"] = idx
        it.setdefault("summary", "")
        it.setdefault("tickers", [])
        it.setdefault("direction", "")
        it.setdefault("noise", False)

    by_index = {it["_i"]: it for it in trimmed}
    fail_count = 0

    for s in range(0, len(trimmed), BATCH_SIZE):
        batch = trimmed[s:s + BATCH_SIZE]
        arr = _analyze_batch(batch, model)
        if arr is None:
            for it in batch:          # 仅该批回退，不殃及其它批
                it["summary"] = "(解析失败)"
            fail_count += len(batch)
            continue
        if all(isinstance(a, dict) and "i" in a for a in arr):
            for a in arr:             # 按 i 精确对齐
                it = by_index.get(a.get("i"))
                if it is None:
                    continue
                it["summary"] = a.get("summary", "") or ""
                it["tickers"] = a.get("tickers", []) or []
                it["direction"] = a.get("direction", "") or ""
                it["noise"] = bool(a.get("noise", False))
        else:
            for it, a in zip(batch, arr):   # 退化为顺序对齐
                if not isinstance(a, dict):
                    continue
                it["summary"] = a.get("summary", "") or ""
                it["tickers"] = a.get("tickers", []) or []
                it["direction"] = a.get("direction", "") or ""
                it["noise"] = bool(a.get("noise", False))

    if fail_count:
        print(f"⚠️ 共 {fail_count}/{len(trimmed)} 条回退为 (解析失败)")
    for it in trimmed:
        it.pop("_i", None)
    return trimmed


def derive_themes(items: list[dict], model: str) -> dict:
    digest = [{"account": it["account_display"],
               "summary": it.get("summary", ""),
               "tickers": it.get("tickers", [])}
              for it in items
              if not it.get("noise") and it.get("summary") not in ("", "(解析失败)")]
    if not digest:
        return {"overview": "", "themes": [], "hot_tickers": []}
    try:
        raw = _call(THEME_SYSTEM, json.dumps(digest, ensure_ascii=False), model)
        return _parse_json(raw)
    except Exception as e:
        print(f"⚠️ 主题 JSON 解析失败: {e}")
        return {"overview": "", "themes": [], "hot_tickers": []}


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
