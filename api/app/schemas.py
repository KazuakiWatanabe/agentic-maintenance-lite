"""FastAPI入出力スキーマを定義するモジュール。

責務:
    `/health` と `/ingest` で利用するリクエスト/レスポンス型を定義する。
主な入出力:
    入力: APIリクエストJSON
    出力: 検証済みPythonオブジェクトおよびレスポンスJSON
重要な制約:
    Pydanticで型検証し、曖昧な入力を受け入れない。
"""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    """`/ingest` に渡されるイベント入力を表すクラス。

    責務:
        device_id, event_type, ts, payload を型検証付きで保持する。
    主要メソッドの役割:
        BaseModelのバリデーションで入力の構造を保証する。
    前提・制約:
        `device_id` と `event_type` は空文字不可。
    """

    device_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    ts: datetime
    payload: Dict[str, Any]


class IngestResponse(BaseModel):
    """`/ingest` の成功レスポンスを表すクラス。

    責務:
        イベント受理結果を最小JSONで返す。
    主要メソッドの役割:
        BaseModelでレスポンス構造を固定化する。
    前提・制約:
        v0.1では `ok` のみを返す。
    """

    ok: bool = True


class HealthResponse(BaseModel):
    """`/health` のレスポンスを表すクラス。

    責務:
        ヘルスチェック状態を短い文字列で返す。
    主要メソッドの役割:
        BaseModelでレスポンス仕様を固定する。
    前提・制約:
        v0.1では `status` を `ok` で返す。
    """

    status: str = "ok"
