"""PostgreSQLへの永続化処理を担当するモジュール。

責務:
    events/plans テーブルに対する保存・取得処理を提供する。
主な入出力:
    入力: `database_url`、イベントID、保守計画dict
    出力: イベント辞書、計画辞書、または書き込み副作用
重要な制約:
    API層から使うI/Oのみを扱い、Agentロジックは持たない。
"""

from typing import Any

import psycopg
from psycopg.rows import dict_row
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


def fetch_event_by_id(database_url: str, event_id: int) -> dict[str, Any] | None:
    """`events` テーブルから event_id に一致する1件を取得する。

    Args:
        database_url: PostgreSQL接続URL。
        event_id: 取得対象のイベントID。

    Returns:
        dict[str, Any] | None: 見つかった場合はイベント辞書、未検出ならNone。

    Raises:
        psycopg.Error: DB接続失敗・SQL実行失敗時に送出される。

    Note:
        event_id が存在する場合のみ辞書を返し、payloadが辞書でない場合は空辞書へ補正する。

    Variables:
        row: `events` から取得した1行。
        ts_text: レスポンス用にISO文字列へ変換した時刻。
        payload: 辞書化したpayload。
    """
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, device_id, ts, event_type, payload
                FROM events
                WHERE id = %s
                """,
                (event_id,),
            )
            # 主要変数: row はDBから取得した元レコード。
            row = cur.fetchone()

    if row is None:
        return None

    # 主要変数: ts_text はAgent入力で扱いやすいISO8601文字列。
    ts_value = row.get("ts")
    ts_text = ts_value.isoformat() if hasattr(ts_value, "isoformat") else str(ts_value)
    # 主要変数: payload は辞書型で統一したイベント詳細。
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    return {
        "id": int(row.get("id", 0)),
        "device_id": str(row.get("device_id", "unknown")),
        "ts": ts_text,
        "event_type": str(row.get("event_type", "unknown")),
        "payload": payload,
    }


def insert_plan(
    database_url: str,
    event_id: int,
    plan_json: dict[str, Any],
    status: str = "validated",
) -> dict[str, Any]:
    """`plans` テーブルへ保守計画を1件保存する。

    Args:
        database_url: PostgreSQL接続URL。
        event_id: 紐づくイベントID。
        plan_json: 保存対象の保守計画dict。
        status: 計画ステータス。

    Returns:
        dict[str, Any]: 保存後の計画レコード辞書。

    Raises:
        psycopg.Error: DB接続失敗・SQL実行失敗時に送出される。
        RuntimeError: INSERT後に行が返らない異常時。

    Note:
        保存が成功した場合のみ保存済みレコードを返す。

    Variables:
        row: INSERT ... RETURNING で取得した保存結果。
        created_at_text: レスポンス向けISO8601文字列。
    """
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO plans (event_id, status, plan_json)
                VALUES (%s, %s, %s)
                RETURNING id, event_id, status, plan_json, created_at
                """,
                (event_id, status, Jsonb(plan_json)),
            )
            # 主要変数: row は保存直後の計画レコード。
            row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to insert plan")

    created_at_value = row.get("created_at")
    # 主要変数: created_at_text は日時型をJSONへ載せるための文字列。
    created_at_text = (
        created_at_value.isoformat()
        if hasattr(created_at_value, "isoformat")
        else str(created_at_value)
    )
    return {
        "id": int(row.get("id", 0)),
        "event_id": int(row.get("event_id", 0)),
        "status": str(row.get("status", "validated")),
        "plan_json": row.get("plan_json"),
        "created_at": created_at_text,
    }


def fetch_latest_plan(database_url: str) -> dict[str, Any] | None:
    """`plans` テーブルの最新1件を取得する。

    Args:
        database_url: PostgreSQL接続URL。

    Returns:
        dict[str, Any] | None: 最新計画レコード。未登録ならNone。

    Raises:
        psycopg.Error: DB接続失敗・SQL実行失敗時に送出される。

    Note:
        レコードが存在する場合のみ辞書を返す。

    Variables:
        row: 取得した最新レコード。
    """
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, event_id, status, plan_json, created_at
                FROM plans
                ORDER BY id DESC
                LIMIT 1
                """
            )
            # 主要変数: row は最新計画レコード。
            row = cur.fetchone()

    if row is None:
        return None

    created_at_value = row.get("created_at")
    created_at_text = (
        created_at_value.isoformat()
        if hasattr(created_at_value, "isoformat")
        else str(created_at_value)
    )
    return {
        "id": int(row.get("id", 0)),
        "event_id": int(row.get("event_id", 0)),
        "status": str(row.get("status", "validated")),
        "plan_json": row.get("plan_json"),
        "created_at": created_at_text,
    }
