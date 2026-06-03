"""
run.py — 主入口：抓取 → 摘要 → 渲染 HTML。
本地: python run.py
CI:   由 .github/workflows/digest.yml 调用
"""
import os, json, pathlib, yaml
from collectors import x_collector, summarize, news_collector
from render import build_html, build_news_html

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
    print("✅ 大V日报完成。docs/index.html 已更新")

    # ── ④ 新闻流追踪（仅每天定时刷新；手动 run 默认跳过，设 RUN_NEWS=1 可临时开启）──
    run_news = (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
                or os.environ.get("RUN_NEWS", "").lower() in ("1", "true", "yes"))
    if not run_news:
        print("④ 新闻流：本次跳过（仅每天定时刷新；手动开启请设 RUN_NEWS=1）")
    else:
        try:
            print("④ 新闻流：X 搜索 + 摘要…")
            groups = news_collector.collect_news(
                cfg["window"]["hours"], cfg["window"]["timezone"])
            news = summarize.summarize_news(groups, model)
            by_t = {i.get("ticker"): i for i in news.get("items", [])}
            for g in groups:
                g["analysis"] = by_t.get(g["ticker"], {})
            (ROOT / ".cache" / "news_analyzed.json").write_text(
                json.dumps({"overview": news.get("overview", ""), "groups": groups},
                           ensure_ascii=False, indent=2))
            build_news_html.main()
            print("✅ 新闻流完成。docs/news.html 已更新")
        except Exception as e:
            print(f"⚠️ 新闻流失败（不影响大V日报）: {e}")


if __name__ == "__main__":
    main()
