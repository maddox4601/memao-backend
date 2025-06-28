# 阶段1：构建依赖
FROM python:3.8-slim as builder  # 明确指定 3.8 版本
WORKDIR /memao-backend

# 安装系统依赖（如需编译C扩展，如MySQLclient）
RUN apt-get update && apt-get install -y \
    gcc python3-dev default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --user -r requirements.txt gunicorn==20.1.0 gevent==21.8.0  # 注意 gevent 版本兼容性

# 阶段2：运行环境
FROM python:3.8-slim  # 保持与构建阶段一致
WORKDIR /memao-backend

# 从builder阶段复制已安装的依赖
COPY --from=builder /root/.local /root/.local
COPY . .

# 设置环境变量
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    GUNICORN_CMD_ARGS="--workers=4 --bind=:5000 --timeout=120 --worker-class=gevent"

CMD ["gunicorn", "app:app"]