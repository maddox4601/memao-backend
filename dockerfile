# 阶段1：构建依赖
FROM python:3.8-slim as builder
WORKDIR /memao-backend

# 安装系统构建依赖（如需编译MySQLclient）
RUN apt-get update && apt-get install -y \
    gcc python3-dev default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（不污染全局环境）
COPY requirements.txt .
RUN pip install --user -r requirements.txt gunicorn==20.1.0 gevent==21.8.0

# 阶段2：构建最终镜像
FROM python:3.8-slim
WORKDIR /memao-backend

# 拷贝依赖和项目文件
COPY --from=builder /root/.local /root/.local
COPY . .

# 设置 PATH 和常用环境变量
ENV PATH="/root/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1

# 暴露 Gunicorn 端口（可选）
EXPOSE 5000

# 启动命令
CMD ["gunicorn", "app:app"]
