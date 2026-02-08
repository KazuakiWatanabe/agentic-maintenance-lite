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

### Changed
- `README.md` をDocker Compose中心のクイックスタートへ更新

### Fixed
- なし

### Removed
- なし
