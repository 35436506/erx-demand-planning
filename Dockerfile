# ERX Demand Planning — website học viên + Forecasting Lab trong một container.
# Railway tự nhận Dockerfile này. Chạy thử trên máy:  docker build -t erx-dpf . && docker run -p 8080:8080 erx-dpf
FROM caddy:2.8.4-alpine AS caddy

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY lab/requirements.txt /app/lab/requirements.txt
RUN pip install -r /app/lab/requirements.txt
COPY --from=caddy /usr/bin/caddy /usr/bin/caddy
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY deploy/start.sh /start.sh
COPY lab /app/lab
COPY site /srv/site
RUN chmod +x /start.sh
ENV PORT=8080
EXPOSE 8080
CMD ["/start.sh"]
