"""PostgreSQLへの永続化処理を担当するモジュール。

責務:
    ingestイベントを `events` テーブルへINSERTする。
主な入出力:
    入力: `database_url` と `EventIn`
    出力: なし（DB書き込み副作用のみ）
重要な制約:
    v0.1では単純INSERTのみを提供し、複雑なトランザクション制御は行わない。
"""

import psycopg
from psycopg.types.json import Jsonb

from app.schemas import EventIn


def insert_event(database_url: str, event: EventIn) -> None:
    """`events` テーブルへイベントを1件保存する。

    Args:
        database_url: PostgreSQL接続URL。
        event: 保存対象イベント。

    Returns:
        None: 正常時は値を返さない。

    Raises:
        psycopg.Error: DB接続失敗・SQL実行失敗時に送出される。

    Note:
        DB書き込みが成功した場合のみ正常終了し、失敗時は例外を呼び出し元へ伝播する。

    Variables:
        payload_json: JSONB列へ保存するために変換したイベントpayload。
    """
    # 主要変数: payload_json はPythonのdictをJSONBとして安全に渡すためのラッパー。
    payload_json = Jsonb(event.payload)
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (device_id, ts, event_type, payload)
                VALUES (%s, %s, %s, %s)
                """,
                (event.device_id, event.ts, event.event_type, payload_json),
            )
