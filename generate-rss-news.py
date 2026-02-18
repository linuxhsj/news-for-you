#!/usr/bin/env python3
"""
AI Daily News Generator - Production Version
Designed for: AI工具爱好者
"""

import argparse
import json
import logging
import os
import re
import ssl
import time
import urllib.parse as urlparse_lib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import feedparser
import urllib.request
import urllib.error

TRANSLATE_ENABLED = True
TITLE_MIN_LENGTH = 15
TITLE_MAX_LENGTH = 80

RSS_SOURCES: dict[str, str] = {
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Anthropic": "https://www.anthropic.com/news",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    
    "GitHub Blog": "https://github.blog/feed/",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    
    "arXiv AI": "http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=15",
    "arXiv ML": "http://export.arxiv.org/api/query?search_query=cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=10",
    "arXiv CV": "http://export.arxiv.org/api/query?search_query=cat:cs.CV&sortBy=submittedDate&sortOrder=descending&max_results=10",
    "arXiv CL": "http://export.arxiv.org/api/query?search_query=cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=10",
    
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "机器之心": "https://www.jiqizhixin.com/rss",
    
    "Hacker News": "https://news.ycombinator.com/rss",
    
    "36氪": "https://36kr.com/feed",
    "虎嗅": "https://www.huxiu.com/rss/0.xml",
    "IT之家": "https://www.ithome.com/rss/",
    "少数派": "https://sspai.com/feed",
    "爱范儿": "https://www.ifanr.com/feed",
}

INCLUDE_KEYWORDS: list[str] = [
    "AI", "LLM", "大模型", "多模态", "multimodal", "智能体", "agent",
    "machine learning", "deep learning", "transformer", "attention", "diffusion",
    "端侧", "on-device", "edge AI", "programming", "copilot", "assistant",
    "RAG", "retrieval", "embedding", "向量数据库", "fine-tuning", "prompt engineering",
    "vision", "speech", "VLM", "VLA", "ASR", "TTS", "reinforcement learning",
    "Claude", "GPT", "Gemini", "Llama", "Qwen", "通义", "幻觉", "alignment",
    "autonomous", "robotics"
]

EXCLUDE_KEYWORDS: list[str] = [
    "融资", "IPO", "投资", "收购", "merger",
    "招聘", "求职", "面试",
    "峰会", "会议", "活动", "Meetup",
    "Super Bowl", "NFL", "体育",
    "娱乐", "八卦", "明星", "politics", "政治", "crypto", "加密货币",
    "gaming", "游戏", "celebrity"
]

HOT_KEYWORDS: list[str] = [
    'Claude', 'GPT-5', 'GPT-4.5', 'OpenAI', 'Anthropic', 'Gemini',
    '发布', 'launch', 'release', 'announce',
    '开源', 'open source', '突破', 'breakthrough', 'SOTA',
    'vulnerability', '安全漏洞'
]

SOURCE_WEIGHTS: dict[str, float] = {
    "OpenAI": 3.0,
    "Anthropic": 3.0,
    "Google DeepMind": 2.5,
    "Hugging Face": 2.0,
    "GitHub Blog": 1.6,
    "arXiv AI": 1.4,
    "arXiv ML": 1.4,
    "arXiv CV": 1.4,
    "arXiv CL": 1.4,
    "TechCrunch AI": 1.2,
    "机器之心": 1.2,
    "Hacker News": 1.0,
    "36氪": 1.0,
    "虎嗅": 1.0,
    "IT之家": 0.8,
    "少数派": 0.8,
    "爱范儿": 0.8,
}

MAX_ITEMS = 10
CACHE_EXPIRE_HOURS = 48


def is_chinese(text: str) -> bool:
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return chinese_chars > len(text) * 0.3


def translate_text(text: str, proxy: str = "", timeout: int = 10) -> str:
    if not text or not TRANSLATE_ENABLED:
        return text
    
    if is_chinese(text):
        return text
    
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-CN",
            "dt": "t",
            "q": text
        }
        full_url = f"{url}?{urlencode(params)}"
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
        
        if proxy:
            handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            opener = urllib.request.build_opener(handler, urllib.request.HTTPSHandler(context=ctx))
            with opener.open(req, timeout=timeout) as r:
                result = json.loads(r.read().decode("utf-8"))
        else:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                result = json.loads(r.read().decode("utf-8"))
        
        if result and result[0]:
            translated = "".join(part[0] for part in result[0] if part[0])
            return translated
    except Exception as e:
        logging.debug("翻译失败: %s", e)
    
    return text


