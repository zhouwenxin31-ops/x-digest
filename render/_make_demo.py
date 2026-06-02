"""生成一份 demo analyzed.json（用 Word 样例内容），让用户预览成品。
真实运行时这个文件由 collector+summarize 自动产生，不需要它。"""
import json, pathlib, datetime as dt
ROOT = pathlib.Path(__file__).resolve().parent.parent
def mk(disp, handle, tid, day, hhmm, local, text, summ, tickers, direction, noise=False):
    return {"account_display":disp,"account_handle":handle,"tweet_id":tid,
        "url":f"https://x.com/{handle}/status/{tid}",
        "created_utc":f"2026-06-0{day}T{hhmm}:00+00:00",
        "created_local":local,"text":text,"summary":summ,
        "tickers":tickers,"direction":direction,"noise":noise,
        "likes":0,"retweets":0,"replies":0}

items=[
 mk("Jukan @COMPUTEX","jukan05","1","2","00:03","08:03",
    "It is believed to be supply for Vera Rubin, making this one of the only cases where Mitsui's monopoly has been broken.",
    "乐天能源材料打破三井在AI电路箔领域垄断，为NVIDIA Vera Rubin供货",
    ["$NVDA"],"看多NVIDIA供应链，关注CCL/电路箔材料新供应商"),
 mk("Jukan @COMPUTEX","jukan05","2","1","23:44","07:44",
    "[Exclusive] Lotte Energy Materials to Supply AI Circuit Foil to NVIDIA Starting This Month...",
    "独家：韩国乐天能源材料本月起正式向NVIDIA供应AI电路箔，用于下一代GPU",
    ["$NVDA","乐天能源材料"],"看多NVIDIA产业链，关注韩国CCL/电路箔供应商"),
 mk("Serenity","aleabitoreddit","3","1","23:51","07:51",
    "I never thought I'd see the day where $GOOGL needs to raise $80b for AI capex… Berkshire $10B. Upstream ecosystem from $LITE to $AVGO to Mediatek to $TSM to $MU should go brrr.",
    "Google融资$80B用于AI资本开支，伯克希尔出资$10B参与，上游生态系统将大幅受益",
    ["$GOOGL","$BRK.A","$LITE","$AVGO","$TSM","$MU"],"强烈看多AI算力上游产业链，光通信→芯片→代工→存储全链条受益"),
 mk("Serenity","aleabitoreddit","4","1","20:01","04:01",
    "$SIVE is a laser chokepoint for photonics and are publicly validated by $GFS and $JBL.",
    "Sivers是光子学激光器关键瓶颈供应商，已获GFS和JBL验证，等待CPO起飞",
    ["$SIVE","$GFS","$LITE","$JBL"],"看多CPO/光通信产业链，$SIVE为核心标的"),
 mk("Serenity","aleabitoreddit","5","1","17:22","01:22",
    "I did say $AAOI was my favorite US optical long… +20.1% today. H1 entering H2 2027 will likely be that massive inflection point for photonics.",
    "AAOI当日大涨20.1%，类比当年SanDisk，预计2027年为光子学大拐点",
    ["$AAOI"],"强烈看多$AAOI，光通信赛道2027年迎来大爆发"),
 mk("kokycpcb @pcbanalysis","pcbanalysis","6","1","18:37","02:37",
    "Peak Performance",
    "短评，无具体信息",[],"短评/无明确方向",noise=True),
]
themes={"themes":[
  "AI Capex持续爆发：Google融资$80B、Nebius投€8B法国建数据中心、Anthropic Series H $65B，超大规模AI基建仍在加速",
  "光通信/CPO赛道升温：Serenity密集推荐$AAOI(+20.1%)、$SIVE、$LITE，认为2027年H1-H2为光子学大拐点",
  "NVIDIA供应链多元化：乐天能源材料打破三井垄断，本月起供应Vera Rubin电路箔",
  "云服务商分化：AWS利润率跳升领先，Azure/Google Cloud承压",
  "数据中心监管风险：美国50+地方暂停令，宾州立法要求数据中心付费",
],"hot_tickers":[
  {"ticker":"$NVDA","count":2},{"ticker":"$LITE","count":2},
  {"ticker":"$GOOGL","count":2},{"ticker":"$AAOI","count":1},
  {"ticker":"$SIVE","count":1},{"ticker":"$TSM","count":1},
]}
(ROOT/".cache").mkdir(exist_ok=True)
(ROOT/".cache"/"analyzed.json").write_text(json.dumps({"items":items,"themes":themes},ensure_ascii=False,indent=2))
print("demo analyzed.json written")
