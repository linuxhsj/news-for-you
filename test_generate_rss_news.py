#!/usr/bin/env python3

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "generate_rss_news",
    Path(__file__).parent / "generate-rss-news.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules["generate_rss_news"] = module
spec.loader.exec_module(module)

from generate_rss_news import (
    NewsItem,
    CacheEntry,
    Config,
    parse_date,
    normalize_url,
    is_hot,
    compute_score,
    dedupe_items,
    filter_items,
    generate_markdown,
)


class TestNewsItem(unittest.TestCase):
    def test_to_dict(self):
        item = NewsItem(
            title="Test Title",
            link="https://example.com",
            pubdate="2024-01-01",
            description="Test desc",
            source="TestSource",
        )
        d = item.to_dict()
        self.assertEqual(d["title"], "Test Title")
        self.assertEqual(d["link"], "https://example.com")
        self.assertEqual(d["source"], "TestSource")

    def test_from_dict(self):
        d = {
            "title": "Test",
            "link": "https://example.com",
            "pubdate": "2024-01-01",
            "description": "desc",
            "source": "Source",
        }
        item = NewsItem.from_dict(d)
        self.assertEqual(item.title, "Test")
        self.assertEqual(item.link, "https://example.com")


class TestCacheEntry(unittest.TestCase):
    def test_is_expired(self):
        entry = CacheEntry(etag="abc", timestamp=0)
        self.assertFalse(entry.is_expired())

        import time
        entry_recent = CacheEntry(etag="abc", timestamp=time.time() - 3600)
        self.assertFalse(entry_recent.is_expired(48))

        entry_old = CacheEntry(etag="abc", timestamp=time.time() - 100 * 3600)
        self.assertTrue(entry_old.is_expired(48))

    def test_to_dict_and_from_dict(self):
        entry = CacheEntry(etag="etag123", last_modified="Mon, 01 Jan 2024", timestamp=12345.0)
        d = entry.to_dict()
        self.assertEqual(d["etag"], "etag123")

        restored = CacheEntry.from_dict(d)
        self.assertEqual(restored.etag, "etag123")
        self.assertEqual(restored.timestamp, 12345.0)


class TestConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = Config()
        self.assertEqual(cfg.hours, 24)
        self.assertEqual(cfg.fallback_hours, 48)
        self.assertEqual(cfg.max_items, 10)

    @patch("builtins.open", create=True)
    def test_from_file_error(self, mock_open):
        mock_open.side_effect = FileNotFoundError()
        cfg = Config.from_file("/nonexistent.json")
        self.assertEqual(cfg.hours, 24)


class TestParseDate(unittest.TestCase):
    def test_rfc2822(self):
        dt = parse_date("Mon, 01 Jan 2024 12:00:00 +0000")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 1)

    def test_iso8601(self):
        dt = parse_date("2024-01-01T12:00:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2024)

    def test_iso8601_with_tz(self):
        dt = parse_date("2024-01-01T12:00:00+08:00")
        self.assertIsNotNone(dt)

    def test_empty(self):
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date(None))

    def test_invalid(self):
        self.assertIsNone(parse_date("invalid date"))


class TestNormalizeUrl(unittest.TestCase):
    def test_basic(self):
        url = normalize_url("https://example.com/path")
        self.assertEqual(url, "https://example.com/path")

    def test_remove_utm(self):
        url = normalize_url("https://example.com?utm_source=test&id=123")
        self.assertNotIn("utm_source", url)
        self.assertIn("id=123", url)

    def test_remove_fragment(self):
        url = normalize_url("https://example.com#section")
        self.assertNotIn("#section", url)

    def test_empty(self):
        self.assertEqual(normalize_url(""), "")


class TestIsHot(unittest.TestCase):
    def test_hot_keyword(self):
        item = NewsItem(title="OpenAI 发布 GPT-5", link="https://example.com")
        self.assertTrue(is_hot(item, ["OpenAI", "GPT-5"]))

    def test_not_hot(self):
        item = NewsItem(title="普通技术文章", link="https://example.com")
        self.assertFalse(is_hot(item, ["OpenAI", "GPT-5"]))

    def test_case_insensitive(self):
        item = NewsItem(title="openai news", link="https://example.com")
        self.assertTrue(is_hot(item, ["OpenAI"]))


