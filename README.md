# lumada-oss-lite

Lumada的な「データ収集 → 統合 → 可視化 → AI（Agentic）」をOSSのみで再現する軽量PoCです。  
PoC v0.1は、Docker Composeのみでローカル起動できる最小構成に限定しています。

## v0.1 成功定義

- `docker compose up -d --build` のみで主要サービスが起動する
- MQTT -> ingestion -> API -> PostgreSQL のデータ経路で `events` に保存できる
- `GET /health` が `200` を返す
- Grafana が起動し、PostgreSQL datasource が provisioning 済み

## 前提

- Windows 11 + Docker Desktop（または同等のDocker実行環境）
- ホストへの Python / PostgreSQL / Grafana / Mosquitto の個別インストールは不要

## クイックスタート

1. 起動

```bash
docker compose up -d --build
```

2. ヘルスチェック

```bash
curl http://localhost:8000/health
```

期待値:

```json
{"status":"ok"}
```

3. MQTTイベント送信（Compose内のmosquittoクライアントを使用）

```bash
docker compose exec mosquitto mosquitto_pub -h localhost -p 1883 -t telemetry/device-001 -m "{\"device_id\":\"device-001\",\"event_type\":\"temperature_alert\",\"ts\":\"2026-02-08T00:00:00Z\",\"payload\":{\"value\":95.1,\"unit\":\"C\"}}"
```

4. PostgreSQL保存確認

```bash
docker compose exec postgres psql -U agentic -d agentic -c "SELECT id, device_id, event_type, ts FROM events ORDER BY id DESC LIMIT 5;"
```

5. Grafana確認

- URL: `http://localhost:3000`
- ユーザー: `admin`
- パスワード: `admin`
- `Postgres` datasource が自動作成済み

## API仕様（v0.1）

- `GET /health` -> `{"status":"ok"}`
- `POST /ingest`
  - 入力: `device_id`, `event_type`, `ts`, `payload`
  - 動作: `events` へINSERT
  - 出力: `{"ok": true}`

## v0.1 スコープ外

ClickHouse / Kafka / MinIO / Airflow / Spark / MLflow / Kubernetes は導入しません。
