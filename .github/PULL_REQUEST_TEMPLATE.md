cat > .github/PULL_REQUEST_TEMPLATE.md << 'EOF'
# 概要
<!-- 何を、なぜ変更したか（1〜3行で） -->

## 変更種別
- [ ] feature（新機能）
- [ ] fix（バグ修正）
- [ ] docs（ドキュメント）
- [ ] refactor（リファクタ）
- [ ] chore（依存更新・CI等）

## 関連 Issue / Discussion
- Issue: #
- Related: #

---

# 変更内容
## 追加・更新したもの
- 

## 影響範囲（スコープ）
- 影響するコンポーネント: ingestion / api / agentic / dashboard / infra など
- 互換性: 破壊的変更の有無（Yes/No）

---

# 動作確認
## ローカル（必須）
- [ ] `docker compose up` で起動できる
- [ ] ingestion（MQTT→DB）経路の確認
- [ ] Grafana が表示できる（任意でもOK）

## AI/Agentic（該当時）
- [ ] reader → planner → validator → generator の順に実行される
- [ ] validator が issues を返した場合に retry される
- [ ] 出力がスキーマ（Pydantic等）に合致する

---

# 品質ゲート（必須）
- [ ] Python: black / isort / ruff（またはflake8）相当が通る
- [ ] 日本語docstring（ファイル/クラス/関数/Note/主要変数説明）がある
- [ ] secrets / APIキーを含まない

---

# リリースノート候補（CHANGELOG追記用）
<!-- タグ付け時に載せたい1行 -->
- 

# スクリーンショット / 参考（任意）
- 
EOF
