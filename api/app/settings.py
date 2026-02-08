"""API設定を環境変数から読み込むモジュール。

責務:
    実行時に必要な設定値を検証し、アプリから再利用可能な形で提供する。
主な入出力:
    入力: 環境変数 `DATABASE_URL`
    出力: `Settings` オブジェクト
重要な制約:
    `DATABASE_URL` 未設定時は明示的に失敗させ、暗黙の既定値を使わない。
"""

import os
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """API全体で共有する設定値を保持するクラス。

    責務:
        接続先データベースURLを型付きで保持する。
    主要メソッドの役割:
        BaseModelのバリデーションで値の妥当性を保証する。
    前提・制約:
        `database_url` は空文字列を許容しない。
    """

    database_url: str = Field(..., min_length=1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """環境変数から設定を読み込み、検証済み設定を返す。

    Returns:
        Settings: 検証済み設定。

    Raises:
        RuntimeError: `DATABASE_URL` が未設定の場合。

    Note:
        `DATABASE_URL` が存在する場合のみ設定を返し、同一プロセス内で結果をキャッシュする。

    Variables:
        database_url: PostgreSQL接続に利用する接続URL。
    """
    # 主要変数: database_url はAPIが利用するPostgreSQL接続先。
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return Settings(database_url=database_url)
