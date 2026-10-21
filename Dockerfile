# 单容器：静态页面 + 数据同步 API（Python 标准库，无第三方依赖）
FROM python:3.12-alpine

LABEL org.opencontainers.image.title="checkinplan" \
      org.opencontainers.image.description="一年级学习打卡页 + 语文数学练习生成器（含数据同步 API）" \
      org.opencontainers.image.source="https://github.com/blackanubis/checkinplan"

WORKDIR /app
COPY server/ /app/server/
COPY html/  /app/html/

ENV CP_WWW=/app/html \
    CP_DATA=/data \
    CP_PORT=80 \
    TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

EXPOSE 80
VOLUME ["/data"]

CMD ["python", "-u", "/app/server/app.py"]
