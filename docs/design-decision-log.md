# Design Decision Log
Project: agentic-maintenance-lite

---

## 1. 初期構想

### 目的
Lumada的構造（データ収集→統合→可視化→知能化）を
OSSのみで軽量に再現する。

### 判断
- 重厚な基盤（Kafka/ClickHouse等）は採用しない
- まずは再現性とデモ可能性を優先

### 理由
PoCの成功率を最大化するため。
スコープを広げることは価値ではない。

---

## 2. v0.1 基盤構築

### 判断
Docker Composeのみで完結する構成に固定。

### 技術選択
- Mosquitto
- FastAPI
- PostgreSQL
- Grafana

### 採用しなかったもの
- ClickHouse（重い）
- Kubernetes（不要）
- Airflow（過剰）

### 理由
「検討範囲を適切な方向性かつ有効な大きさで固定する」ことを優先。

---

## 3. Agentic設計の導入（v0.2）

### 判断
LLMは使わない。

### 理由
AIの有無より、構造（validator + retry + schema）を完成させることが本質。

### 構造決定
- Reader
- Planner（ルールベース）
- Validator
- Generator
- Orchestrator（最大2回retry）

### 意図
AIは差し替え可能な部品にする。

---

## 4. Issueコード体系の固定

### 判断
Validatorのエラーを「体系化」する。

### 理由
retryの意味を明確化し、
構造的に修正可能な設計にするため。

### カテゴリ
- SCHEMA
- BUSINESS
- DATA
- SYSTEM

---

## 5. Retry戦略の明文化

### 判断
最大2回。

### 理由
無限ループ回避。
PoCとしての決定論的振る舞いを保証する。

---

## 6. plan.version の導入

### 判断
v0.2固定。

### 理由
将来的な構造変更（v0.3 LLM化）との互換境界を作る。

---

## 7. Business Ruleの導入

### 追加ルール
- タスク数上限
- 総工数上限
- 必須安全タスク
- 記録タスク必須

### 意図
スキーマ検証だけでなく、
「意味のある妥当性」へ拡張。

---

## 8. 設計思想の変遷

### 初期
技術スタック中心。

### 中盤
Agentic構造中心。

### 現在
スコープ設計と検証構造が中心。

---

## 9. 現在の到達点

- Dockerのみで再現可能
- 構造的Agentic成立
- retry検証可能
- 設計思想がドキュメント化

---

## 10. 次の分岐

- v0.3 LLM導入
- 可視化強化
- 外部API接続
- マルチイベント連鎖処理

---

