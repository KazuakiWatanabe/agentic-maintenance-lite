# Issue Codes (v0.2)

このドキュメントは、`agentic` の Validator/Planner が扱う Issue コード体系を固定する。

## 命名規則

- `SCHEMA_*`: 構造/型/必須項目の不備
- `BUSINESS_*`: 業務ルール/安全/運用上の不備
- `DATA_*`: 入力データ（event由来）の不備
- `SYSTEM_*`: 例外/内部エラー（原則HTTP 500で扱い、Issueにしない方針）

## SYSTEM系の方針

- `SYSTEM_*` は通常 `issues[]` に含めず、API側で `500` として処理する。
- PoC v0.2では、`/plan/generate` の内部例外は `HTTP 500` を返す。

## Issue一覧（v0.2）

### SCHEMA_TASKS_EMPTY

- 意味: `tasks` が空、または配列として扱えない
- path例: `tasks`
- 修正方針: Plannerがイベント種別に応じた既定タスクを再生成する
- 重大度: `error`

### SCHEMA_MISSING_SUMMARY

- 意味: `summary` が空文字または空白のみ
- path例: `summary`
- 修正方針: Plannerが既定サマリーを補完する
- 重大度: `error`

### SCHEMA_TASK_INVALID_TEXT

- 意味: `tasks[i].title` または `tasks[i].description` が空
- path例: `tasks[2].title`
- 修正方針: Plannerが既定文言で補完する
- 重大度: `error`

### SCHEMA_INVALID_PRIORITY

- 意味: `tasks[i].priority` が 1〜5 範囲外
- path例: `tasks[0].priority`
- 修正方針: Plannerが 1〜5 に丸める（通常は3を基準）
- 重大度: `error`

### SCHEMA_INVALID_ESTIMATE

- 意味: `tasks[i].estimated_minutes` が 1未満または不正型
- path例: `tasks[1].estimated_minutes`
- 修正方針: Plannerが妥当な既定値（例: 15分）へ補正する
- 重大度: `error`

### SCHEMA_MISSING_SAFETY_NOTES

- 意味: `safety_notes` が空、または空文字を含む
- path例: `tasks[3].safety_notes`
- 修正方針: Plannerが安全注意文を最低1件補完する
- 重大度: `error`

### DATA_MISSING_EVENT_FIELDS

- 意味: `event` に `device_id` / `event_type` / `ts` / `payload` が欠ける、または型不正
- path例: `event.payload`
- 修正方針: 原データ起因のため、入力イベントの補正を優先する（Planner修正だけでは解消不能）
- 重大度: `error`

### BUSINESS_MAX_TOTAL_MINUTES_EXCEEDED

- 意味: タスク総工数が上限（240分）を超過
- path例: `tasks[*].estimated_minutes`
- 修正方針: Plannerが低優先タスクの工数短縮または統合を実施する
- 重大度: `warn`

### BUSINESS_TOO_MANY_TASKS

- 意味: タスク件数が上限（8件）を超過
- path例: `tasks`
- 修正方針: Plannerが類似タスクを統合し、件数を削減する
- 重大度: `warn`

### BUSINESS_REQUIRED_TASK_MISSING

- 意味: `event_type` 別に必須の確認タスクが存在しない
- path例: `tasks`
- 修正方針:
  - `temperature`: sensor check / threshold confirm 系を追加
  - `vibration`: bearing/fixture check 系を追加
  - `anomaly`: safety confirm 系を追加
- 重大度: `error`

### BUSINESS_SAFETY_STOP_REQUIRED

- 意味: `event.payload.severity >= 4` なのに停止/隔離タスクが存在しない
- path例: `event.payload.severity`
- 修正方針: Plannerが停止/隔離タスクを優先度1で先頭へ追加する
- 重大度: `error`

### BUSINESS_CONTACT_REQUIRED

- 意味: 記録/報告（連絡）タスクが存在しない
- path例: `tasks`
- 修正方針: Plannerが記録/報告タスクを末尾へ追加する
- 重大度: `warn`
