"""`/health` エンドポイントを提供するモジュール。

責務:
    APIプロセスの稼働状態を返す最小ヘルスチェックを提供する。
主な入出力:
    入力: なし
    出力: `{"status": "ok"}`
重要な制約:
    DB接続など重い処理は行わず、軽量に200を返す。
"""

from fastapi import APIRouter

from app.schemas import HealthResponse

# 主要変数: router はヘルスチェック系エンドポイントを束ねるルーター。
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """APIの稼働状態を返す。

    Returns:
        HealthResponse: 固定値 `status="ok"` を持つレスポンス。

    Note:
        条件分岐は持たず、常に同じ結果を返す。

    Variables:
        なし。
    """
    return HealthResponse(status="ok")
