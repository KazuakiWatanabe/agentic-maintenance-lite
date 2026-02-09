# Development Log: agentic-maintenance-lite

## Phase 1: v0.1 基盤構築

### 目的
Dockerのみで再現可能な OSS Lumada-lite パイプラインを構築する。

### 構成
- Mosquitto (MQTT)
- ingestion (MQTT subscriber)
- FastAPI (/health, /ingest)
- PostgreSQL
- Grafana (provisioning済)

### 成果
- docker compose up で完全起動
- MQTT → API → DB 保存確認
- Grafana datasource 自動生成
- Windows耐性（LF固定、.gitattributes、相対パス）

---

## Phase 2: v0.2 Agentic 実装

### 目的
events → MaintenancePlan JSON を生成する構造を実装。

### Agent構造
- Reader
- Planner（ルールベース）
- Validator（schema + business rule）
- Generator
- Orchestrator（retry 最大2回）

### API追加
- POST /plan/generate?event_id=...

### 検証
- events → plans 保存確認
- AGENTIC_FAULT_INJECTION=1 による retry 動作確認

---

## Phase 3: 設計強化

### 追加内容
- Issueコード体系を固定（docs/issue_codes.md）
- Retry戦略をREADMEに明文化
- plan.version = "0.2" 固定管理
- Validatorにビジネスルール追加
  - タスク上限
  - 総工数上限
  - 必須タスク
  - 安全停止ルール
  - 記録タスク必須

---

## 技術的判断ログ

### LLMをv0.2では入れなかった理由
- Windows環境の安定性優先
- 構造（validator + retry）を先に完成させるため

### スコープ制御
- ClickHouse/Kafka等は導入しない
- Compose 5サービス以内維持

---

## 次の候補

- v0.3: PlannerをLLM化（Ollama）
- ダッシュボード強化
- Retryログの構造化
