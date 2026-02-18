#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_FILE="${OUTPUT_FILE:-/tmp/daily-ai-news.md}"

if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

cd "$SCRIPT_DIR" && python3 generate-rss-news.py \
  -o "$OUTPUT_FILE" \
  --hours 24 \
  --fallback-hours 48 \
  --max-items 10 \
  ${RSS_PROXY:+--proxy "$RSS_PROXY"} \
  ${RSS_INSECURE_SSL:+--insecure-ssl}

if [ -n "$FEISHU_WEBHOOK" ]; then
  curl -X POST "$FEISHU_WEBHOOK" \
    -H "Content-Type: application/json" \
    -d "{\"msg_type\":\"text\",\"content\":{\"text\":\"$(cat "$OUTPUT_FILE" | sed 's/"/\\"/g' | tr '\n' '\\n')\"}}"
elif [ -n "$FEISHU_TARGET_ID" ]; then
  if command -v openclaw &> /dev/null; then
    openclaw message send \
      --channel feishu \
      --target "$FEISHU_TARGET_ID" \
      --message "$(cat "$OUTPUT_FILE")"
  else
    echo "⚠️ openclaw CLI 未安装，请使用 FEISHU_WEBHOOK 方式"
    echo "📄 报告已保存到: $OUTPUT_FILE"
  fi
else
  echo "⚠️ 未配置飞书推送，请设置 FEISHU_WEBHOOK 或 FEISHU_TARGET_ID 环境变量"
  echo "📄 报告已保存到: $OUTPUT_FILE"
fi
