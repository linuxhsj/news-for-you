# AI Daily News / AI 精选日报

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

Automatically aggregate AI-related news, intelligently translate, deduplicate, and sort to generate structured Markdown reports and push to Feishu groups.

### Features

- **Multi-source Aggregation**: Supports 17+ data sources including RSS/Atom/arXiv
- **Smart Translation**: Auto-translate English titles to Chinese (Google Translate)
- **Title Enhancement**: Auto-add context to short titles
- **Similarity Deduplication**: Smart deduplication based on Jaccard similarity
- **Hot Topic Detection**: Auto-identify and pin important news
- **Proxy Support**: HTTP/HTTPS proxy support
- **Detailed Errors**: Shows specific failure reasons (timeout/403/SSL errors, etc.)

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI Daily News Pipeline                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │  Hot Search API │    │   RSS Feeds     │
│                 │    │                 │    │                 │
│ • OpenAI Blog   │    │ • TianAPI       │    │ • arXiv Papers  │
│ • Anthropic     │    │ • ITAPI         │    │ • TechCrunch    │
│ • DeepMind      │    │ • UAPI          │    │ • Hacker News   │
│ • GitHub Blog   │    │                 │    │ • 36Kr/Huxiu    │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Processing Pipeline                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │   Fetcher    │──▶│   Parser     │──▶│  Translator  │──▶│   Filter     │ │
│  │              │   │              │   │              │   │              │ │
│  │ • HTTP/Proxy │   │ • RSS/Atom   │   │ • Google     │   │ • Keywords   │ │
│  │ • SSL/Cache  │   │ • HTML       │   │   Translate  │   │ • Time       │ │
│  │ • Parallel   │   │ • JSON API   │   │ • Title      │   │ • Dedup      │ │
│  └──────────────┘   └──────────────┘   │   Enhancement│   │ • Scoring    │ │
│                                         └──────────────┘   └──────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Output & Delivery                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐              ┌──────────────────┐                     │
│  │  Markdown Report │              │   Feishu Push    │                     │
│  │                  │              │                  │                     │
│  │ • AI News        │              │ • Webhook API    │                     │
│  │ • Hot Search     │              │ • openclaw CLI   │                     │
│  │ • TOP 10         │              │ • Scheduled Task │                     │
│  └──────────────────┘              └──────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Sources

| Type | Sources |
|------|---------|
| International AI Companies | OpenAI, Anthropic, Google DeepMind |
| Developer Platforms | GitHub Blog, Hugging Face |
| Academic Papers | arXiv (AI/ML/CV/CL) |
| Tech Media | TechCrunch AI, Jiqizhixin |
| Tech Communities | Hacker News |
| Chinese Media | 36Kr, Huxiu, ITHome, SSPai, Ifanr |

### Quick Start

```bash
# Basic run
python3 generate-rss-news.py

# With proxy (or set RSS_PROXY environment variable)
python3 generate-rss-news.py --proxy http://your-proxy:port --insecure-ssl

# Use config file
python3 generate-rss-news.py --config config.json

# Custom parameters
python3 generate-rss-news.py --max-items 15 --hours 48 --output /tmp/news.md
```

### Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--config` | - | JSON config file path |
| `--output, -o` | daily-ai-news.md | Markdown output path |
| `--hours` | 24 | Primary time window (hours) |
| `--fallback-hours` | 48 | Fallback window when no results |
| `--max-items` | 10 | Maximum items to output |
| `--timeout` | 25 | Request timeout per source (seconds) |
| `--proxy` | - | Proxy address |
| `--insecure-ssl` | False | Disable HTTPS certificate verification |
| `--verbose` | False | Output debug information |
| `--cache-path` | /tmp/rss-cache.json | HTTP cache file path |

### Configuration File

Create `config.json` to customize:

```json
{
  "hours": 24,
  "max_items": 10,
  "proxy": "",
  "sources": {
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Anthropic": "https://www.anthropic.com/news"
  },
  "include_keywords": ["AI", "LLM", "GPT"],
  "exclude_keywords": ["funding", "hiring"],
  "hot_keywords": ["Claude", "GPT-5", "release"]
}
```

### Switching to Other News Domains

To aggregate news from other domains (e.g., finance, sports, entertainment), simply modify `config.json`:

1. **Change `sources`**: Replace RSS feed URLs with your target domain sources
2. **Update `include_keywords`**: Add relevant keywords for your domain
3. **Update `exclude_keywords`**: Filter out unwanted content
4. **Update `hot_keywords`**: Keywords that indicate important news in your domain

Example for Finance News:

