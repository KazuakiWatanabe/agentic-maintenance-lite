"""Agent実行順序とretry制御を担うOrchestratorモジュール。

責務:
    Reader -> Planner -> Validator -> (Retry) -> Generator の制御フローを提供する。
主な入出力:
    入力: イベント辞書
    出力: 検証済み保守計画dict
重要な制約:
    Validator issuesが残る場合は最大2回まで再生成を行い、超過時は例外を送出する。
"""

from typing import Any

from agentic.app.generator import GeneratorAgent
from agentic.app.planner import PlannerAgent
from agentic.app.reader import ReaderAgent
from agentic.app.schemas import Issue, MaintenancePlan
from agentic.app.validator import ValidatorAgent


class PlanValidationError(Exception):
    """retry上限を超えても計画が妥当化できない場合の例外クラス。

    責務:
        最終issuesとretry回数を呼び出し元へ伝達する。
    主要メソッドの役割:
        `__init__` で失敗詳細をプロパティへ格納する。
    前提・制約:
        `issues` は空でないことを想定する。
    """

    def __init__(self, message: str, issues: list[Issue], retry_count: int):
        """例外情報を初期化する。

        Args:
            message: 例外メッセージ。
            issues: 最終的に残ったIssue一覧。
            retry_count: 実施した再試行回数。

        Returns:
            None

        Note:
            retry_countはPlanner再生成を行った回数のみを保持する。

        Variables:
            なし。
        """
        super().__init__(message)
        self.issues = issues
        self.retry_count = retry_count


class MaintenanceOrchestrator:
    """v0.2 Agenticフローを統合制御するクラス。

    責務:
        Agent間の実行順序、issuesに基づくretry、最終出力生成を統括する。
    主要メソッドの役割:
        `run` が1イベント分の処理全体を実行する。
    前提・制約:
        retry上限は既定で2回とし、成功時のみGeneratorを実行する。
    """

    def __init__(
        self,
        reader: ReaderAgent,
        planner: PlannerAgent,
        validator: ValidatorAgent,
        generator: GeneratorAgent,
        max_retries: int = 2,
    ):
        """Orchestratorを構成するAgent群を初期化する。

        Args:
            reader: 要約生成を担当するReader Agent。
            planner: 計画生成を担当するPlanner Agent。
            validator: 不備検証を担当するValidator Agent。
            generator: 最終整形を担当するGenerator Agent。
            max_retries: Validator不合格時の最大再試行回数。

        Returns:
            None

        Note:
            `max_retries` が0未満の場合は0として扱う。

        Variables:
            なし。
        """
        self._reader = reader
        self._planner = planner
        self._validator = validator
        self._generator = generator
        self._max_retries = max(0, max_retries)

    def run(self, event: dict[str, Any]) -> dict:
        """単一イベントから検証済み保守計画dictを生成する。

        Args:
            event: DBから取得したイベント辞書。

        Returns:
            dict: `plans.plan_json` へ保存可能な計画dict。

        Raises:
            PlanValidationError: retry上限まで再生成してもissuesが解消しない場合。

        Note:
            issuesは各retryごとに上書きし、累積しない。retryは最大2回まで実行する。

        Variables:
            summary: Readerが生成したイベント要約。
            plan: 現在試行中の保守計画モデル。
            issues: 直近のValidator結果。
            retry_count: 実施済みretry回数。
            validated_plan: 最終的にPydantic再検証を通した計画モデル。
        """
        # 主要変数: summary はPlannerへの入力となる一次要約。
        summary = self._reader.read_event(event)
        # 主要変数: plan はretry中に更新される現在の計画モデル。
        plan = self._planner.plan(event, summary, issues=None)
        # 主要変数: issues は直近検証結果で、各ループで上書きする。
        issues = self._validator.validate(plan)
        # 主要変数: retry_count はPlanner再実行回数を示す。
        retry_count = 0

        while issues and retry_count < self._max_retries:
            retry_count += 1
            plan = self._planner.plan(event, summary, issues=issues)
            issues = self._validator.validate(plan)

        if issues:
            raise PlanValidationError(
                message="plan validation failed after retries",
                issues=issues,
                retry_count=retry_count,
            )

        # 主要変数: validated_plan は最終的にPydantic検証を再度通した計画。
        validated_plan = MaintenancePlan.model_validate(plan.model_dump())
        return self._generator.generate(validated_plan)


def build_default_orchestrator() -> MaintenanceOrchestrator:
    """標準構成のOrchestratorを生成する。

    Returns:
        MaintenanceOrchestrator: Reader/Planner/Validator/Generatorを束ねたOrchestrator。

    Note:
        v0.2要件に合わせて `max_retries=2` 固定で生成する。

    Variables:
        orchestrator: 標準Agent構成のOrchestratorインスタンス。
    """
    # 主要変数: orchestrator はAPIから直接利用する標準実装。
    orchestrator = MaintenanceOrchestrator(
        reader=ReaderAgent(),
        planner=PlannerAgent(),
        validator=ValidatorAgent(),
        generator=GeneratorAgent(),
        max_retries=2,
    )
    return orchestrator
