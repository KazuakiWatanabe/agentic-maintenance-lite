"""イベント要約から保守計画を生成するPlanner Agentモジュール。

責務:
    event_type別のルールに基づいて実行可能な保守タスク列を生成する。
主な入出力:
    入力: イベント辞書、Reader要約、Validator issues（任意）
    出力: `MaintenancePlan`
重要な制約:
    issuesが渡された場合は不備箇所を修正して再生成し、再試行を前提に安定した出力を返す。
"""

from datetime import datetime, timezone
from typing import Any

from agentic.app.schemas import Issue, MaintenancePlan, Task


class PlannerAgent:
    """保守タスクをルールベースで組み立てるクラス。

    責務:
        イベント種別ごとに標準タスクを生成し、issuesに応じて補正する。
    主要メソッドの役割:
        `plan` が生成全体を統括し、`_repair_tasks` がissues対応を行う。
    前提・制約:
        v0.2ではLLMを使わず、固定ルールのみで計画を生成する。
    """

    def plan(
        self,
        event: dict[str, Any],
        summary: str,
        issues: list[Issue] | None = None,
    ) -> MaintenancePlan:
        """イベント情報と要約から保守計画を生成する。

        Args:
            event: DBイベント辞書。
            summary: Readerで生成した要約文字列。
            issues: Validatorから返却された修正要求一覧。

        Returns:
            MaintenancePlan: 生成または再生成した保守計画。

        Note:
            初回生成かつ `payload.inject_invalid_priority_once` が真の場合のみ、検証用に不正priorityを1回だけ混入する。

        Variables:
            event_kind: event_typeを温度/振動/異常へ正規化した種別。
            tasks_payload: `Task` へ変換する前段の辞書リスト。
            plan_payload: `MaintenancePlan` へ変換するための辞書。
        """
        # 主要変数: event_kind はルール選択のために正規化したイベント種別。
        event_kind = self._normalize_event_kind(str(event.get("event_type", "anomaly")))
        # 主要変数: tasks_payload はスキーマ変換前のタスク辞書列。
        tasks_payload = self._build_tasks(event_kind)

        # 主要変数: summary_text はissuesを反映する可能性がある要約文字列。
        summary_text = summary.strip()
        if issues:
            summary_text = self._repair_summary(summary_text)
            tasks_payload = self._repair_tasks(tasks_payload, issues)

        # 主要変数: plan_payload は最終的にMaintenancePlanへ変換する辞書本体。
        plan_payload = {
            "event_id": self._to_event_id(event),
            "summary": summary_text,
            "tasks": tasks_payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": "0.2",
        }

        # 主要変数: payload は初回リトライ検証用フラグを参照するためのイベントpayload。
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        inject_invalid_once = bool(payload.get("inject_invalid_priority_once"))
        if issues is None and inject_invalid_once and plan_payload["tasks"]:
            plan_payload["tasks"][0]["priority"] = 9
            return self._construct_without_validation(plan_payload)

        return MaintenancePlan.model_validate(plan_payload)

    def _normalize_event_kind(self, event_type: str) -> str:
        """イベント種別文字列をPlanner用のカテゴリへ正規化する。

        Args:
            event_type: 元のevent_type文字列。

        Returns:
            str: `temperature` / `vibration` / `anomaly` のいずれか。

        Note:
            部分一致判定で分類し、該当しない場合は `anomaly` として扱う。

        Variables:
            normalized: 小文字化した判定用文字列。
        """
        # 主要変数: normalized は条件分岐に使う小文字化済みevent_type。
        normalized = event_type.lower()
        if "temp" in normalized or "temperature" in normalized:
            return "temperature"
        if "vibration" in normalized or "bearing" in normalized:
            return "vibration"
        return "anomaly"

    def _to_event_id(self, event: dict[str, Any]) -> int:
        """イベント辞書からevent_idを安全に抽出する。

        Args:
            event: DBイベント辞書。

        Returns:
            int: 取得したevent_id。変換不能時は0。

        Note:
            `event["id"]` が数値へ変換できない場合のみ0を返す。

        Variables:
            raw_event_id: 元のイベントID値。
        """
        # 主要変数: raw_event_id は型変換前のID値。
        raw_event_id = event.get("id", 0)
        try:
            return int(raw_event_id)
        except (TypeError, ValueError):
            return 0

    def _build_tasks(self, event_kind: str) -> list[dict[str, Any]]:
        """イベント種別ごとの標準タスクを生成する。

        Args:
            event_kind: 正規化済みイベント種別。

        Returns:
            list[dict[str, Any]]: `Task` 変換前のタスク辞書列。

        Note:
            `temperature` / `vibration` / `anomaly` のみを想定し、未知値は `anomaly` 扱いにフォールバックする。

        Variables:
            tasks: 生成したタスク辞書リスト。
        """
        # 主要変数: tasks は最終的にTaskモデルへ変換されるタスク候補。
        if event_kind == "temperature":
            tasks = [
                {
                    "id": "temperature-01",
                    "title": "センサー値と配線状態を確認",
                    "description": "温度センサーの値妥当性と断線・接触不良の有無を点検する。",
                    "priority": 2,
                    "estimated_minutes": 20,
                    "safety_notes": ["設備停止手順を実施してから点検を開始する。"],
                },
                {
                    "id": "temperature-02",
                    "title": "閾値設定を確認",
                    "description": "監視閾値と運転条件の整合性を確認し、必要なら見直し候補を記録する。",
                    "priority": 3,
                    "estimated_minutes": 15,
                    "safety_notes": ["変更前に現行設定を必ずバックアップする。"],
                },
                {
                    "id": "temperature-03",
                    "title": "冷却または停止判断",
                    "description": "実測値と設備状態から冷却継続か一時停止かを判断し、責任者へ共有する。",
                    "priority": 1,
                    "estimated_minutes": 25,
                    "safety_notes": ["高温部へ接触しないよう保護具を着用する。"],
                },
                {
                    "id": "temperature-04",
                    "title": "対応結果を記録",
                    "description": "判断根拠と実施内容を保守記録へ残す。",
                    "priority": 4,
                    "estimated_minutes": 10,
                    "safety_notes": ["記録時に機密情報を含めない。"],
                },
            ]
            return tasks

        if event_kind == "vibration":
            tasks = [
                {
                    "id": "vibration-01",
                    "title": "ベアリングと固定具を確認",
                    "description": "異常振動源になりやすい箇所を目視と簡易計測で確認する。",
                    "priority": 1,
                    "estimated_minutes": 25,
                    "safety_notes": ["回転体へ接近する前に必ず停止を確認する。"],
                },
                {
                    "id": "vibration-02",
                    "title": "潤滑状態を点検",
                    "description": "潤滑剤の劣化や不足を点検し、必要なら補充計画を立てる。",
                    "priority": 2,
                    "estimated_minutes": 20,
                    "safety_notes": ["薬剤取扱手順と換気を遵守する。"],
                },
                {
                    "id": "vibration-03",
                    "title": "交換要否を判断",
                    "description": "摩耗度合いから部品交換の要否と停止時間を見積もる。",
                    "priority": 3,
                    "estimated_minutes": 30,
                    "safety_notes": ["交換判断時は保全責任者の承認を得る。"],
                },
                {
                    "id": "vibration-04",
                    "title": "対応内容を記録",
                    "description": "点検結果と次回監視ポイントを記録する。",
                    "priority": 4,
                    "estimated_minutes": 10,
                    "safety_notes": ["計測値は単位付きで記録する。"],
                },
            ]
            return tasks

        tasks = [
            {
                "id": "anomaly-01",
                "title": "現地状況を確認",
                "description": "安全確保後に現地で異常箇所と影響範囲を確認する。",
                "priority": 1,
                "estimated_minutes": 20,
                "safety_notes": ["二次災害防止のため立入範囲を制御する。"],
            },
            {
                "id": "anomaly-02",
                "title": "一次切り分けを実施",
                "description": "電源・ネットワーク・センサーの観点で初期切り分けを行う。",
                "priority": 2,
                "estimated_minutes": 25,
                "safety_notes": ["通電作業時は絶縁手袋を着用する。"],
            },
            {
                "id": "anomaly-03",
                "title": "安全確保手順を実行",
                "description": "必要な隔離・停止手順を実行して設備を安全状態へ移行する。",
                "priority": 1,
                "estimated_minutes": 15,
                "safety_notes": ["緊急停止後の再起動は指示があるまで行わない。"],
            },
            {
                "id": "anomaly-04",
                "title": "連絡と記録を実施",
                "description": "関係者へ連絡し、判断根拠と作業内容を記録する。",
                "priority": 3,
                "estimated_minutes": 10,
                "safety_notes": ["時刻と連絡先を漏れなく記録する。"],
            },
        ]
        return tasks

    def _repair_summary(self, summary: str) -> str:
        """issues対応時にsummaryの欠損を補正する。

        Args:
            summary: 現在のsummary文字列。

        Returns:
            str: 補正後summary。

        Note:
            summaryが空文字の場合のみ既定文を設定する。

        Variables:
            repaired_summary: 補正結果のsummary文字列。
        """
        # 主要変数: repaired_summary は不足情報を補完したsummary。
        repaired_summary = summary.strip()
        if not repaired_summary:
            repaired_summary = (
                "イベント概要が不足しているため、現地確認・安全確保・一次切り分けを優先して"
                "保守計画を作成する。"
            )
        return repaired_summary

    def _repair_tasks(
        self,
        tasks_payload: list[dict[str, Any]],
        issues: list[Issue],
    ) -> list[dict[str, Any]]:
        """Validator issuesをもとにタスク内容を補正する。

        Args:
            tasks_payload: 補正対象のタスク辞書列。
            issues: Validatorから渡された不備一覧。

        Returns:
            list[dict[str, Any]]: 補正済みタスク辞書列。

        Note:
            `TASKS_EMPTY` の指摘がある場合のみタスクを既定値で再生成し、その後全タスクを正規化する。

        Variables:
            has_tasks_empty: TASKS_EMPTYがissuesに含まれるかどうか。
            repaired_tasks: 補正処理中のタスクリスト。
            normalized_notes: 空文字を除去した安全注意事項。
        """
        # 主要変数: has_tasks_empty はタスク再生成の要否判定に使う。
        has_tasks_empty = any(issue.code == "TASKS_EMPTY" for issue in issues)
        if has_tasks_empty or not tasks_payload:
            tasks_payload = self._build_tasks("anomaly")

        # 主要変数: repaired_tasks は順次補正したタスクを格納する。
        repaired_tasks: list[dict[str, Any]] = []
        for index, task in enumerate(tasks_payload):
            repaired = dict(task)
            if not str(repaired.get("id", "")).strip():
                repaired["id"] = f"repaired-{index + 1:02d}"
            if not str(repaired.get("title", "")).strip():
                repaired["title"] = "確認タスク"
            if not str(repaired.get("description", "")).strip():
                repaired["description"] = "現地確認と記録を実施する。"

            priority = repaired.get("priority")
            if not isinstance(priority, int):
                priority = 3
            repaired["priority"] = max(1, min(5, priority))

            estimate = repaired.get("estimated_minutes")
            if not isinstance(estimate, int) or estimate <= 0:
                estimate = 15
            repaired["estimated_minutes"] = estimate

            raw_notes = repaired.get("safety_notes")
            if not isinstance(raw_notes, list):
                raw_notes = []
            # 主要変数: normalized_notes は空文字除去済み安全注意事項。
            normalized_notes = [
                str(note).strip() for note in raw_notes if str(note).strip()
            ]
            if not normalized_notes:
                normalized_notes = ["作業前に設備停止と周囲安全を確認する。"]
            repaired["safety_notes"] = normalized_notes
            repaired_tasks.append(repaired)

        return repaired_tasks

    def _construct_without_validation(
        self,
        plan_payload: dict[str, Any],
    ) -> MaintenancePlan:
        """Pydantic検証を意図的にスキップして計画モデルを構築する。

        Args:
            plan_payload: `MaintenancePlan` 相当の辞書データ。

        Returns:
            MaintenancePlan: `model_construct` で構築した未検証モデル。

        Note:
            リトライ動作検証のため、初回のみ不正値を含んだ計画を返すときに限定して利用する。

        Variables:
            unvalidated_tasks: 検証を通さずに生成したTaskモデル一覧。
        """
        # 主要変数: unvalidated_tasks は意図的に検証を飛ばして作るTask群。
        unvalidated_tasks = [
            Task.model_construct(**task_payload)
            for task_payload in plan_payload.get("tasks", [])
        ]
        return MaintenancePlan.model_construct(
            event_id=plan_payload.get("event_id", 0),
            summary=plan_payload.get("summary", ""),
            tasks=unvalidated_tasks,
            created_at=plan_payload.get("created_at", ""),
            version=plan_payload.get("version", "0.2"),
        )
