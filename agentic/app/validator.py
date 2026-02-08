"""保守計画の不備を検出してIssue一覧を返すValidator Agentモジュール。

責務:
    Plannerが生成した計画をルール検証し、修正に必要なIssueを返却する。
主な入出力:
    入力: `MaintenancePlan`
    出力: `Issue` のリスト（不備なしなら空リスト）
重要な制約:
    例外で処理を止めず、常にissuesを返すことでOrchestratorのretry判定に利用できる形を維持する。
"""

from typing import Any

from agentic.app.schemas import Issue, MaintenancePlan, Task


class ValidatorAgent:
    """保守計画の妥当性を判定するクラス。

    責務:
        必須項目、範囲制約、安全注意事項の妥当性を検証する。
    主要メソッドの役割:
        `validate` が全体検証を実行し、必要なIssueを蓄積する。
    前提・制約:
        v0.2では少なくとも6種類のIssueコードを返却可能であること。
    """

    def validate(self, plan: MaintenancePlan) -> list[Issue]:
        """保守計画を検証し、不備一覧を返す。

        Args:
            plan: 検証対象の保守計画。

        Returns:
            list[Issue]: 不備一覧。問題がない場合は空リスト。

        Note:
            `tasks` が空の場合は `TASKS_EMPTY` を返し、タスク個別検証はスキップする。

        Variables:
            issues: 検出したIssueを蓄積するリスト。
            tasks: 計画に含まれるタスク一覧。
        """
        # 主要変数: issues は検証中に発見した不備を順次追加する。
        issues: list[Issue] = []

        summary_value = getattr(plan, "summary", "")
        if not self._is_non_blank_text(summary_value):
            issues.append(
                Issue(
                    code="MISSING_SUMMARY",
                    message="summary が空です。",
                    path="summary",
                )
            )

        # 主要変数: tasks は個別タスク検証対象の一覧。
        tasks = getattr(plan, "tasks", [])
        if not isinstance(tasks, list) or not tasks:
            issues.append(
                Issue(
                    code="TASKS_EMPTY",
                    message="tasks が空です。",
                    path="tasks",
                )
            )
            return issues

        for index, task in enumerate(tasks):
            self._validate_task(index, task, issues)
        return issues

    def _validate_task(self, index: int, task: Task | Any, issues: list[Issue]) -> None:
        """単一タスクを検証し、issuesへ追記する。

        Args:
            index: tasks内のインデックス。
            task: 検証対象タスク。
            issues: 追記先Issueリスト。

        Returns:
            None

        Note:
            title/descriptionのどちらかが空なら `TASK_INVALID_TEXT` を返し、pathは該当フィールドを示す。

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
                    code="TASK_INVALID_TEXT",
                    message="title が空です。",
                    path=f"tasks[{index}].title",
                )
            )

        # 主要変数: description_value は空文字判定に使用するタスク説明。
        description_value = getattr(task, "description", "")
        if not self._is_non_blank_text(description_value):
            issues.append(
                Issue(
                    code="TASK_INVALID_TEXT",
                    message="description が空です。",
                    path=f"tasks[{index}].description",
                )
            )

        # 主要変数: priority_value は範囲判定を行う優先度。
        priority_value = getattr(task, "priority", None)
        if not isinstance(priority_value, int) or not 1 <= priority_value <= 5:
            issues.append(
                Issue(
                    code="INVALID_PRIORITY",
                    message="priority は1〜5である必要があります。",
                    path=f"tasks[{index}].priority",
                )
            )

        # 主要変数: estimate_value は工数見積もりの妥当性判定値。
        estimate_value = getattr(task, "estimated_minutes", None)
        if not isinstance(estimate_value, int) or estimate_value <= 0:
            issues.append(
                Issue(
                    code="INVALID_ESTIMATE",
                    message="estimated_minutes は1以上である必要があります。",
                    path=f"tasks[{index}].estimated_minutes",
                )
            )

        # 主要変数: notes_value は安全注意事項の一覧値。
        notes_value = getattr(task, "safety_notes", None)
        if not isinstance(notes_value, list) or not notes_value:
            issues.append(
                Issue(
                    code="MISSING_SAFETY_NOTES",
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
                    code="MISSING_SAFETY_NOTES",
                    message="safety_notes に空文字が含まれています。",
                    path=f"tasks[{index}].safety_notes",
                )
            )

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
