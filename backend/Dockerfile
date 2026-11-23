# 多阶段构建：前端构建产物直接由后端托管，单容器、断网可演示
# 注意：本文件尚未在本机验证（未安装 Docker），首次构建请在 CI 或本地确认。

FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY fixtures/ /fixtures/
COPY --from=web /web/dist /app/../frontend/dist

# 数据卷：把导出的 platform.db 挂进来，镜像里不带数据
ENV PLATFORM_DATA_DIR=/data
VOLUME ["/data"]

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
