# lumada-oss-lite
Lumada的な「データ収集 → 統合 → 可視化 → AI（Agentic）による業務設計」を、OSSのみで再現する軽量PoC。

## 目的
- テンプレを当てるだけではなく、PoCの検討開始時点で **適切な方向性 × 有効なスコープサイズ** を固定し、成功確率を最大化する
- “AIは手段”として、検討空間（スコープ）の設計を中心に据える

## 何ができるか（PoC v1）
- MQTT（擬似センサ/ログ）を取り込み
- PostgreSQL に保存
- Grafana で可視化
- 異常イベント発生時に Agentic（reader/planner/validator/generator）が
  - 事象を要約し
  - 保守作業計画（実行可能JSON）を生成する


## Branch Strategy
- main: 常に動く（デモ可能／READMEとcomposeが整っている状態）
- develop: 次リリース候補の統合先
- feature/*: 機能追加（短命）
- fix/*: バグ修正（短命）
- docs/*: ドキュメントのみ（短命）

## アーキテクチャ（軽量）
Device Simulator → MQTT(Mosquitto)
↓
Ingest API(FastAPI)
↓
PostgreSQL
↓ ↓
Grafana Dashboard Agentic(AI)
- reader: 異常要約
- planner: 作業案
- validator: 検証 + retry判定
- generator: 実行可能JSON生成

## Release / Tags
- vMAJOR.MINOR.PATCH（例: v0.1.0）
- mainにマージしたタイミングでタグを付け、CHANGELOGを確定する