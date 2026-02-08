"""検証済み保守計画をJSON互換dictへ整形するGenerator Agentモジュール。

責務:
    `MaintenancePlan` をDB保存可能なdictへ変換する最終整形を担う。
主な入出力:
    入力: `MaintenancePlan`
    出力: JSONシリアライズ可能なdict
重要な制約:
    生データの改変は行わず、`model_dump` の結果をそのまま返す。
"""

from agentic.app.schemas import MaintenancePlan


class GeneratorAgent:
    """保守計画モデルをdictへ変換するクラス。

    責務:
        検証済みモデルを永続化可能な辞書へ変換する。
    主要メソッドの役割:
        `generate` が `model_dump` を呼び出して最終出力を返す。
    前提・制約:
        返却値は `plans.plan_json` へ直接保存可能であること。
    """

    def generate(self, plan: MaintenancePlan) -> dict:
        """検証済み保守計画をdictへ変換する。

        Args:
            plan: 検証済み保守計画。

        Returns:
            dict: JSONシリアライズ可能な保守計画辞書。

        Note:
            出力整形は `model_dump(mode="json")` のみを行い、追加加工は行わない。

        Variables:
            dumped_plan: `model_dump` で生成した辞書データ。
        """
        # 主要変数: dumped_plan はDB保存に使う最終辞書。
        dumped_plan = plan.model_dump(mode="json")
        return dumped_plan
