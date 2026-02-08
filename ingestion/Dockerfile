FROM python:3.12-slim

# 目的: MQTT購読して /ingest に転送する最小コンテナ
# 方針: シェルスクリプトを使わない / exec形式で起動 / 依存最小

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app

CMD ["python", "-m", "app.main"]
