# Changelog
形式: Keep a Changelog + SemVer（vMAJOR.MINOR.PATCH）

## [Unreleased]
### Added
- Docker Composeのみで起動するPoC v0.1スキャフォールドを追加
- `api/` にFastAPI実装（`GET /health`, `POST /ingest`）を追加
- `ingestion/` にMQTT subscriber実装（API失敗時最大3回リトライ）を追加
- PostgreSQL初期化SQL（`infra/initdb/01_create_tables.sql`）を追加
- Grafana datasource provisioning（`dashboard/provisioning/datasources/datasource.yml`）を追加
- Windows向けLF固定設定（`.gitattributes`）を追加
- `agentic/app/schemas.py` に v0.2 用 `Issue` / `Task` / `MaintenancePlan` を追加
- `agentic/app/reader.py`, `agentic/app/planner.py`, `agentic/app/validator.py`, `agentic/app/generator.py`, `agentic/app/orchestrator.py` を追加
- `POST /plan/generate` と `GET /plans/latest` を追加し、`plans` への保存処理を実装
- `AGENTIC_FAULT_INJECTION=1` で初回生成を意図的に失敗させるretry検証機構を追加
- `POST /plan/generate` のログに `event_id`, `retry`, `issues` のINFO出力を追加
- `docs/issue_codes.md` を追加し、SCHEMA/DATA/BUSINESS のIssue体系を固定
- Validatorにビジネスルール（件数上限、総工数上限、必須タスク、安全停止、記録報告）を追加

### Changed
- `README.md` をDocker Compose中心のクイックスタートへ更新
- `api` コンテナが `agentic` パッケージを読み込めるよう、Compose build context と Dockerfile を更新
- `api/app/db.py` を拡張し、`events` 取得・`plans` 保存/取得に対応
- `README.md` に `Verification（v0.1 / v0.2）` 手順を追加し、Windows向けretry確認手順を明記
- `README.md` に Issueコード参照、Retry Strategy、Plan Versioning 方針を追加
- ValidatorのIssueコードを `SCHEMA_*` / `DATA_*` / `BUSINESS_*` 命名へ統一
- Orchestrator/Plannerを更新し、最新Issueに基づくretry修正戦略を明確化

### Fixed
- なし

### Removed
- なし