class TestComputeScore(unittest.TestCase):
    def test_source_weight(self):
        item = NewsItem(title="Test", link="https://example.com", source="OpenAI")
        now = datetime.now(timezone.utc)
        score = compute_score(item, {"OpenAI": 3.0}, [], now, 24)
        self.assertGreater(score, 0)

    def test_hot_keyword_bonus(self):
        item1 = NewsItem(title="Test", link="https://example.com", source="Test")
        item2 = NewsItem(title="OpenAI 发布新模型", link="https://example.com", source="Test")
        now = datetime.now(timezone.utc)
        score1 = compute_score(item1, {"Test": 1.0}, ["OpenAI"], now, 24)
        score2 = compute_score(item2, {"Test": 1.0}, ["OpenAI"], now, 24)
        self.assertGreater(score2, score1)

    def test_recency_bonus(self):
        now = datetime.now(timezone.utc)
        item_recent = NewsItem(
            title="Test",
            link="https://example.com",
            source="Test",
            dt=now - timedelta(hours=1),
        )
        item_old = NewsItem(
            title="Test",
            link="https://example.com",
            source="Test",
            dt=now - timedelta(hours=20),
        )
        score_recent = compute_score(item_recent, {"Test": 1.0}, [], now, 24)
        score_old = compute_score(item_old, {"Test": 1.0}, [], now, 24)
        self.assertGreater(score_recent, score_old)


class TestDedupeItems(unittest.TestCase):
    def test_dedupe_by_link(self):
        items = [
            NewsItem(title="Breaking News Today", link="https://example.com/1", source="A"),
            NewsItem(title="Different Story Here", link="https://example.com/1", source="B"),
            NewsItem(title="Unique Article Content", link="https://example.com/2", source="C"),
        ]
        result = dedupe_items(items)
        self.assertEqual(len(result), 2)

    def test_dedupe_by_title_source(self):
        items = [
            NewsItem(title="Same Title Here Now", link="", source="A"),
            NewsItem(title="Same Title Here Now", link="", source="A"),
            NewsItem(title="Different Title Content", link="", source="B"),
        ]
        result = dedupe_items(items)
        self.assertEqual(len(result), 2)
    
    def test_dedupe_similar_titles(self):
        items = [
            NewsItem(title="OpenAI releases GPT-5 model", link="https://a.com/1", source="A"),
            NewsItem(title="OpenAI releases GPT-5 model today", link="https://b.com/2", source="B"),
            NewsItem(title="Google announces new AI", link="https://c.com/3", source="C"),
        ]
        result = dedupe_items(items)
        self.assertEqual(len(result), 2)


class TestFilterItems(unittest.TestCase):
    def test_filter_include(self):
        now = datetime.now(timezone.utc)
        pubdate = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        items = [
            NewsItem(title="AI news", link="https://example.com/1", pubdate=pubdate),
            NewsItem(title="Sports news", link="https://example.com/2", pubdate=pubdate),
        ]
        cutoff = now - timedelta(hours=24)
        fallback = now - timedelta(hours=48)

        primary, fallback_list = filter_items(
            items, ["AI"], [], cutoff, fallback
        )
        self.assertEqual(len(primary), 1)
        self.assertEqual(primary[0].title, "AI news")

    def test_filter_exclude(self):
        now = datetime.now(timezone.utc)
        pubdate = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        items = [
            NewsItem(title="AI 融资新闻", link="https://example.com/1", pubdate=pubdate),
            NewsItem(title="AI 技术突破", link="https://example.com/2", pubdate=pubdate),
        ]
        cutoff = now - timedelta(hours=24)
        fallback = now - timedelta(hours=48)

        primary, _ = filter_items(
            items, ["AI"], ["融资"], cutoff, fallback
        )
        self.assertEqual(len(primary), 1)
        self.assertEqual(primary[0].title, "AI 技术突破")


class TestGenerateMarkdown(unittest.TestCase):
    def test_empty_items(self):
        md = generate_markdown([], 24, [])
        self.assertIn("暂无符合条件的资讯", md)

    def test_with_items(self):
        items = [
            NewsItem(
                title="Test Article",
                link="https://example.com",
                source="TestSource",
                dt=datetime.now(timezone.utc),
            )
        ]
        md = generate_markdown(items, 24, [])
        self.assertIn("Test Article", md)
        self.assertIn("TestSource", md)

    def test_hot_section(self):
        items = [
            NewsItem(
                title="OpenAI 发布新模型",
                link="https://example.com",
                source="TestSource",
                dt=datetime.now(timezone.utc),
            )
        ]
        md = generate_markdown(items, 24, ["OpenAI"])
        self.assertIn("重点速递", md)


if __name__ == "__main__":
    unittest.main()
