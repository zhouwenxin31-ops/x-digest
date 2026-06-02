"""
collectors/notify.py — 把日报链接推到群（飞书/企业微信 webhook）。
可选。在 run.py 末尾或单独调用。
环境变量:
  WEBHOOK_URL    群机器人 webhook 地址
  PAGES_URL      你的 GitHub Pages 日报地址，如 https://<user>.github.io/x-digest/
注意：这是"向群里发消息"，属于代你发送的动作——脚本只在你配置了 WEBHOOK_URL
      时才会发，等于你已显式授权。不想自动发就别设这个变量。
"""
import os, datetime, requests

def push():
    url = os.environ.get("WEBHOOK_URL")
    pages = os.environ.get("PAGES_URL", "")
    if not url:
        print("未配置 WEBHOOK_URL，跳过群推送")
        return
    today = datetime.datetime.utcnow().strftime("%m-%d")
    # 飞书自定义机器人格式；企业微信把 payload 换成 {"msgtype":"text","text":{"content":...}}
    payload = {
        "msg_type": "text",
        "content": {"text": f"🌙 隔夜推特大V动态 {today} 已更新\n{pages}"},
    }
    r = requests.post(url, json=payload, timeout=15)
    print("群推送:", r.status_code)

if __name__ == "__main__":
    push()
