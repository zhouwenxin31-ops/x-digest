"""
run.py — 主入口：抓取 → 摘要 → 渲染 HTML。
本地: python run.py
CI:   由 .github/workflows/digest.yml 调用
"""
import json, pathlib, yaml
from collectors import x_collector, summarize
from render import build_html

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())

    print("① 抓取推文…")
    items = x_collector.collect(cfg)
    (ROOT / ".cache").mkdir(exist_ok=True)
    (ROOT / ".cache" / "raw_tweets.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2))

    print("② Claude 摘要…")
    model = cfg["summarize"]["model"]
    items = summarize.analyze_posts(items, model, cfg["summarize"]["max_posts_per_account"])
    themes = summarize.derive_themes(items, model)
    (ROOT / ".cache" / "analyzed.json").write_text(
        json.dumps({"items": items, "themes": themes}, ensure_ascii=False, indent=2))

    print("③ 渲染 HTML…")
    build_html.main()
    print("✅ 完成。docs/index.html 已更新")


if __name__ == "__main__":
    main()
