"""FastAPIアプリのエントリポイントを定義するモジュール。

責務:
    APIアプリケーションを生成し、v0.2で必要なルーターを登録する。
主な入出力:
    入力: なし（起動時にモジュールが読み込まれる）
    出力: FastAPIアプリインスタンス `app`
重要な制約:
    v0.2では `/health`, `/ingest`, `/plan/generate`, `/plans/latest` を公開する。
"""

from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.ingest import router as ingest_router
from app.routes.plan import router as plan_router


def create_app() -> FastAPI:
    """FastAPIアプリケーションを生成する。

    Returns:
        FastAPI: ルーター登録済みアプリインスタンス。

    Note:
        この関数は条件分岐を持たず、常に同じ初期化結果を返す。

    Variables:
        app: API設定とルーティング情報を保持する中核オブジェクト。
    """
    # 主要変数: app はエンドポイント定義を束ねるFastAPI本体。
    app = FastAPI(title="agentic-maintenance-lite-api", version="0.2.0")
    app.include_router(health_router)
    app.include_router(ingest_router)
    app.include_router(plan_router)
    return app


app = create_app()
