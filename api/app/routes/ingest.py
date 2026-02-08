"""`/ingest` エンドポイントを提供するモジュール。

責務:
    入力イベントを検証し、PostgreSQLの `events` テーブルへ保存する。
主な入出力:
    入力: `EventIn` 形式のJSON
    出力: 成功時 `{"ok": true}`
重要な制約:
    DB書き込み失敗時は詳細をログへ残し、APIレスポンスは短く返す。
"""

import logging

from fastapi import APIRouter, HTTPException

from app.db import insert_event
from app.schemas import EventIn, IngestResponse
from app.settings import get_settings

# 主要変数: router はingest関連エンドポイントを束ねるルーター。
router = APIRouter()
# 主要変数: logger は障害時の簡潔なトレース出力に使用する。
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=IngestResponse)
def ingest(event: EventIn) -> IngestResponse:
    """受信イベントをDBへ保存する。

    Args:
        event: 保存対象のイベント情報。

    Returns:
        IngestResponse: 保存成功時に `ok=True` を返す。

    Raises:
        HTTPException: DB保存失敗時に500を返す。

    Note:
        DB保存が成功した場合のみ `ok=True` を返し、例外時は500へ変換して返す。

    Variables:
        settings: `DATABASE_URL` を保持する設定オブジェクト。
    """
    try:
        # 主要変数: settings は環境依存設定を1箇所で取得するために使用する。
        settings = get_settings()
        insert_event(settings.database_url, event)
        return IngestResponse(ok=True)
    except Exception as exc:
        logger.exception("ingest failed")
        raise HTTPException(status_code=500, detail="ingest failed") from exc
