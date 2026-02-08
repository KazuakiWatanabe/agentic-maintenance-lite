FROM python:3.12-slim

# 目的: Windows環境でも動く最小FastAPIコンテナ
# 方針: シェルスクリプトを使わない / exec形式で起動 / 依存最小

WORKDIR /app

# 依存を先に入れてキャッシュを効かせる
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# アプリ本体
COPY app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
