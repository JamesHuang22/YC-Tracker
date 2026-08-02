# YC Tracker — Design Document

## 1. 为什么做这个

我每天花时间跟踪 YC 创业公司——哪些融到钱了、哪些死了、哪些值得关注。市面上没有一个工具专门做这个。Crunchbase 太贵太泛，YC 官方目录只有静态信息。

解决我自己的问题：一个自动化的 YC 公司状态追踪器。

## 2. 核心功能（V1）

### 数据层
- 爬 YC 官方目录获取所有 batch 的公司基础信息（名称、描述、标签、location）
- 每天自动搜索 Google News，检测融资新闻
- 每周自动检测公司网站是否还活着（HTTP status）
- 用 LLM 提取新闻中的融资轮次、金额、估值

### 展示层（Telegram bot + GitHub README）
- 每周一发一份报告到 Telegram：「本周 3 家公司融到钱，2 家可能死了」
- GitHub README 自动更新 badges/stats
- （后期）简单 web dashboard

### 不做（V1）
- 不做用户系统
- 不做 Crunchbase API 集成（付费墙）
- 不做前端 dashboard

## 3. 技术栈

| 组件 | 选择 | 原因 |
|---|---|---|
| 语言 | Python | 爬虫、数据处理最顺手 |
| 数据库 | SQLite / Supabase | SQLite 起步够用，以后可升 Supabase |
| 爬虫 | httpx + BeautifulSoup | YC 目录是静态页面 |
| 定时任务 | Hermes cron | 已有环境 |
| AI 提取 | DeepSeek API | 已有 key，便宜 |
| 部署 | Hermes 本机 | 暂时不需要服务器 |
| 通知渠道 | Telegram bot | 已有 bot |

## 4. 数据结构

```sql
CREATE TABLE companies (
    id TEXT PRIMARY KEY,           -- yc-{slug}
    name TEXT NOT NULL,
    slug TEXT,
    batch TEXT,                    -- "S26", "W26", etc.
    description TEXT,
    industry TEXT,
    location TEXT,
    website TEXT,
    linkedin_url TEXT,
    founders TEXT,                 -- JSON array of names
    team_size INTEGER,
    total_funding_usd INTEGER,
    last_funding_round TEXT,       -- "Seed", "Series A", etc.
    last_funding_date DATE,
    status TEXT DEFAULT 'active',   -- active, acquired, dead, unknown
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE news_events (
    id SERIAL PRIMARY KEY,
    company_id TEXT REFERENCES companies(id),
    title TEXT,
    url TEXT,
    source TEXT,
    published_at TIMESTAMP,
    summary TEXT,
    event_type TEXT,               -- funding, acquisition, product_launch, etc.
    funding_amount_usd INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE health_checks (
    id SERIAL PRIMARY KEY,
    company_id TEXT REFERENCES companies(id),
    checked_at TIMESTAMP DEFAULT NOW(),
    website_reachable BOOLEAN,
    website_status_code INTEGER,
    notes TEXT
);
```

## 5. 数据流

```
YC 目录爬虫 (每天)
  │
  ▼
本地 SQLite
  │
  ├──→ Google News RSS (每天) → LLM 提取 → 写入 news_events
  │
  ├──→ Website Health Check (每周) → 写入 health_checks
  │
  └──→ 生成报告 → Telegram / GitHub README
```

## 6. V1 交付清单

### Phase 1 — 基础数据（2 天）
- [ ] 爬虫：抓 YC 目录所有 batch 的公司
- [ ] 数据库：建表，写入基础数据
- [ ] Hermes cron：每天跑一次爬虫

### Phase 2 — 新闻检测（2 天）
- [ ] Google News RSS 搜索 YC 公司名
- [ ] DeepSeek LLM 提取融资信息
- [ ] 写入 news_events 表

### Phase 3 — 报告输出（1 天）
- [ ] Telegram 每周报告
- [ ] GitHub README 自动更新
- [ ] Website health check

## 7. 限制

- YC 目录爬虫可能被 ban（降低频率 + User-Agent 轮换）
- Crunchbase 付费墙 —— 新闻只靠 Google News
- "公司死了" 的判断靠 website 挂了 + 半年无新闻，不一定准确

## 8. V2 — 信号扫描系统（核心升级）

### 8.1 目标

MVP (Phase 1) 只存了静态的公司信息。V2 的目标是**自动扫描 + 时间序列对比**：

> 每周自动跑一次 AI agent，扫描每个 batch 里所有公司的多源信号
> （LinkedIn / Google News / X / 网站），给每家公司打一个 **development_score**，
> 存成带时间戳的 **snapshot**。
> 下次扫描时对比上次 snapshot，判断"这家公司最近有没有真正发展"。

### 8.2 信号来源（按价值排序）

