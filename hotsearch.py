#!/usr/bin/env python3
"""
热搜数据获取测试
- UAPI: 微博、百度、知乎、B站、抖音、今日头条
- TianAPI: 微信热搜
- ITAPI: 小红书热点
- 智能筛选：跨平台热度聚合，选出最重要的10条
- 飞书推送：发送到飞书群
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import re
import os
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# 飞书群 ID
FEISHU_GROUP_ID = "oc_3e108939f68467ddd73cedfb796642e8"

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

PROXY = os.environ.get("RSS_PROXY", "http://127.0.0.1:7890")

UAPI_BASE = "https://uapis.cn/api/v1/misc/hotboard"
TIANAPI_KEY = os.environ.get("TIANAPI_KEY", "")
TIANAPI_WXHOT = f"https://apis.tianapi.com/wxhottopic/index?key={TIANAPI_KEY}"
ITAPI_KEY = os.environ.get("ITAPI_KEY", "")
ITAPI_XIAOHONGSHU = f"https://api.itapi.cn/api/hotnews/xiaohongshu?key={ITAPI_KEY}"

UAPI_PLATFORMS = {
    "weibo": {"name": "微博热搜", "source": "微博", "weight": 1.0},
    "baidu": {"name": "百度热搜", "source": "百度", "weight": 1.0},
    "zhihu": {"name": "知乎热榜", "source": "知乎", "weight": 0.9},
    "bilibili": {"name": "B站热榜", "source": "B站", "weight": 0.8},
    "douyin": {"name": "抖音热点", "source": "抖音", "weight": 1.0},
    "toutiao": {"name": "今日头条", "source": "今日头条", "weight": 0.9},
}

TIANAPI_PLATFORMS = {
    "weixin": {"name": "微信热搜", "source": "微信", "weight": 1.2},
}

ITAPI_PLATFORMS = {
    "xiaohongshu": {"name": "小红书热点", "source": "小红书", "weight": 0.9},
}

PLATFORM_ORDER = ["weibo", "baidu", "zhihu", "bilibili", "douyin", "toutiao", "weixin", "xiaohongshu"]

STOP_WORDS = {"的", "了", "是", "在", "有", "和", "与", "或", "等", "这", "那", "我", "你", "他", "她", "它", "们", "着", "过", "被", "把", "给", "向", "从", "到", "为", "以", "及", "其", "之", "上", "下", "中", "内", "外", "前", "后", "左", "右", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "百", "千", "万", "亿", "个", "只", "条", "件", "次", "名", "位", "种", "类", "样", "些", "多", "少", "大", "小", "长", "短", "高", "低", "快", "慢", "新", "老", "好", "坏", "对", "错", "真", "假", "能", "会", "要", "可", "应", "该", "须", "必", "需", "将", "已", "正", "再", "也", "就", "才", "都", "又", "还", "更", "最", "很", "太", "真", "实", "际", "现", "当", "应", "该", "因", "所", "而", "但", "却", "只", "仅", "已", "曾", "常", "总", "全", "每", "各", "某", "任", "何", "谁", "哪", "什", "么", "怎", "样", "几", "多", "少", "多", "久", "远", "近", "这", "那", "此", "彼", "某", "各", "每", "凡", "诸", "众", "群", "些", "若", "如", "似", "像", "同", "异", "比", "较", "最", "更", "很", "太", "极", "甚", "颇", "稍", "略", "较", "更", "最", "极", "甚", "颇", "稍", "略"}


def fetch_json(url: str, timeout: int = 15, headers: dict = None) -> dict:
    try:
        req = urllib.request.Request(url, headers=headers or HEADERS)
        handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
        opener = urllib.request.build_opener(handler, urllib.request.HTTPSHandler(context=SSL_CONTEXT))
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def get_uapi_hot(platform: str, limit: int = 20) -> list:
    if platform not in UAPI_PLATFORMS:
        return []
    
    config = UAPI_PLATFORMS[platform]
    print(f"   方法: UAPI ({config['name']})")
    
    url = f"{UAPI_BASE}?type={platform}"
    data = fetch_json(url)
    
    if "error" in data:
        print(f"   ❌ 请求失败: {data['error']}")
        return []
    
    if "list" not in data:
        print(f"   ❌ 数据格式错误")
        return []
    
    items = []
    for idx, item in enumerate(data["list"][:limit], 1):
        items.append({
            "title": item.get("title", ""),
            "hot": item.get("hot_value", ""),
            "url": item.get("url", ""),
            "source": config["source"],
            "platform": platform,
            "rank": idx,
            "weight": config["weight"],
        })
    
    print(f"   ✅ 获取 {len(items)} 条")
    return items


def get_weixin_hot(limit: int = 20) -> list:
    config = TIANAPI_PLATFORMS["weixin"]
    print(f"   方法: TianAPI ({config['name']})")
    
    data = fetch_json(TIANAPI_WXHOT)
    
    if "error" in data:
        print(f"   ❌ 请求失败: {data['error']}")
        return []
    
    if data.get("code") != 200:
        print(f"   ❌ API错误: {data.get('msg', '未知错误')}")
        return []
    
    items = []
    for idx, item in enumerate(data.get("result", {}).get("list", [])[:limit], 1):
        items.append({
            "title": item.get("word", ""),
            "hot": "",
            "url": f"https://weixin.sogou.com/weixin?type=2&query={urllib.parse.quote(item.get('word', ''))}",
            "source": config["source"],
            "platform": "weixin",
            "rank": idx,
            "weight": config["weight"],
        })
    
    print(f"   ✅ 获取 {len(items)} 条")
    return items


def get_xiaohongshu_hot(limit: int = 20) -> list:
    config = ITAPI_PLATFORMS["xiaohongshu"]
    print(f"   方法: ITAPI ({config['name']})")
    
    data = fetch_json(ITAPI_XIAOHONGSHU)
    
    if "error" in data:
        print(f"   ❌ 请求失败: {data['error']}")
        return []
    
    if data.get("code") != 200:
        print(f"   ❌ API错误: {data.get('msg', '未知错误')}")
        return []
    
    items = []
    for item in data.get("data", [])[:limit]:
        items.append({
            "title": item.get("name", ""),
            "hot": item.get("viewnum", ""),
            "url": item.get("url", ""),
            "source": config["source"],
            "platform": "xiaohongshu",
            "rank": item.get("rank", 0),
            "weight": config["weight"],
        })
    
    print(f"   ✅ 获取 {len(items)} 条")
    return items


def get_hot_list(platform: str, limit: int = 20) -> list:
    if platform == "weixin":
        return get_weixin_hot(limit)
    elif platform == "xiaohongshu":
        return get_xiaohongshu_hot(limit)
    elif platform in UAPI_PLATFORMS:
        return get_uapi_hot(platform, limit)
    else:
        print(f"   ❌ 不支持的平台: {platform}")
        return []


def get_all_hot_lists(platforms: list = None, limit: int = 20) -> dict:
    if platforms is None:
        platforms = PLATFORM_ORDER
    
    results = {}
    for platform in platforms:
        results[platform] = get_hot_list(platform, limit)
    
    return results


def get_platform_name(platform: str) -> str:
    if platform in UAPI_PLATFORMS:
        return UAPI_PLATFORMS[platform]["name"]
    elif platform in TIANAPI_PLATFORMS:
        return TIANAPI_PLATFORMS[platform]["name"]
    elif platform in ITAPI_PLATFORMS:
        return ITAPI_PLATFORMS[platform]["name"]
    return platform


def get_platform_weight(platform: str) -> float:
    if platform in UAPI_PLATFORMS:
        return UAPI_PLATFORMS[platform]["weight"]
    elif platform in TIANAPI_PLATFORMS:
        return TIANAPI_PLATFORMS[platform]["weight"]
    elif platform in ITAPI_PLATFORMS:
        return ITAPI_PLATFORMS[platform]["weight"]
    return 1.0


def normalize_title(title: str) -> str:
    title = re.sub(r'[^\w\s\u4e00-\u9fff]', '', title)
    title = title.lower().strip()
    return title


def extract_keywords(title: str) -> set:
    normalized = normalize_title(title)
    words = set()
    current_word = ""
    
    for char in normalized:
        if '\u4e00' <= char <= '\u9fff':
            if current_word:
                if current_word not in STOP_WORDS and len(current_word) > 1:
                    words.add(current_word)
                current_word = ""
            if char not in STOP_WORDS:
                words.add(char)
        elif char.isalnum():
            current_word += char
        else:
            if current_word and current_word not in STOP_WORDS and len(current_word) > 1:
                words.add(current_word)
            current_word = ""
    
    if current_word and current_word not in STOP_WORDS and len(current_word) > 1:
        words.add(current_word)
    
    return words


def jaccard_similarity(set1: set, set2: set) -> float:
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def calculate_similarity(title1: str, title2: str) -> float:
    if not title1 or not title2:
        return 0.0
    
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    
    if norm1 == norm2:
        return 1.0
    
    if norm1 in norm2 or norm2 in norm1:
        return 0.9
    
    kw1 = extract_keywords(title1)
    kw2 = extract_keywords(title2)
    
    return jaccard_similarity(kw1, kw2)


def parse_hot_value(hot_str: str) -> float:
    if not hot_str:
        return 0.0
    
    hot_str = str(hot_str).strip()
    
    try:
        if '亿' in hot_str:
            num = float(re.sub(r'[^\d.]', '', hot_str.replace('亿', '')))
            return num * 100000000
        elif '万' in hot_str:
            num = float(re.sub(r'[^\d.]', '', hot_str.replace('万', '')))
            return num * 10000
        else:
            num = float(re.sub(r'[^\d.]', '', hot_str))
            return num
    except:
        return 0.0


def select_top_news(all_items: list, top_n: int = 10, similarity_threshold: float = 0.6) -> list:
    if not all_items:
        return []
    
    clusters = []
    
    for item in all_items:
        matched = False
        for cluster in clusters:
            if calculate_similarity(item["title"], cluster["title"]) >= similarity_threshold:
                cluster["items"].append(item)
                matched = True
                break
        
        if not matched:
            clusters.append({
                "title": item["title"],
                "items": [item],
            })
    
    scored_clusters = []
    for cluster in clusters:
        items = cluster["items"]
        
        platform_count = len(set(item["platform"] for item in items))
        platform_score = platform_count * 100
        
        rank_scores = []
        for item in items:
            rank_score = (21 - item["rank"]) * item["weight"]
            rank_scores.append(rank_score)
        avg_rank_score = sum(rank_scores) / len(rank_scores) if rank_scores else 0
        
        hot_values = []
        for item in items:
            hot = parse_hot_value(item.get("hot", ""))
            if hot > 0:
                hot_values.append(hot)
        max_hot = max(hot_values) if hot_values else 0
        hot_score = min(max_hot / 100000, 50)
        
        total_score = platform_score + avg_rank_score + hot_score
        
        platforms = [item["source"] for item in items]
        best_item = max(items, key=lambda x: (parse_hot_value(x.get("hot", "")), -x["rank"]))
        
        scored_clusters.append({
            "title": best_item["title"],
            "url": best_item["url"],
            "hot": best_item.get("hot", ""),
            "platforms": platforms,
            "platform_count": platform_count,
            "score": total_score,
        })
    
    scored_clusters.sort(key=lambda x: (-x["platform_count"], -x["score"]))
    
    return scored_clusters[:top_n]


def format_top_news(top_items: list) -> str:
    if not top_items:
        return "暂无数据"
    
    lines = []
    for i, item in enumerate(top_items, 1):
        title = item["title"]
        if len(title) > 30:
            title = title[:30] + "..."
        
        hot_str = f"🔥{item['hot']}" if item.get("hot") else ""
        cross_str = f"[{item['platform_count']}平台]" if item["platform_count"] > 1 else ""
        
        info_parts = [p for p in [hot_str, cross_str] if p]
        info_str = " ".join(info_parts)
        
        lines.append(f"**{i}. {title}**")
        if info_str:
            lines.append(f"   {info_str}")
        lines.append(f"   [查看详情]({item['url']})")
        lines.append("")
    
    return "\n".join(lines)


def format_hot_list(items: list, show_hot: bool = True) -> str:
    if not items:
        return "暂无数据"
    
    lines = []
    for i, item in enumerate(items, 1):
        title = item["title"]
        if len(title) > 25:
            title = title[:25] + "..."
        
        hot_str = f"🔥{item['hot']}" if show_hot and item.get("hot") else ""
        
        if hot_str:
            lines.append(f"{i}. {title} {hot_str}")
        else:
            lines.append(f"{i}. {title}")
    
    return "\n".join(lines)


def generate_markdown_report(results: dict, top_news: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        "# 📱 热搜速递",
        "",
        f"⏰ {now}",
        "",
        "---",
        "",
        "## 🔥 TOP 10 热点",
        "",
    ]
    
    lines.append(format_top_news(top_news))
    
    lines.append("---")
    lines.append("")
    lines.append("## 📋 各平台热搜")
    lines.append("")
    
    for platform, items in results.items():
        name = get_platform_name(platform)
        
        lines.append(f"**{name}**")
        if items:
            lines.append(format_hot_list(items))
        else:
            lines.append("❌ 获取失败")
        lines.append("")
    
    return "\n".join(lines)


def format_feishu_message(top_items: list, total_count: int, platforms: list) -> str:
    """格式化飞书消息"""
    if not top_items:
        return "暂无数据"

    lines = ["📱 今日热点速递", ""]
    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("🔥 TOP 10 热点")
    lines.append("")

    for i, item in enumerate(top_items, 1):
        title = item["title"]
        if len(title) > 30:
            title = title[:30] + "..."
        
        hot_str = f"🔥{item['hot']}" if item.get("hot") else ""
        cross_str = f"[{item['platform_count']}平台]" if item["platform_count"] > 1 else ""
        
        info_parts = [p for p in [hot_str, cross_str] if p]
        info_str = " ".join(info_parts)
        
        lines.append(f"**{i}. {title}**")
        if info_str:
            lines.append(f"   {info_str}")
        lines.append(f"   [查看详情]({item['url']})")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"📊 统计: {total_count}条热搜 | {len(platforms)}个平台")

    return "\n".join(lines)


def send_to_feishu(message: str) -> bool:
    """发送消息到飞书群"""
    try:
        import subprocess
        import os

        # 设置环境变量（nvm 环境）
        env = os.environ.copy()
        env["PATH"] = f"/Users/linux/.nvm/versions/node/v22.22.0/bin:{env['PATH']}"

        # OpenClaw 命令路径
        openclaw_path = "/Users/linux/.nvm/versions/node/v22.22.0/bin/openclaw"

        cmd = [
            openclaw_path, "message", "send",
            "--channel", "feishu",
            "--target", FEISHU_GROUP_ID,
            "--message", message
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        if result.returncode == 0:
            print("✅ 已成功发送到飞书群")
            return True
        else:
            print(f"❌ 发送到飞书失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 发送到飞书失败: {e}")
        return False


def main():
    print("=" * 60)
    print("热搜数据获取测试 - 智能筛选版")
    print("=" * 60)
    
    results = get_all_hot_lists(PLATFORM_ORDER)
    
    all_items = []
    for platform, items in results.items():
        all_items.extend(items)
    
    print(f"\n� 共获取 {len(all_items)} 条热搜数据")
    
    print("\n🔍 智能筛选 TOP 10...")
    top_news = select_top_news(all_items, top_n=10)
    
    print("\n" + "=" * 60)
    print("🔥 今日热点 TOP 10:")
    print("=" * 60)
    for i, item in enumerate(top_news, 1):
        platform_str = "、".join(item["platforms"][:3])
        if len(item["platforms"]) > 3:
            platform_str += f"等{len(item['platforms'])}平台"
        print(f"{i}. {item['title']}")
        print(f"   来源: {platform_str} | 得分: {item['score']:.1f}")
    
    print("\n" + "=" * 60)
    print("生成完整报告...")
    
    report = generate_markdown_report(results, top_news)
    
    output_file = "/tmp/hotsearch-test.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n" + "=" * 60)
    print(f"✅ 已保存到: {output_file}")

    # 发送到飞书群
    print("\n" + "=" * 60)
    print("📤 发送到飞书群...")

    feishu_message = format_feishu_message(top_news, len(all_items), list(results.keys()))
    if send_to_feishu(feishu_message):
        print("✅ 已成功发送到飞书群")
    else:
        print("❌ 发送到飞书群失败")


if __name__ == "__main__":
    main()
