FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装Trivy
RUN wget https://github.com/aquasecurity/trivy/releases/latest/download/trivy_0.50.0_Linux-64bit.deb \
    && dpkg -i trivy_0.50.0_Linux-64bit.deb \
    && rm trivy_0.50.0_Linux-64bit.deb

# 设置工作目录
WORKDIR /app

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY operator/ ./operator/

# 创建非root用户
RUN useradd -m -u 1000 scanner && chown -R scanner:scanner /app
USER scanner

# 预下载Trivy数据库（可选，加快首次启动）
# RUN trivy image --download-db-only

# 暴露端口
EXPOSE 9443 8080

# 设置Python路径
ENV PYTHONPATH=/app

# 启动命令
CMD ["kopf", "run", "--module", "operator.main", "--verbose"]