```json
{
  "sources": {
    "Bloomberg": "https://www.bloomberg.com/feed/podcast/bloomberg-technology.xml",
    "Reuters": "https://www.reutersagency.com/feed/",
    "WSJ": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"
  },
  "include_keywords": ["stock", "market", "investment", "finance", "trading"],
  "exclude_keywords": ["celebrity", "entertainment"],
  "hot_keywords": ["IPO", "merger", "acquisition", "earnings"]
}
```

---

## Hot Search Aggregator / 热搜聚合

A standalone module that aggregates hot search data from 8 major Chinese platforms and intelligently selects the top 10 most important topics.

### Supported Platforms

| Platform | Data Source | Features |
|----------|-------------|----------|
| Weibo Hot Search | UAPI | Real-time trending topics |
| Baidu Hot Search | UAPI | Search engine trends |
| Zhihu Hot List | UAPI | Q&A community trends |
| Bilibili Hot List | UAPI | Video platform trends |
| Douyin Hot Topics | UAPI | Short video trends |
| Toutiao Headlines | UAPI | News aggregation |
| WeChat Hot Search | TianAPI | WeChat ecosystem trends |
| Xiaohongshu Hot | ITAPI | Lifestyle & shopping trends |

### Intelligent Filtering

The module uses a multi-factor scoring algorithm to identify the most important topics:

1. **Cross-Platform Frequency**: Topics appearing on multiple platforms get higher priority (+100 points per platform)
2. **Ranking Weight**: Higher rankings score more (Rank 1 = 20 points, Rank 20 = 1 point)
3. **Hot Value**: Higher view/engagement counts contribute to score
4. **Platform Weight**: Different platforms have different authority weights
5. **Similarity Deduplication**: Similar topics are merged, showing all source platforms

### Quick Start

```bash
# Run hot search aggregation
python3 hotsearch.py

# Output saved to /tmp/hotsearch-test.md
```

### API Keys Required

Configure in `.env` file:

