# 🌙 x-digest · 隔夜推特大V动态

每天北京时间早 9:30 前自动汇总监控名单里 X 大V 过去 24h 的推文，
用 Claude 逐条提炼「关键信息 / 提及标的 / 方向」，生成一页 HTML 日报，
发布到 GitHub Pages，群里发一个链接即可。

## 它做什么
1. 按 `config.yaml` 名单，用 X API v2 拉每个账号过去 24h 的原创/引用推文
2. 调 Claude API 逐条结构化摘要 + 汇总高频标的与核心主题
3. 渲染成 `docs/index.html`（样式见仓库），并归档到 `docs/archive/`
4. GitHub Actions 定时跑 + 自动部署 Pages；可选推送链接到飞书/企业微信群

---

## 一次性配置

### 1. X API（必需，付费）
- 去 https://developer.x.com 用要监控用的账号登录
- 建 Project → 建 App → 走 pay-per-use onboarding，绑卡 + 充值 credits
- 在 Console **设置月度 spending cap**（防失控；你这量约 $20–60/月）
- 复制 App 的 **Bearer Token**

### 2. Anthropic API（必需）
- console.anthropic.com 拿一个 API key

### 3. 填名单
编辑 `config.yaml`，把 handle 核对准确（**写错会拉不到人**）。
名单里 `flowgod` / `shortseller` 这两个我没拿到确切 handle，
请去 X 上确认真实 handle 后替换，否则它们会被自动跳过。

### 4. GitHub 配置
- 把本仓库推到你的 GitHub
- **Settings → Secrets and variables → Actions** 添加：
  - `X_BEARER_TOKEN`
  - `ANTHROPIC_API_KEY`
  - （可选）`WEBHOOK_URL`、`PAGES_URL` —— 想自动发群再加
- **Settings → Pages → Source 选 GitHub Actions**
- 部署后你的链接是 `https://<你的用户名>.github.io/<仓库名>/`

---

## 跑起来
- **自动**：每天 01:15 UTC（≈北京 9:15）触发。GitHub cron 高峰常延迟 5–15 分钟，
  所以排在 9:15 以尽量赶在 9:30 前出报告。
- **手动**：Actions 页面 → x-digest → Run workflow。
- **本地调试**：
  ```bash
  pip install -r requirements.txt
  export X_BEARER_TOKEN=...   ANTHROPIC_API_KEY=...
  python run.py
  open docs/index.html
  ```

## 成本
- X API：按量，你这名单约 **$20–60/月**（每账号每日均 1 帖 ≈ $0.15/月）
- Claude API：每天一次摘要，**极低**
- GitHub Actions + Pages：**免费**

## 注意
- 摘要是机器生成、可能有误，报告页脚已注明"非投资建议、决策前核对原帖"
- handle→user_id 解析结果缓存在 `.cache/user_ids.json`，只在首次/新增账号时付费解析
- 群推送是"代你发消息"的动作：只有配置了 `WEBHOOK_URL` 才会发；不想自动发就别设

## 之后可扩展（已预留结构）
- 研报 alert 邮件解析（Gmail）
- 持仓：Futu OpenAPI（自己组合）/ EDGAR·披露易·akshare（市场）
- 美股个股新闻：Finnhub `company-news`
