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

## 8. 未来方向（V2+）

- Web dashboard
- 多 VC 支持（a16z, Sequoia 等）
- 社区贡献（PR 更新公司状态）
- Crunchbase API（如果有预算）
- 邮件 newsletter（用户订阅 weekly digest）
