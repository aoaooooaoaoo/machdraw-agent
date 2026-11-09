# 多阶段构建：Node 构建前端 → Python 运行时（含预建的检索索引）
#
# 部署到 Render / Fly / 任意容器平台时，端口由平台通过 $PORT 注入；
# 本地直接 `docker compose up` 时不设 PORT，回落到 8077。

# ---------- 阶段 1：构建前端 ----------
FROM node:22-alpine AS web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY apps/web/ ./
RUN npm run build

# ---------- 阶段 2：运行时 ----------
FROM python:3.12-slim
WORKDIR /app

# OCR：拍题/公式图片识别（离线，不依赖外部服务）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    RP_LLM_PROVIDER=mock

COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码 + 离线流水线 + 知识库
COPY apps/api/app ./apps/api/app
COPY apps/api/tests ./apps/api/tests
COPY apps/api/static ./apps/api/static
COPY pipeline ./pipeline
COPY kb ./kb
COPY eval ./eval
# 前端构建产物（由阶段 1 产出）
COPY --from=web /web/dist ./apps/web/dist

# 构建检索索引（离线，约 2–5 秒）
RUN python pipeline/build_kb.py

# 数据目录（SQLite 落在这里；容器平台通常是临时盘，重启会重置）
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8077

# 健康检查：跟随平台注入的 $PORT
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD python -c "import os,urllib.request,sys; p=os.environ.get('PORT','8077'); sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+p+'/api/health', timeout=4).status==200 else 1)"

# 用 sh -c 才能力展开 ${PORT}（exec 形式不展开环境变量）
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8077} --app-dir apps/api"]
