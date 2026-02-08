"""agentic v0.2で利用するPydanticスキーマを定義するモジュール。

責務:
    Reader/Planner/Validator/Generator/Orchestrator間で受け渡す型を固定化する。
主な入出力:
    入力: 保守計画に関する辞書データ
    出力: `Issue`, `Task`, `MaintenancePlan` の検証済みモデル
重要な制約:
    `MaintenancePlan.model_dump()` を `plans.plan_json` に保存する前提で、JSON化可能な値のみを保持する。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Issue(BaseModel):
    """バリデーション失敗内容を表現するクラス。

    責務:
        Validatorが検出した不備をコード・説明・パスで表現する。
    主要メソッドの役割:
        BaseModelの検証でIssue構造を決定論的に固定する。
    前提・制約:
        `code`, `message`, `path` は空文字列を許容しない。
    """

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)


class Task(BaseModel):
    """保守作業タスクを表現するクラス。

    責務:
        1件の作業手順を実行可能な最小要素として保持する。
    主要メソッドの役割:
        `validate_safety_notes` で安全注意事項の空文字混入を防ぐ。
    前提・制約:
        `priority` は1〜5、`estimated_minutes` は1以上、`safety_notes` は1件以上必須。
    """

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    priority: int = Field(..., ge=1, le=5)
    estimated_minutes: int = Field(..., ge=1)
    safety_notes: list[str] = Field(..., min_length=1)

    @field_validator("safety_notes")
    @classmethod
    def validate_safety_notes(cls, notes: list[str]) -> list[str]:
        """安全注意事項リストを検証し、空文字を排除する。

        Args:
            notes: タスクに紐づく安全注意事項リスト。

        Returns:
            list[str]: 先頭末尾空白を除去した安全注意事項リスト。

        Raises:
            ValueError: 空文字を含む場合、または有効な注意事項が1件も無い場合。

        Note:
            リスト件数は維持される前提で検証し、空文字が混在する場合は失敗させる。

        Variables:
            normalized_notes: 空白除去後の安全注意事項リスト。
        """
        # 主要変数: normalized_notes は空白除去後の値を保持する。
        normalized_notes = [note.strip() for note in notes if isinstance(note, str)]
        if len(normalized_notes) != len(notes):
            raise ValueError("safety_notes must be string list")
        if any(not note for note in normalized_notes):
            raise ValueError("safety_notes must not include blank text")
        if not normalized_notes:
            raise ValueError("safety_notes must include at least one item")
        return normalized_notes


class MaintenancePlan(BaseModel):
    """v0.2の保守計画全体を表現するクラス。

    責務:
        event_idに紐づく保守計画を1つのJSON構造として保持する。
    主要メソッドの役割:
        `validate_created_at` でISO8601文字列の妥当性を検証する。
    前提・制約:
        `version` は常に `"0.2"` とし、`tasks` は最低1件必須。
    """

    event_id: int
    summary: str = Field(..., min_length=1)
    tasks: list[Task] = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)
    version: Literal["0.2"] = "0.2"

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: str) -> str:
        """作成日時文字列がISO8601形式であることを検証する。

        Args:
            value: 検証対象の日時文字列。

        Returns:
            str: 検証済みの日時文字列。

        Raises:
            ValueError: ISO8601として解釈できない場合。

        Note:
            `Z` を含む文字列は `+00:00` に正規化して判定する。

        Variables:
            normalized_value: `datetime.fromisoformat` 用に正規化した文字列。
        """
        # 主要変数: normalized_value はZ表記をPython標準で扱える形式へ変換した値。
        normalized_value = value.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(normalized_value)
        except ValueError as exc:
            raise ValueError("created_at must be ISO8601") from exc
        return value