def enhance_title(title: str, description: str = "", source: str = "") -> str:
    if len(title) >= TITLE_MIN_LENGTH and len(title) <= TITLE_MAX_LENGTH:
        return title
    
    if len(title) < TITLE_MIN_LENGTH:
        context_hints = {
            "Claude": "发布",
            "GPT": "发布",
            "Gemini": "发布",
            "Llama": "发布",
            "Sonnet": "发布",
            "Opus": "发布",
            "Haiku": "发布",
            "announces": "宣布",
            "releases": "发布",
            "launches": "推出",
            "introduces": "推出",
        }
        
        hint = ""
        for keyword, action in context_hints.items():
            if keyword.lower() in title.lower():
                hint = action
                break
        
        if hint:
            return f"{title} {hint}"
        
        if description:
            desc_clean = re.sub(r'<[^>]+>', '', description)
            desc_clean = unescape(desc_clean).strip()
            if len(desc_clean) > 20:
                return f"{title}：{desc_clean[:TITLE_MAX_LENGTH - len(title) - 2]}"
        
        if source:
            return f"{title}（{source}）"
    
    if len(title) > TITLE_MAX_LENGTH:
        return title[:TITLE_MAX_LENGTH - 3] + "..."
    
    return title


@dataclass
class NewsItem:
    title: str
    link: str
    pubdate: str = ""
    description: str = ""
    source: str = ""
    dt: Optional[datetime] = None
    score: float = 0.0
    original_title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "link": self.link,
            "pubdate": self.pubdate,
            "description": self.description,
            "source": self.source,
            "_dt": self.dt,
            "_score": self.score,
            "original_title": self.original_title,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NewsItem":
        return cls(
            title=data.get("title", ""),
            link=data.get("link", ""),
            pubdate=data.get("pubdate", ""),
            description=data.get("description", ""),
            source=data.get("source", ""),
            dt=data.get("_dt"),
            score=data.get("_score", 0.0),
            original_title=data.get("original_title", ""),
        )


