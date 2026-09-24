# 基础镜像：Python 3.12 官方轻量版
FROM hub.rat.dev/library/python:3.12-slim

# 设置容器内的工作目录
WORKDIR /app

# 先复制依赖文件，利用Docker缓存加速构建
COPY requirements.txt .

# 安装Python依赖，使用清华源加速
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目所有代码到容器内
COPY . .

# 暴露服务端口
EXPOSE 8000

# 容器启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
