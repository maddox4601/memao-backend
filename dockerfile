# 阶段1：构建依赖
FROM python:3.8-slim as builder
WORKDIR /memao-backend

# 安装系统构建依赖（用于编译 MySQLclient 等）
RUN apt-get update && apt-get install -y \
    gcc python3-dev default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（不使用 --user）
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt \
    gunicorn==20.1.0 gevent==23.9.1

# 阶段2：构建最终镜像
FROM python:3.8-slim
WORKDIR /memao-backend

# 安装运行时所需的 libmysqlclient 运行库
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 拷贝 Python 依赖（从 builder 阶段）
COPY --from=builder /install /usr/local

# 拷贝项目文件
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 暴露端口（可选）
EXPOSE 5000

# 启动 Gunicorn
CMD ["gunicorn", "-w", "3", "-k", "gevent", "-b", "0.0.0.0:5000", "wsgi:app"]