| 来源 | 看什么 | 获取方式 |
|---|---|---|
| 🥇 **LinkedIn** | 团队人数变化、扩招职位、高层变动 | 公司页 JSON (yc_oss) / opencli (Agent Reach) |
| 🥈 **Google News** | 融资、收购、产品发布、合作 | RSS 搜索 + DeepSeek 提取 |
| 🥉 **X/Twitter** | 创始人发帖频率、产品讨论热度 | twitter-cli (Agent Reach, 需 cookies) |
| 4️⃣ **公司网站** | 活着吗、改版了吗 | 已有 `health` 命令 |

### 8.3 新增数据结构

```sql
CREATE TABLE company_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT REFERENCES companies(id),
    snapshot_date DATE,
    team_size INTEGER,
    linkedin_job_count INTEGER,          -- LinkedIn 招聘职位数
    news_count INTEGER,                  -- 本期抓到的相关新闻数
    news_summary TEXT,                   -- LLM 生成的信号摘要
    x_activity_score INTEGER,            -- 0-100 X 活跃度
    funding_hint TEXT,                   -- LLM 提取的融资线索（若有）
    development_score INTEGER,           -- 0-100 综合发展分（LLM 打分）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, snapshot_date)
);
```

### 8.4 扫描流程（每次自动触发）

```
触发 (Hermes cron, 每周一次)
  │
  ▼
遍历指定 batch 的所有公司
  │
  ├─→ 采集器 (每家公司):
  │     • LinkedIn 团队/职位变化
  │     • Google News RSS 搜 3 条最新
  │     • (可选) X 热度
  │     • 网站 health check
  │
  ├─→ LLM 打分器 (DeepSeek):
  │     输入: 该公司全部信号
  │     输出: development_score (0-100) + 一句话理由 + funding_hint
  │
  ├─→ 存 snapshot (company_snapshots 表)
  │
  ▼
对比上次 snapshot
  ├─→ Top movers: 本周发展最快 10 家 (score 涨幅最大)
  ├─→ Red flags: 可能出问题 5 家 (score 暴跌 / 网站挂了 / 无新闻)
  └─→ 发送报告到 Telegram / 邮箱
```

### 8.5 LLM 打分标准（development_score 0-100）

| 信号 | 加分 |
|---|---|
| 新融资 (seed/series) | +30 |
| 团队扩招 (LinkedIn 职位增加) | +20 |
| 重大产品发布 / 合作 | +20 |
| 创始人高活跃 (X 发帖多) | +10 |
| 网站改版 / 正常运营 | +10 |
| 收购 / 上市 | +50 |
| 负面信号 | 扣分 |
| 网站挂了 | -40 |
| 3 个月无任何新闻 | -20 |

LLM 综合判断给出 0-100 分 + 一句话理由。

### 8.6 CLI / 命令

```bash
# 手动扫描一个 batch
python -m yc_tracker scan --batch "Summer 2026"

# 扫描所有 batch
python -m yc_tracker scan --all

# 查看某公司 snapshot 历史（时间序列）
python -m yc_tracker snapshot conifer

# 本周 movers（对比上次）
python -m yc_tracker movers --batch "Summer 2026"

# 手动跑打分（只测 LLM 打分）
python -m yc_tracker score conifer
```

### 8.7 数据源接入点

- `yc_tracker/crawlers/` 已有 `BaseCrawler` + `@register` 框架
- 新增 crawler: `news_crawler.py` (Google News RSS)、`linkedin_crawler.py`、`x_crawler.py` (可选)
- `yc_tracker/score.py` — LLM 打分器 (DeepSeek)
- `yc_tracker/snapshot.py` — snapshot 存储与对比逻辑

### 8.8 Hermes cron 接入

每周一早上 8:00 PT 自动跑：
```
python -m yc_tracker scan --batch "Summer 2026"
python -m yc_tracker movers --batch "Summer 2026"   # 对比后输出
```

### 8.9 验收标准 (V2)

- [ ] `scan` 能对 batch 里所有公司生成 snapshot
- [ ] snapshot 有 development_score + 理由
- [ ] 连续两次 scan 后，`movers` 能输出 Top movers + Red flags
- [ ] LinkedIn / Google News 至少两个信号源接入
- [ ] DeepSeek 打分可配置（key 从 env 读）

### 8.10 依赖

- `feedparser` (RSS) — 已在 requirements
- `openai` / `httpx` 调 DeepSeek
- Agent Reach (twitter-cli, opencli) — 可选增强

---

## 9. 未来方向（V3+）

- Web dashboard
- 多 VC 支持（a16z, Sequoia 等）
- 社区贡献（PR 更新公司状态）
- Crunchbase API（如果有预算）
- 邮件 newsletter（用户订阅 weekly digest）
