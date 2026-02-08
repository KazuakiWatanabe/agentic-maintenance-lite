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

## Verification（v0.1 / v0.2）

Issueコード体系: `docs/issue_codes.md`

### 1. 共通：クリーン起動（DB含め完全リセット）

```bash
docker compose down -v
docker compose up -d --build
```

### 2. v0.1 Verification（基盤：MQTT -> API -> Postgres + Grafana）

#### 2.1 APIヘルス

```bash
curl http://localhost:8000/health
```

期待:

- `200`
- `{"status":"ok"}`

#### 2.2 Grafana起動確認（datasource provisioning）

- URL: `http://localhost:3000`
- ログイン: `admin / admin`
- Datasources に `Postgres` が存在すること（自動作成済）

#### 2.3 MQTT publish（ホストにmosquitto_pub不要）

##### 2.3.1 ネットワーク名確認

```bash
docker network ls
```

`*_default` のようなネットワーク（例: `agentic-maintenance-lite_default`）を特定します。

##### 2.3.2 publish（`<COMPOSE_NETWORK>` を置換）

```bash
docker run --rm --network <COMPOSE_NETWORK> eclipse-mosquitto:2 mosquitto_pub -h mosquitto -p 1883 -t telemetry/test -m "{\"device_id\":\"dev-1\",\"event_type\":\"temperature\",\"ts\":\"2026-02-08T00:00:00Z\",\"payload\":{\"value\":42}}"
```

#### 2.4 events に保存されたことを確認（psqlもホスト不要）

```bash
docker compose exec postgres psql -U agentic -d agentic -c "select id, device_id, event_type, ts from events order by id desc limit 5;"
```

期待:

- 直前の publish が1件以上入っている

### 3. v0.2 Verification（Agentic：/plan/generate + plans保存 + retry）

#### 3.1 `event_id` を取得

2.4 のSQL結果から最新 `id`（`event_id`）を控えます。

#### 3.2 `/plan/generate` を叩く

```bash
curl -X POST "http://localhost:8000/plan/generate?event_id=<EVENT_ID>"
```

期待:

- `200`
- JSONが返る（`event_id`, `summary`, `tasks[]`, `version` を含む）

#### 3.3 plans に保存されたことを確認

```bash
docker compose exec postgres psql -U agentic -d agentic -c "select id, event_id, status, created_at from plans order by id desc limit 5;"
```

`plan_json` の最低限の整合も確認:

```bash
docker compose exec postgres psql -U agentic -d agentic -c "select plan_json->>'version' as version, jsonb_array_length(plan_json->'tasks') as tasks from plans order by id desc limit 1;"
```

期待:

- `version = 0.2`
- `tasks >= 1`

### 4. v0.2 retry 検証（意図的失敗 -> Validator -> Retry -> 成功）

fault injection は環境変数 `AGENTIC_FAULT_INJECTION=1` のときだけ有効化されます（既定は `0`）。

#### 4.1 再起動（Git Bash）

```bash
docker compose down
AGENTIC_FAULT_INJECTION=1 docker compose up -d --build
```

#### 4.2 再起動（PowerShell）

```powershell
docker compose down
$env:AGENTIC_FAULT_INJECTION="1"
docker compose up -d --build
```

#### 4.3 retry発生を確認

1. 2.3 の publish を実行
2. 2.4 で `event_id` を確認
3. 3.2 の `/plan/generate` を実行

期待:

- `200` で成功する
- APIログに retry が出る（少なくとも1回）

ログ例:

```text
plan.generate event_id=12 retry=1 issues=['SCHEMA_INVALID_PRIORITY']
```

## Retry Strategy

- retry発生条件: Validator が `issues[]` を返した場合のみ
- retry回数: 最大2回（初回 + retry2回で終了）
- issues の扱い:
  - retry時は「直前の issues」を Planner に渡して修正する
  - issues は累積せず、最新検証結果で上書きする
- 失敗時挙動:
  - 2回のretry後も issues が残る場合は `HTTP 422`
  - 返却ボディに `issues[]`（`code`, `message`, `path`）を含める
- ログ:
  - `event_id`, `retry_count`, `issue_codes` を INFO で出力する

## Plan Versioning

- `plan.version` はAPI互換境界として扱う
- v0.2 の `MaintenancePlan.version` はコード側で固定値 `"0.2"`（外部入力で変更不可）
- Generator は `model_dump()` の `version` をそのまま `plans.plan_json` に保存する
- 将来 `v0.3` で plan 構造を変更する場合にのみ `version` を変更する

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
