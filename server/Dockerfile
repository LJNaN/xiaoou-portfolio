FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# 依赖单独一层，改代码不会重装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# 图片和内容都走 bind mount（见 docker-compose.yml），不进镜像。
# 这里只把目录建好，省得首次启动时缩略图写不进去。
RUN mkdir -p /data/images/full /data/images/thumb /data/content

EXPOSE 5003

# 用 sh -c 才能读到 compose 传进来的 PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-5003} --proxy-headers"]