@dataclass
class CacheEntry:
    etag: str = ""
    last_modified: str = ""
    timestamp: float = 0.0

    def is_expired(self, expire_hours: float = CACHE_EXPIRE_HOURS) -> bool:
        if self.timestamp == 0:
            return False
        age_hours = (time.time() - self.timestamp) / 3600
        return age_hours > expire_hours

    def to_dict(self) -> dict[str, Any]:
        return {
            "etag": self.etag,
            "last_modified": self.last_modified,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        return cls(
            etag=data.get("etag", ""),
            last_modified=data.get("last_modified", ""),
            timestamp=data.get("timestamp", 0.0),
        )


@dataclass
class Config:
    hours: int = 24
    fallback_hours: int = 48
    max_items: int = MAX_ITEMS
    timeout: int = 25
    sources: dict[str, str] = field(default_factory=lambda: RSS_SOURCES)
    include_keywords: list[str] = field(default_factory=lambda: INCLUDE_KEYWORDS)
    exclude_keywords: list[str] = field(default_factory=lambda: EXCLUDE_KEYWORDS)
    hot_keywords: list[str] = field(default_factory=lambda: HOT_KEYWORDS)
    source_weights: dict[str, float] = field(default_factory=lambda: SOURCE_WEIGHTS)
    cache_path: str = "/tmp/rss-cache.json"
    proxy: str = ""

    @classmethod
    def from_file(cls, path: str) -> "Config":
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(
                hours=int(data.get("hours", 24)),
                fallback_hours=int(data.get("fallback_hours", 48)),
                max_items=int(data.get("max_items", MAX_ITEMS)),
                timeout=int(data.get("timeout", 25)),
                sources=data.get("sources", RSS_SOURCES),
                include_keywords=data.get("include_keywords", INCLUDE_KEYWORDS),
                exclude_keywords=data.get("exclude_keywords", EXCLUDE_KEYWORDS),
                hot_keywords=data.get("hot_keywords", HOT_KEYWORDS),
                source_weights=data.get("source_weights", SOURCE_WEIGHTS),
                cache_path=data.get("cache_path", "/tmp/rss-cache.json"),
                proxy=data.get("proxy", ""),
            )
        except Exception as e:
            logging.warning("配置文件读取失败: %s", e)
            return cls()


def fetch(
    url: str,
    *,
    insecure_ssl: bool = False,
    timeout: int = 25,
    retries: int = 2,
    cache_entry: Optional[CacheEntry] = None,
    proxy: str = "",
) -> tuple[str, CacheEntry, bool, str]:
    ctx: Optional[ssl.SSLContext] = None
    if insecure_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    elif url.lower().startswith("https://"):
        ctx = ssl.create_default_context()

    headers: dict[str, str] = {"User-Agent": "Mozilla/5.0"}
    new_cache = CacheEntry(timestamp=time.time())

    if cache_entry:
        if cache_entry.etag:
            headers["If-None-Match"] = cache_entry.etag
        if cache_entry.last_modified:
            headers["If-Modified-Since"] = cache_entry.last_modified

    handler: Optional[urllib.request.BaseHandler] = None
    if proxy:
        handler = urllib.request.ProxyHandler({
            "http": proxy,
            "https": proxy,
        })

    backoff = 0.8
    last_error = ""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            if handler:
                opener = urllib.request.build_opener(handler, urllib.request.HTTPSHandler(context=ctx))
                with opener.open(req, timeout=timeout) as r:
                    raw = r.read()
                    new_cache.etag = r.headers.get("ETag") or ""
                    new_cache.last_modified = r.headers.get("Last-Modified") or ""
                    return raw.decode("utf-8", errors="replace"), new_cache, False, ""
            else:
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                    raw = r.read()
                    new_cache.etag = r.headers.get("ETag") or ""
                    new_cache.last_modified = r.headers.get("Last-Modified") or ""
                    return raw.decode("utf-8", errors="replace"), new_cache, False, ""
        except urllib.error.HTTPError as e:
            if e.code == 304:
                return "", CacheEntry(), True, ""
            last_error = f"HTTP {e.code}"
            logging.debug("Fetch failed: %s (%s) attempt=%d", url, e, attempt + 1)
        except urllib.error.URLError as e:
            if "timed out" in str(e).lower():
                last_error = "超时"
            elif "connection refused" in str(e).lower():
                last_error = "连接被拒绝"
            elif "name or service not known" in str(e).lower():
                last_error = "DNS解析失败"
            else:
                last_error = str(e.reason) if hasattr(e, 'reason') else str(e)[:30]
            logging.debug("Fetch failed: %s (%s) attempt=%d", url, e, attempt + 1)
        except ssl.SSLError as e:
            last_error = f"SSL错误: {str(e)[:30]}"
            logging.debug("Fetch failed: %s (%s) attempt=%d", url, e, attempt + 1)
        except Exception as e:
            last_error = str(e)[:40]
            logging.debug("Fetch failed: %s (%s) attempt=%d", url, e, attempt + 1)

        if attempt < retries:
            time.sleep(backoff)
            backoff *= 2

    return "", CacheEntry(), False, last_error


def load_cache(path: str) -> dict[str, CacheEntry]:
    try:
        if not path:
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {k: CacheEntry.from_dict(v) for k, v in data.items() if isinstance(v, dict)}
    except Exception:
        return {}


def save_cache(path: str, cache: dict[str, CacheEntry]) -> None:
    try:
        if not path:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in cache.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logging.warning("缓存保存失败: %s", e)


def parse_feed(xml: str, source: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    if not xml:
        return items

    try:
        feed = feedparser.parse(xml)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            pubdate = ""
            if hasattr(entry, "published"):
                pubdate = entry.published
            elif hasattr(entry, "updated"):
                pubdate = entry.updated

            description = entry.get("summary", "") or entry.get("description", "")
            description = re.sub(r"<[^>]+>", "", unescape(description))[:150]

            if "arxiv" in source.lower():
                title = f"[论文] {title}"
                authors = entry.get("authors", [])
                if authors:
                    author_names = [a.get("name", "") for a in authors[:2]]
                    description = f"作者: {', '.join(author_names)}"

            items.append(NewsItem(
                title=unescape(title),
                link=link,
                pubdate=pubdate,
                description=description,
                source=source,
            ))
    except Exception as e:
        logging.warning("解析 feed 失败 [%s]: %s", source, e)

    return items


def parse_date(pubdate: str) -> Optional[datetime]:
    if not pubdate:
        return None

    s = pubdate.strip()

    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        s2 = s
        if s2.endswith("Z"):
            s2 = s2[:-1] + "+00:00"
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def parse_anthropic_html(html: str, source: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    if not html:
        return items

    try:
        links = re.findall(r'href="(/news/[a-z0-9-]+)"', html)
        seen = set()
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            
            slug = link.replace("/news/", "")
            title = slug.replace("-", " ").title()
            
            items.append(NewsItem(
                title=title,
                link=f"https://www.anthropic.com{link}",
                pubdate="",
                description="",
                source=source,
            ))
    except Exception as e:
        logging.warning("解析 Anthropic HTML 失败: %s", e)

    return items


def enrich_single_item(item: NewsItem, ctx: ssl.SSLContext, handler: Optional[urllib.request.BaseHandler], timeout: int) -> NewsItem:
    try:
        req = urllib.request.Request(item.link, headers={"User-Agent": "Mozilla/5.0"})
        if handler:
            opener = urllib.request.build_opener(handler, urllib.request.HTTPSHandler(context=ctx))
            with opener.open(req, timeout=timeout) as r:
                html = r.read().decode("utf-8", errors="replace")
        else:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                html = r.read().decode("utf-8", errors="replace")

        title_match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html)
        if title_match:
            item.title = title_match.group(1)

        date_match = re.search(r'(\w+\s+\d+,\s+\d{4})', html)
        if date_match:
            item.pubdate = date_match.group(1)
    except Exception as e:
        logging.debug("Enrich item failed [%s]: %s", item.link, e)
    
    return item


def enrich_anthropic_items(items: list[NewsItem], proxy: str = "", timeout: int = 15) -> list[NewsItem]:
    if not items:
        return items

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    handler: Optional[urllib.request.BaseHandler] = None
    if proxy:
        handler = urllib.request.ProxyHandler({
            "http": proxy,
            "https": proxy,
        })

    items_to_fetch = items[:10]
    
    with ThreadPoolExecutor(max_workers=min(5, len(items_to_fetch))) as executor:
        futures = {
            executor.submit(enrich_single_item, item, ctx, handler, timeout): item
            for item in items_to_fetch
        }
        
        enriched = []
        for future in as_completed(futures):
            try:
                enriched.append(future.result())
            except Exception as e:
                logging.debug("Future failed: %s", e)
                enriched.append(futures[future])
        
        return enriched


def normalize_url(url: str) -> str:
    try:
        if not url:
            return ""
        u = urlparse(url)
        qs = [(k, v) for (k, v) in parse_qsl(u.query) if not k.lower().startswith("utm_")]
        u2 = u._replace(query=urlencode(qs), fragment="")
        return urlunparse(u2)
    except Exception:
        return (url or "").strip()


def is_hot(item: NewsItem, hot_keywords: list[str]) -> bool:
    title = item.title.casefold()
    return any(kw.casefold() in title for kw in hot_keywords)


def compute_score(
    item: NewsItem,
    source_weights: dict[str, float],
    hot_keywords: list[str],
    now_utc: datetime,
    window_hours: int,
) -> float:
    score = 0.0
    score += float(source_weights.get(item.source, 1.0))

    title = item.title.casefold()
    if any(kw.casefold() in title for kw in hot_keywords):
        score += 2.0

    if item.description:
        score += 0.2

    if item.dt and window_hours > 0:
        delta_hours = (now_utc - item.dt).total_seconds() / 3600.0
        recency = max(0.0, 1.0 - (delta_hours / max(window_hours, 1)))
        score += recency * 3.0

    return score


def tokenize_title(title: str) -> set[str]:
    s = title.casefold()
    s = re.sub(r'[^\w\s]', ' ', s)
    words = s.split()
    return set(w for w in words if len(w) > 2)


def title_similarity(t1: str, t2: str) -> float:
    words1 = tokenize_title(t1)
    words2 = tokenize_title(t2)
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)


def dedupe_items(items: list[NewsItem], similarity_threshold: float = 0.7) -> list[NewsItem]:
    seen_links: set[str] = set()
    seen_titles: list[str] = []
    out: list[NewsItem] = []

    for it in items:
        link = normalize_url(it.link)
        if link and link in seen_links:
            continue
        
        title_lower = it.title.casefold()
        
        is_duplicate = False
        for seen_title in seen_titles:
            if title_similarity(it.title, seen_title) >= similarity_threshold:
                is_duplicate = True
                break
        
        if is_duplicate:
            continue
        
        if link:
            seen_links.add(link)
        seen_titles.append(it.title)
        it.link = link
        out.append(it)

    return out


def filter_items(
    items: list[NewsItem],
    include_keywords: list[str],
    exclude_keywords: list[str],
    cutoff: datetime,
    fallback_cutoff: datetime,
) -> tuple[list[NewsItem], list[NewsItem]]:
    include_kws = [kw.casefold() for kw in include_keywords]
    exclude_kws = [kw.casefold() for kw in exclude_keywords]

    primary: list[NewsItem] = []
    fallback: list[NewsItem] = []

    for item in items:
        title = item.title.casefold()
        desc = item.description.casefold()

        if any((kw in title) or (kw in desc) for kw in exclude_kws):
            continue

        if not any((kw in title) or (kw in desc) for kw in include_kws):
            continue

        dt = parse_date(item.pubdate)
        if dt:
            item.dt = dt
            if dt >= cutoff:
                primary.append(item)
            elif dt >= fallback_cutoff:
                fallback.append(item)

    return primary, fallback


def generate_markdown(items: list[NewsItem], hours: int, hot_keywords: list[str]) -> str:
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_cn = datetime.now().strftime("%Y年%m月%d日")

    sources = sorted(set(i.source for i in items))

    md = f"""# 🚨 AI 精选日报

**生成时间**: {time_now}  
**时间范围**: 过去 {hours} 小时  
**数据源**: {', '.join(sources) if sources else 'RSS 聚合'}

---

"""

    if not items:
        return md + "⚠️ 暂无符合条件的资讯\n"

    hot = [i for i in items if is_hot(i, hot_keywords)]
    normal = [i for i in items if i not in hot]

    if hot:
        md += "## 🔥 重点速递\n\n"
        for i, item in enumerate(hot, 1):
            pub = item.dt.astimezone().strftime("%m-%d %H:%M") if item.dt else ""
            md += f"**{i}. {item.title}**\n"
            if pub:
                md += f"- ⏰ {pub}\n"
            md += f"- 📰 {item.source}\n"
            md += f"- 🔗 [原文链接]({item.link})\n"
            if item.description:
                desc = item.description[:100]
                if not is_chinese(desc):
                    desc = translate_text(desc)
                md += f"- 💬 {desc}...\n"
            md += "\n"

    if normal:
        md += "## 📊 技术动态\n\n"
        for i, item in enumerate(normal, 1):
            pub = item.dt.astimezone().strftime("%m-%d %H:%M") if item.dt else ""
            md += f"{i}. [{item.title}]({item.link})\n"
            if pub:
                md += f"   - ⏰ {pub}\n"
            md += f"   - {item.source}\n\n"

    md += f"""## 📌 今日结论

• 关注模型能力边界与端侧部署进展
• 持续跟踪智能体工具链成熟度

---

**统计**: 🔥 {len(hot)} + 📊 {len(normal)} | cron: 每天 08:00

"""
    return md


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Daily News Generator (RSS/Atom)")
    parser.add_argument("-o", "--output", default=os.environ.get("DAILY_AI_NEWS_OUTPUT", ""), help="Markdown 输出路径")
    parser.add_argument("--hours", type=int, default=24, help="主时间窗口（小时）")
    parser.add_argument("--fallback-hours", type=int, default=48, help="无结果时的回退窗口（小时）")
    parser.add_argument("--max-items", type=int, default=MAX_ITEMS, help="最多输出条数（去重后）")
    parser.add_argument("--timeout", type=int, default=25, help="单个源请求超时（秒）")
    parser.add_argument("--insecure-ssl", action="store_true", default=os.environ.get("RSS_INSECURE_SSL") == "1", help="禁用 HTTPS 证书校验（不推荐）")
    parser.add_argument("--verbose", action="store_true", help="输出调试信息")
    parser.add_argument("--config", help="JSON 配置文件路径")
    parser.add_argument("--cache-path", default=os.environ.get("RSS_CACHE_PATH", ""), help="HTTP 缓存文件路径")
    parser.add_argument("--proxy", default=os.environ.get("RSS_PROXY", ""), help="代理地址，如 http://your-proxy:port")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.config:
        cfg = Config.from_file(args.config)
        if args.proxy:
            cfg.proxy = args.proxy
    else:
        cfg = Config(
            hours=args.hours,
            fallback_hours=args.fallback_hours,
            max_items=args.max_items,
            timeout=args.timeout,
            cache_path=args.cache_path or "/tmp/rss-cache.json",
            proxy=args.proxy,
        )

    if cfg.proxy:
        print(f"🌐 使用代理: {cfg.proxy}")

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=cfg.hours)
    fallback_cutoff = now_utc - timedelta(hours=cfg.fallback_hours)

    print("=" * 55)
    print("   AI Daily News Generator")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)
    print()

    all_items: list[NewsItem] = []
    cache = load_cache(cfg.cache_path)

    stats = {"success": 0, "cached": 0, "failed": 0}
    source_results: dict[str, tuple[int, str, str]] = {}

    futures: dict = {}
    with ThreadPoolExecutor(max_workers=min(8, len(cfg.sources))) as executor:
        for name, url in cfg.sources.items():
            futures[executor.submit(
                fetch,
                url,
                insecure_ssl=args.insecure_ssl,
                timeout=cfg.timeout,
                cache_entry=cache.get(url),
                proxy=cfg.proxy,
            )] = (name, url)

        for future in as_completed(futures):
            name, url = futures[future]
            xml, new_cache_entry, not_modified, error_msg = future.result()

            if not_modified:
                stats["cached"] += 1
                source_results[name] = (0, "cached", "")
                logging.debug("   %s: 缓存命中", name)
                continue

            if xml:
                if name == "Anthropic":
                    items = parse_anthropic_html(xml, name)
                    items = enrich_anthropic_items(items, cfg.proxy, cfg.timeout)
                else:
                    items = parse_feed(xml, name)
                for it in items:
                    it.link = normalize_url(it.link)
                all_items.extend(items)
                stats["success"] += 1
                source_results[name] = (len(items), "success", "")
                logging.debug("   %s: %d 条", name, len(items))
                if new_cache_entry.etag or new_cache_entry.last_modified:
                    cache[url] = new_cache_entry
            else:
                stats["failed"] += 1
                source_results[name] = (0, "failed", error_msg)
                logging.debug("   %s: 获取失败 - %s", name, error_msg)

    save_cache(cfg.cache_path, cache)

    print("📡 数据源状态:")
    for name in cfg.sources.keys():
        count, status, error = source_results.get(name, (0, "pending", ""))
        if status == "success":
            print(f"   ✅ {name}: {count} 条")
        elif status == "cached":
            print(f"   💾 {name}: 缓存命中")
        elif status == "failed":
            print(f"   ❌ {name}: {error if error else '获取失败'}")
    print()

    print(f"📊 汇总: 成功 {stats['success']} | 缓存 {stats['cached']} | 失败 {stats['failed']}")
    print(f"📊 抓取条目: {len(all_items)} 条")

    primary, fallback = filter_items(
        all_items,
        cfg.include_keywords,
        cfg.exclude_keywords,
        cutoff,
        fallback_cutoff,
    )

    result = primary if primary else fallback
    print(f"📊 过滤结果: {len(primary)} 条 ({cfg.hours}h) + {len(fallback)} 条 ({cfg.fallback_hours}h fallback)")
    print()

    result = dedupe_items(result)
    
    print("🌐 正在翻译和优化标题...")
    for it in result:
        it.original_title = it.title
        if not is_chinese(it.title):
            it.title = translate_text(it.title, cfg.proxy, cfg.timeout)
        it.title = enhance_title(it.title, it.description, it.source)
    print()

    for it in result:
        it.score = compute_score(it, cfg.source_weights, cfg.hot_keywords, now_utc, cfg.hours)

    result.sort(
        key=lambda x: (x.score, x.dt or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )

    if cfg.max_items and cfg.max_items > 0:
        result = result[:cfg.max_items]

    md = generate_markdown(result, cfg.hours, cfg.hot_keywords)

    output_path = Path(args.output) if args.output else (Path.cwd() / "daily-ai-news.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"✅ Saved: {output_path}")
    print()
    print("-" * 55)
    print(md)


if __name__ == "__main__":
    main()
