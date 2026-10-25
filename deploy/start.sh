#!/bin/sh
# Khởi động Forecasting Lab (nội bộ) và máy chủ web Caddy (cổng công khai $PORT do Railway cấp).
set -e
export PORT="${PORT:-8080}"
cd /app/lab
streamlit run app.py \
  --server.port 8501 --server.address 127.0.0.1 \
  --server.baseUrlPath lab --server.headless true \
  --browser.gatherUsageStats false &
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
