# lumada-oss-lite

Lumada的な「データ収集 → 統合 → 可視化 → AI（Agentic）」をOSSのみで再現する軽量PoCです。  
ローカル開発は Docker Compose のみで成立します。

## v0.1 成功定義

- `docker compose up -d --build` のみで主要サービスが起動する
- MQTT -> ingestion -> API -> PostgreSQL のデータ経路で `events` に保存できる
- `GET /health` が `200` を返す
- Grafana が起動し、PostgreSQL datasource が provisioning 済み

## v0.2 成功定義

- `POST /plan/generate?event_id={id}` で `plan_json` を生成・返却できる
- 生成した `plan_json` が `plans` テーブルへ保存される
- Orchestrator が Validator issues をもとに最大2回 retry できる
- Pydantic スキーマで計画構造が検証される

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

## v0.2 デモ手順（schemas -> validator/retry -> API）

1. MQTTでイベント投入（通常ケース）

```bash
docker compose exec mosquitto mosquitto_pub -h localhost -p 1883 -t telemetry/device-002 -m "{\"device_id\":\"device-002\",\"event_type\":\"temperature_alert\",\"ts\":\"2026-02-08T12:00:00Z\",\"payload\":{\"value\":88.2,\"unit\":\"C\"}}"
```

2. 直近の `event_id` を確認

```bash
docker compose exec postgres psql -U agentic -d agentic -c "SELECT id, device_id, event_type, ts FROM events ORDER BY id DESC LIMIT 5;"
```

3. 計画生成APIを実行

```bash
curl -X POST "http://localhost:8000/plan/generate?event_id=1"
```

4. plans 保存確認

```bash
docker compose exec postgres psql -U agentic -d agentic -c "SELECT id, event_id, status, plan_json->>'version' AS version FROM plans ORDER BY id DESC LIMIT 5;"
```

5. 最新計画取得（デバッグ用）

```bash
curl http://localhost:8000/plans/latest
```

6. retry動作の簡易確認（初回だけ不正priorityを混入）

```bash
docker compose exec mosquitto mosquitto_pub -h localhost -p 1883 -t telemetry/device-003 -m "{\"device_id\":\"device-003\",\"event_type\":\"anomaly\",\"ts\":\"2026-02-08T12:30:00Z\",\"payload\":{\"inject_invalid_priority_once\":true}}"
```

その後 `event_id` を指定して `POST /plan/generate` を呼ぶと、Validatorで不備検知後に再生成され、成功時は `plans` に保存されます。

## API仕様（v0.1）

- `GET /health` -> `{"status":"ok"}`
- `POST /ingest`
  - 入力: `device_id`, `event_type`, `ts`, `payload`
  - 動作: `events` へINSERT
  - 出力: `{"ok": true}`

## API仕様（v0.2追加）

- `POST /plan/generate?event_id={id}`
  - 動作: `events` から1件取得 -> Orchestrator実行 -> `plans` に保存
  - 成功時: 保存済み `plan_json` を返却
  - 失敗時: `event_id` 未存在は `404`、retry上限超過は `422`
- `GET /plans/latest`
  - 動作: `plans` の最新1件を取得
  - 成功時: 最新 `plan_json`

## v0.1 スコープ外

ClickHouse / Kafka / MinIO / Airflow / Spark / MLflow / Kubernetes は導入しません。
