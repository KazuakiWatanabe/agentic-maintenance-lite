"""保守計画と入力イベントの不備を検出してIssue一覧を返すValidator Agentモジュール。

責務:
    SCHEMA/DATA/BUSINESS の各ルールで計画を検証し、Planner再試行向けIssueを返却する。
主な入出力:
    入力: `MaintenancePlan`, event辞書
    出力: `Issue` のリスト（不備なしなら空リスト）
重要な制約:
    例外で処理を止めず、常にissuesを返すことでOrchestratorのretry判定に利用できる形を維持する。
"""

from typing import Any

from agentic.app.schemas import Issue, MaintenancePlan, Task


class ValidatorAgent:
    """保守計画の妥当性を判定するクラス。

    責務:
        SCHEMAルールに加え、業務上の最小ルール（工数・必須タスク・安全）を検証する。
    主要メソッドの役割:
        `validate` が全体検証を実行し、必要なIssueを蓄積する。
    前提・制約:
        validateは `validate(plan, event)` で呼び出し、eventの必須フィールドも同時に検証する。
    """

    def validate(self, plan: MaintenancePlan, event: dict[str, Any]) -> list[Issue]:
        """保守計画とイベント入力を検証し、不備一覧を返す。

        Args:
            plan: 検証対象の保守計画。
            event: 計画生成の元となったイベント辞書。

        Returns:
            list[Issue]: 不備一覧。問題がない場合は空リスト。

        Note:
            `tasks` が空の場合は `SCHEMA_TASKS_EMPTY` を返し、タスク個別検証と業務ルール検証をスキップする。

        Variables:
            issues: 検出したIssueを蓄積するリスト。
            tasks: 計画に含まれるタスク一覧。
        """
        # 主要変数: issues は検証中に発見した不備を順次追加する。
        issues: list[Issue] = []
        self._validate_event_fields(event, issues)

        summary_value = getattr(plan, "summary", "")
        if not self._is_non_blank_text(summary_value):
            issues.append(
                Issue(
                    code="SCHEMA_MISSING_SUMMARY",
                    message="summary が空です。",
                    path="summary",
                )
            )

        # 主要変数: tasks は個別タスク検証対象の一覧。
        tasks = getattr(plan, "tasks", [])
        if not isinstance(tasks, list) or not tasks:
            issues.append(
                Issue(
                    code="SCHEMA_TASKS_EMPTY",
                    message="tasks が空です。",
                    path="tasks",
                )
            )
            return issues

        for index, task in enumerate(tasks):
            self._validate_task(index, task, issues)

        self._validate_business_rules(plan, event, issues)
        return issues

    def _validate_event_fields(
        self,
        event: dict[str, Any],
        issues: list[Issue],
    ) -> None:
        """イベント入力の必須フィールドを検証する。

        Args:
            event: 検証対象イベント辞書。
            issues: 追記先Issueリスト。

        Returns:
            None

        Note:
            欠落があるフィールドごとに `DATA_MISSING_EVENT_FIELDS` を追加し、まとめて返却する。

        Variables:
            required_fields: 必須フィールド名一覧。
            payload_value: `event.payload` の値。
        """
        # 主要変数: required_fields は必須項目の固定一覧。
        required_fields = ["device_id", "event_type", "ts", "payload"]
        for field_name in required_fields:
            if field_name not in event:
                issues.append(
                    Issue(
                        code="DATA_MISSING_EVENT_FIELDS",
                        message=f"{field_name} が不足しています。",
                        path=f"event.{field_name}",
                    )
                )

        if "device_id" in event and not self._is_non_blank_text(event.get("device_id")):
            issues.append(
                Issue(
                    code="DATA_MISSING_EVENT_FIELDS",
                    message="device_id が空です。",
                    path="event.device_id",
                )
            )
        if "event_type" in event and not self._is_non_blank_text(
            event.get("event_type")
        ):
            issues.append(
                Issue(
                    code="DATA_MISSING_EVENT_FIELDS",
                    message="event_type が空です。",
                    path="event.event_type",
                )
            )
        if "ts" in event and not self._is_non_blank_text(event.get("ts")):
            issues.append(
                Issue(
                    code="DATA_MISSING_EVENT_FIELDS",
                    message="ts が空です。",
                    path="event.ts",
                )
            )

        # 主要変数: payload_value はseverity判定などに使うevent詳細。
        payload_value = event.get("payload")
        if "payload" in event and not isinstance(payload_value, dict):
            issues.append(
                Issue(
                    code="DATA_MISSING_EVENT_FIELDS",
                    message="payload はオブジェクトである必要があります。",
                    path="event.payload",
                )
            )

    def _validate_task(self, index: int, task: Task | Any, issues: list[Issue]) -> None:
        """単一タスクを検証し、issuesへ追記する。

        Args:
            index: tasks内のインデックス。
            task: 検証対象タスク。
            issues: 追記先Issueリスト。

        Returns:
            None

        Note:
            title/descriptionのどちらかが空なら `SCHEMA_TASK_INVALID_TEXT` を返し、pathは該当フィールドを示す。

        Variables:
            title_value: タスクタイトル値。
            description_value: タスク説明値。
            priority_value: 優先度値。
            estimate_value: 見積時間値。
            notes_value: 安全注意事項値。
        """
        # 主要変数: title_value は空文字判定に使用するタスクタイトル。
        title_value = getattr(task, "title", "")
        if not self._is_non_blank_text(title_value):
            issues.append(
                Issue(
                    code="SCHEMA_TASK_INVALID_TEXT",
                    message="title が空です。",
                    path=f"tasks[{index}].title",
                )
            )

        # 主要変数: description_value は空文字判定に使用するタスク説明。
        description_value = getattr(task, "description", "")
        if not self._is_non_blank_text(description_value):
            issues.append(
                Issue(
                    code="SCHEMA_TASK_INVALID_TEXT",
                    message="description が空です。",
                    path=f"tasks[{index}].description",
                )
            )

        # 主要変数: priority_value は範囲判定を行う優先度。
        priority_value = getattr(task, "priority", None)
        if not isinstance(priority_value, int) or not 1 <= priority_value <= 5:
            issues.append(
                Issue(
                    code="SCHEMA_INVALID_PRIORITY",
                    message="priority は1〜5である必要があります。",
                    path=f"tasks[{index}].priority",
                )
            )

        # 主要変数: estimate_value は工数見積もりの妥当性判定値。
        estimate_value = getattr(task, "estimated_minutes", None)
        if not isinstance(estimate_value, int) or estimate_value <= 0:
            issues.append(
                Issue(
                    code="SCHEMA_INVALID_ESTIMATE",
                    message="estimated_minutes は1以上である必要があります。",
                    path=f"tasks[{index}].estimated_minutes",
                )
            )

        # 主要変数: notes_value は安全注意事項の一覧値。
        notes_value = getattr(task, "safety_notes", None)
        if not isinstance(notes_value, list) or not notes_value:
            issues.append(
                Issue(
                    code="SCHEMA_MISSING_SAFETY_NOTES",
                    message="safety_notes が空です。",
                    path=f"tasks[{index}].safety_notes",
                )
            )
            return

        has_blank_note = any(
            not isinstance(note, str) or not note.strip() for note in notes_value
        )
        if has_blank_note:
            issues.append(
                Issue(
                    code="SCHEMA_MISSING_SAFETY_NOTES",
                    message="safety_notes に空文字が含まれています。",
                    path=f"tasks[{index}].safety_notes",
                )
            )

    def _validate_business_rules(
        self,
        plan: MaintenancePlan,
        event: dict[str, Any],
        issues: list[Issue],
    ) -> None:
        """業務ルールを検証し、必要なIssueを追記する。

        Args:
            plan: 検証対象の保守計画。
            event: 入力イベント辞書。
            issues: 追記先Issueリスト。

        Returns:
            None

        Note:
            タスク件数・総工数・event_type必須タスク・severity安全タスク・記録連絡タスクの順で判定する。

        Variables:
            tasks: 保守タスク一覧。
            total_minutes: 見積工数合計。
            event_kind: event_typeを正規化した種別。
            severity: payloadから抽出した重大度。
        """
        # 主要変数: tasks は業務ルール判定対象のタスクリスト。
        tasks = plan.tasks
        if len(tasks) > 8:
            issues.append(
                Issue(
                    code="BUSINESS_TOO_MANY_TASKS",
                    message="tasks は8件以下である必要があります。",
                    path="tasks",
                )
            )

        # 主要変数: total_minutes はタスク全体の見積工数合計。
        total_minutes = sum(
            task.estimated_minutes
            for task in tasks
            if isinstance(task.estimated_minutes, int)
        )
        if total_minutes > 240:
            issues.append(
                Issue(
                    code="BUSINESS_MAX_TOTAL_MINUTES_EXCEEDED",
                    message="総工数が240分を超えています。",
                    path="tasks[*].estimated_minutes",
                )
            )

        # 主要変数: event_kind は必須タスク判定に使うイベント分類。
        event_kind = self._normalize_event_kind(event.get("event_type", "anomaly"))
        if not self._has_required_task(tasks, event_kind):
            issues.append(
                Issue(
                    code="BUSINESS_REQUIRED_TASK_MISSING",
                    message=f"{event_kind} 向け必須タスクが不足しています。",
                    path="tasks",
                )
            )

        # 主要変数: severity は停止/隔離要否判定に使う重大度。
        severity = self._extract_severity(event)
        if severity >= 4 and not self._has_stop_or_isolating_task(tasks):
            issues.append(
                Issue(
                    code="BUSINESS_SAFETY_STOP_REQUIRED",
                    message="severity>=4 のため停止/隔離タスクが必要です。",
                    path="event.payload.severity",
                )
            )

        if not self._has_contact_or_record_task(tasks):
            issues.append(
                Issue(
                    code="BUSINESS_CONTACT_REQUIRED",
                    message="記録または報告タスクが必要です。",
                    path="tasks",
                )
            )

    def _has_required_task(self, tasks: list[Task], event_kind: str) -> bool:
        """event_type別の必須タスクが存在するかを判定する。

        Args:
            tasks: 検証対象タスク一覧。
            event_kind: `temperature` / `vibration` / `anomaly`。

        Returns:
            bool: 必須タスクが見つかればTrue。

        Note:
            キーワード判定はtitle/description/safety_notesの部分一致で実施する。

        Variables:
            required_keywords: event種別ごとの必須キーワード群。
        """
        # 主要変数: required_keywords はイベント種別ごとの必須判定キーワード。
        required_keywords = {
            "temperature": ["sensor", "threshold", "センサー", "閾値"],
            "vibration": ["bearing", "fixture", "ベアリング", "固定具"],
            "anomaly": ["safety", "安全", "安全確認"],
        }
        keywords = required_keywords.get(event_kind, required_keywords["anomaly"])
        return any(self._task_contains_keywords(task, keywords) for task in tasks)

    def _has_stop_or_isolating_task(self, tasks: list[Task]) -> bool:
        """停止/隔離タスクの有無を判定する。

        Args:
            tasks: 検証対象タスク一覧。

        Returns:
            bool: 停止/隔離系キーワードを含むタスクがあればTrue。

        Note:
            severity高時の安全要件を満たすか判定するために利用する。

        Variables:
            keywords: 停止/隔離判定キーワード一覧。
        """
        # 主要変数: keywords は停止/隔離タスク判定で使用するキーワード。
        keywords = ["stop", "isolate", "停止", "隔離", "緊急停止"]
        return any(self._task_contains_keywords(task, keywords) for task in tasks)

    def _has_contact_or_record_task(self, tasks: list[Task]) -> bool:
        """記録/報告タスクの有無を判定する。

        Args:
            tasks: 検証対象タスク一覧。

        Returns:
            bool: 記録/報告系タスクがあればTrue。

        Note:
            すべての計画で最低1件必要な運用タスク判定に利用する。

        Variables:
            keywords: 記録/報告判定キーワード一覧。
        """
        # 主要変数: keywords は記録/報告タスク判定で使用するキーワード。
        keywords = ["record", "report", "記録", "報告", "連絡"]
        return any(self._task_contains_keywords(task, keywords) for task in tasks)

    def _task_contains_keywords(self, task: Task, keywords: list[str]) -> bool:
        """タスクが指定キーワードを含むか判定する。

        Args:
            task: 判定対象タスク。
            keywords: 部分一致で判定するキーワード一覧。

        Returns:
            bool: いずれかのキーワードを含む場合True。

        Note:
            判定対象はtitle/description/safety_notesを連結した文字列。

        Variables:
            target_text: 小文字化した比較対象文字列。
        """
        notes_text = " ".join(task.safety_notes)
        # 主要変数: target_text はキーワード一致判定に使う結合文字列。
        target_text = f"{task.title} {task.description} {notes_text}".lower()
        return any(keyword.lower() in target_text for keyword in keywords)

    def _normalize_event_kind(self, event_type: Any) -> str:
        """event_type文字列を検証用カテゴリへ正規化する。

        Args:
            event_type: 入力event_type値。

        Returns:
            str: `temperature` / `vibration` / `anomaly` のいずれか。

        Note:
            部分一致判定で分類し、該当しない場合は `anomaly` として扱う。

        Variables:
            normalized: 小文字化した判定用文字列。
        """
        # 主要変数: normalized は条件分岐に使う小文字化済みevent_type。
        normalized = str(event_type).lower()
        if "temp" in normalized or "temperature" in normalized:
            return "temperature"
        if "vibration" in normalized or "bearing" in normalized:
            return "vibration"
        return "anomaly"

    def _extract_severity(self, event: dict[str, Any]) -> int:
        """event.payload.severity を整数として抽出する。

        Args:
            event: 入力イベント辞書。

        Returns:
            int: severity値。未設定・不正値は0。

        Note:
            severityが数値へ変換可能な場合のみ値を返す。

        Variables:
            payload: eventから取得したpayload辞書。
            raw_severity: 変換前のseverity値。
        """
        # 主要変数: payload はseverity取得元のイベント詳細。
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        # 主要変数: raw_severity は型変換前のseverity。
        raw_severity = payload.get("severity", 0)
        try:
            return int(raw_severity)
        except (TypeError, ValueError):
            return 0

    def _is_non_blank_text(self, value: Any) -> bool:
        """文字列が空白以外を含むか判定する。

        Args:
            value: 判定対象の値。

        Returns:
            bool: 空白以外の文字を含む文字列ならTrue。

        Note:
            文字列型でない値は常にFalseとして扱う。

        Variables:
            なし。
        """
        return isinstance(value, str) and bool(value.strip())
