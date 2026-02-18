# AI 精选日报

自动聚合 AI 相关资讯，智能翻译、去重、排序，生成结构化 Markdown 报告并推送到飞书群。

## 功能特性

- **多源聚合**: 支持 RSS/Atom/arXiv 等 17+ 数据源
- **智能翻译**: 英文标题自动翻译为中文（Google Translate）
- **标题增强**: 简短标题自动补充上下文信息
- **相似度去重**: 基于 Jaccard 相似度的智能去重
- **热点识别**: 自动识别重要新闻并置顶
- **代理支持**: 支持 HTTP/HTTPS 代理
- **详细错误**: 显示具体的失败原因（超时/403/SSL错误等）

## 数据源

| 类型 | 来源 |
|------|------|
| 国际 AI 公司 | OpenAI, Anthropic, Google DeepMind |
| 开发平台 | GitHub Blog, Hugging Face |
| 学术论文 | arXiv (AI/ML/CV/CL) |
| 科技媒体 | TechCrunch AI, 机器之心 |
| 技术社区 | Hacker News |
| 国内媒体 | 36氪, 虎嗅, IT之家, 少数派, 爱范儿 |

## 快速开始

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

## 命令行参数

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

## 配置文件

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

## 输出示例

```markdown
# 🚨 AI 精选日报

**生成时间**: 2026-02-18 12:58  
**时间范围**: 过去 24 小时  
**数据源**: Hacker News, IT之家

---

## 🔥 重点速递

**1. 2 亿美元合作告急：消息称 Anthropic 与美国军方 AI 使用分歧激化**
- ⏰ 02-18 11:10
- 📰 IT之家
- 🔗 [原文链接](https://...)
- 💬 IT之家 2 月 18 日消息，人工智能企业与美国军方的关系...

## 📊 技术动态

1. [数千名首席执行官承认人工智能对就业或生产力没有影响](...)
   - ⏰ 02-18 09:40
   - Hacker News

## 📌 今日结论

• 关注模型能力边界与端侧部署进展
• 持续跟踪智能体工具链成熟度
```

## 环境变量

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

## 定时任务

使用 crontab 设置定时推送：

```bash
# 每天早上 8 点运行
0 8 * * * cd /path/to/news && ./send-news-to-feishu.sh
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `generate-rss-news.py` | 主程序，生成 Markdown 报告 |
| `send-news-to-feishu.sh` | 发送报告到飞书的脚本 |
| `config.json` | 配置文件 |
| `test_generate_rss_news.py` | 单元测试 |

## 依赖

- Python 3.10+
- feedparser

```bash
pip install feedparser
```

## License

MIT