| Variable | Description | Get API Key |
|----------|-------------|-------------|
| `TIANAPI_KEY` | TianAPI key for WeChat hot search | [TianAPI Console](https://www.tianapi.com/console/) |
| `ITAPI_KEY` | ITAPI key for Xiaohongshu hot search | [ITAPI Console](https://api.itapi.cn/user/key) |

### Sample Output

```
# � 热搜速递

⏰ 2026-02-18 16:29

---

## 🔥 TOP 10 热点

**1. 高市早苗再次当选日本首相**
   🔥9215837 [5平台]
   [查看详情](https://...)

**2. 大年初二为何最好不要午睡**
   🔥7332542 [3平台]
   [查看详情](https://...)

**3. 春晚机器人厉害在哪里**
   🔥10541083 [2平台]
   [查看详情](https://...)

---

## � 各平台热搜

**微博热搜**
1. 诗幂 🔥1106185
2. 孩子存1000比你存20万利息高 🔥793359
...

**百度热搜**
1. "典"话新春 🔥7904032
...
```

---

### Deployment Guide

#### Step 1: Configure Feishu Push

**Option A: Webhook (Recommended)**

1. Create a bot in your Feishu group
2. Get the webhook URL
3. Add to `.env`:
   ```
   FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your-token
   ```

**Option B: openclaw CLI**

1. Install openclaw: `npm install -g openclaw`
2. Configure Feishu credentials in openclaw
3. Add to `.env`:
   ```
   FEISHU_TARGET_ID=oc_xxxxxxxxxxxxxxxxxxxxxxxx
   ```

#### Step 2: Set Up Scheduled Task

```bash
# Edit crontab
crontab -e

# Add scheduled task (run at 8 AM daily)
0 8 * * * cd /path/to/news && ./send-news-to-feishu.sh >> /tmp/news-cron.log 2>&1
```

#### Step 3: Verify

```bash
# Manual test
./send-news-to-feishu.sh

# Check log
cat /tmp/news-cron.log
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `RSS_PROXY` | Proxy address |
| `RSS_INSECURE_SSL` | Set to `1` to disable SSL verification |
| `FEISHU_WEBHOOK` | Feishu bot webhook URL |
| `FEISHU_TARGET_ID` | Feishu group ID (when using openclaw CLI) |
| `TIANAPI_KEY` | TianAPI key for WeChat hot search |
| `ITAPI_KEY` | ITAPI key for Xiaohongshu hot search |

### Files

| File | Description |
|------|-------------|
| `generate-rss-news.py` | Main program, generates Markdown report |
| `hotsearch.py` | Hot search aggregator with intelligent filtering |
| `send-news-to-feishu.sh` | Script to send report to Feishu |
| `config.json` | Configuration file |
| `test_generate_rss_news.py` | Unit tests |

### Dependencies

- Python 3.10+

```bash
pip install -r requirements.txt
```

---

<a name="中文"></a>
## 中文

自动聚合 AI 相关资讯，智能翻译、去重、排序，生成结构化 Markdown 报告并推送到飞书群。

### 功能特性

- **多源聚合**: 支持 RSS/Atom/arXiv 等 17+ 数据源
- **智能翻译**: 英文标题自动翻译为中文（Google Translate）
- **标题增强**: 简短标题自动补充上下文信息
- **相似度去重**: 基于 Jaccard 相似度的智能去重
- **热点识别**: 自动识别重要新闻并置顶
- **代理支持**: 支持 HTTP/HTTPS 代理
- **详细错误**: 显示具体的失败原因（超时/403/SSL错误等）

### 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI 精选日报处理流水线                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    数据源       │    │   热搜 API      │    │   RSS 订阅源    │
│                 │    │                 │    │                 │
│ • OpenAI Blog   │    │ • TianAPI       │    │ • arXiv 论文    │
│ • Anthropic     │    │ • ITAPI         │    │ • TechCrunch    │
│ • DeepMind      │    │ • UAPI          │    │ • Hacker News   │
│ • GitHub Blog   │    │                 │    │ • 36氪/虎嗅     │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              处理流水线                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │   数据获取   │──▶│   内容解析   │──▶│   智能翻译   │──▶│   过滤筛选   │ │
│  │              │   │              │   │              │   │              │ │
│  │ • HTTP/代理  │   │ • RSS/Atom   │   │ • Google     │   │ • 关键词     │ │
│  │ • SSL/缓存   │   │ • HTML       │   │   翻译 API   │   │ • 时间窗口   │ │
│  │ • 并行请求   │   │ • JSON API   │   │ • 标题增强   │   │ • 去重/评分  │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              输出与推送                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐              ┌──────────────────┐                     │
│  │  Markdown 报告   │              │    飞书推送      │                     │
│  │                  │              │                  │                     │
│  │ • AI 资讯        │              │ • Webhook API    │                     │
│  │ • 热搜聚合       │              │ • openclaw CLI   │                     │
│  │ • TOP 10 热点    │              │ • 定时任务       │                     │
│  └──────────────────┘              └──────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 数据源

| 类型 | 来源 |
|------|------|
| 国际 AI 公司 | OpenAI, Anthropic, Google DeepMind |
| 开发平台 | GitHub Blog, Hugging Face |
| 学术论文 | arXiv (AI/ML/CV/CL) |
| 科技媒体 | TechCrunch AI, 机器之心 |
| 技术社区 | Hacker News |
| 国内媒体 | 36氪, 虎嗅, IT之家, 少数派, 爱范儿 |

### 快速开始

```bash
# 基础运行
python3 generate-rss-news.py

# 使用代理（或设置环境变量 RSS_PROXY）
python3 generate-rss-news.py --proxy http://your-proxy:port --insecure-ssl

# 使用配置文件
python3 generate-rss-news.py --config config.json

# 自定义参数
python3 generate-rss-news.py --max-items 15 --hours 48 --output /tmp/news.md
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--config` | - | JSON 配置文件路径 |
| `--output, -o` | daily-ai-news.md | Markdown 输出路径 |
| `--hours` | 24 | 主时间窗口（小时） |
| `--fallback-hours` | 48 | 无结果时的回退窗口 |
| `--max-items` | 10 | 最多输出条数 |
| `--timeout` | 25 | 单个源请求超时（秒） |
| `--proxy` | - | 代理地址 |
| `--insecure-ssl` | False | 禁用 HTTPS 证书校验 |
| `--verbose` | False | 输出调试信息 |
| `--cache-path` | /tmp/rss-cache.json | HTTP 缓存文件路径 |

### 配置文件

创建 `config.json` 自定义配置：

```json
{
  "hours": 24,
  "max_items": 10,
  "proxy": "",
  "sources": {
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Anthropic": "https://www.anthropic.com/news"
  },
  "include_keywords": ["AI", "LLM", "大模型"],
  "exclude_keywords": ["融资", "招聘"],
  "hot_keywords": ["Claude", "GPT-5", "发布"]
}
```

### 切换到其他领域新闻

如需聚合其他领域的新闻（如财经、体育、娱乐等），只需修改 `config.json`：

1. **修改 `sources`**: 替换为目标领域的 RSS 源地址
2. **更新 `include_keywords`**: 添加该领域的相关关键词
3. **更新 `exclude_keywords`**: 过滤不需要的内容
4. **更新 `hot_keywords`**: 该领域重要新闻的关键词

示例 - 财经新闻配置：

```json
{
  "sources": {
    "财新网": "https://rsshub.app/caixin/finance",
    "华尔街见闻": "https://rsshub.app/wallstreetcn/news/global",
    "东方财富": "https://rsshub.app/eastmoney/report/strategyreport"
  },
  "include_keywords": ["股票", "基金", "投资", "财经", "金融", "市场"],
  "exclude_keywords": ["娱乐", "八卦", "明星"],
  "hot_keywords": ["IPO", "并购", "财报", "降息", "加息"]
}
```

---

## 热搜聚合模块

独立模块，聚合 8 大平台热搜数据，智能筛选 TOP 10 热点话题。

### 支持平台

| 平台 | 数据源 | 特点 |
|------|--------|------|
| 微博热搜 | UAPI | 实时热点话题 |
| 百度热搜 | UAPI | 搜索引擎趋势 |
| 知乎热榜 | UAPI | 问答社区热点 |
| B站热榜 | UAPI | 视频平台趋势 |
| 抖音热点 | UAPI | 短视频热点 |
| 今日头条 | UAPI | 新闻聚合热点 |
| 微信热搜 | TianAPI | 微信生态热点 |
| 小红书热点 | ITAPI | 生活方式趋势 |

### 智能筛选算法

模块采用多因子评分算法识别最重要的热点：

1. **跨平台频次**: 出现在多个平台的话题优先级更高（每多一个平台 +100 分）
2. **排名权重**: 排名越靠前得分越高（第 1 名 20 分，第 20 名 1 分）
3. **热度值**: 浏览量/互动量越高得分越高
4. **平台权重**: 不同平台有不同的权威性权重
5. **相似度去重**: 相似话题合并，显示所有来源平台

### 快速开始

```bash
# 运行热搜聚合
python3 hotsearch.py

# 输出保存到 /tmp/hotsearch-test.md
```

### API 密钥配置

在 `.env` 文件中配置：

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `TIANAPI_KEY` | 天行数据 API Key（微信热搜） | [TianAPI 控制台](https://www.tianapi.com/console/) |
| `ITAPI_KEY` | 顺为数据 API Key（小红书热点） | [ITAPI 控制台](https://api.itapi.cn/user/key) |

### 输出示例

```
# � 热搜速递

⏰ 2026-02-18 16:29

---

## 🔥 TOP 10 热点

**1. 高市早苗再次当选日本首相**
   🔥9215837 [5平台]
   [查看详情](https://...)

**2. 大年初二为何最好不要午睡**
   🔥7332542 [3平台]
   [查看详情](https://...)

**3. 春晚机器人厉害在哪里**
   �10541083 [2平台]
   [查看详情](https://...)

---

## 📋 各平台热搜

**微博热搜**
1. 诗幂 🔥1106185
2. 孩子存1000比你存20万利息高 🔥793359
...

**百度热搜**
1. "典"话新春 🔥7904032
...
```

---

### 部署指南

#### 步骤 1：配置飞书推送

**方式 A：Webhook（推荐）**

1. 在飞书群中创建机器人
2. 获取 Webhook 地址
3. 添加到 `.env` 文件：
   ```
   FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your-token
   ```

**方式 B：openclaw CLI**

1. 安装 openclaw：`npm install -g openclaw`
2. 在 openclaw 中配置飞书凭证
3. 添加到 `.env` 文件：
   ```
   FEISHU_TARGET_ID=oc_xxxxxxxxxxxxxxxxxxxxxxxx
   ```

#### 步骤 2：设置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天早上 8 点运行）
0 8 * * * cd /path/to/news && ./send-news-to-feishu.sh >> /tmp/news-cron.log 2>&1
```

#### 步骤 3：验证

```bash
# 手动测试
./send-news-to-feishu.sh

# 查看日志
cat /tmp/news-cron.log
```

### 环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

| 变量 | 说明 |
|------|------|
| `RSS_PROXY` | 代理地址 |
| `RSS_INSECURE_SSL` | 设为 `1` 禁用 SSL 校验 |
| `FEISHU_WEBHOOK` | 飞书机器人 Webhook 地址 |
| `FEISHU_TARGET_ID` | 飞书群 ID（使用 openclaw CLI 时） |
| `TIANAPI_KEY` | 天行数据 API Key（微信热搜） |
| `ITAPI_KEY` | 顺为数据 API Key（小红书热点） |

### 文件说明

| 文件 | 说明 |
|------|------|
| `generate-rss-news.py` | 主程序，生成 Markdown 报告 |
| `hotsearch.py` | 热搜聚合模块，智能筛选 TOP 10 |
| `send-news-to-feishu.sh` | 发送报告到飞书的脚本 |
| `config.json` | 配置文件 |
| `test_generate_rss_news.py` | 单元测试 |

### 依赖

- Python 3.10+

```bash
pip install -r requirements.txt
```

## License

MIT
