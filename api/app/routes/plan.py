"""保守計画生成APIエンドポイントを提供するモジュール。

責務:
    eventsから対象イベントを取得し、Orchestratorで計画生成してplansへ保存する。
主な入出力:
    入力: `event_id`（query parameter）
    出力: 保存済み `plan_json`（成功時）
重要な制約:
    Validator retryが上限超過した場合は422を返し、issuesを含める。
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from agentic.app.orchestrator import PlanValidationError, build_default_orchestrator
from app.db import fetch_event_by_id, fetch_latest_plan, insert_plan
from app.settings import get_settings

# 主要変数: router は計画生成関連エンドポイントを束ねる。
router = APIRouter()
# 主要変数: logger は障害時の最小ログ出力に使用する。
logger = logging.getLogger(__name__)


@router.post("/plan/generate")
def generate_plan(event_id: int = Query(..., ge=1)) -> dict:
    """指定イベントから保守計画を生成して保存する。

    Args:
        event_id: 計画生成対象のイベントID。

    Returns:
        dict: 保存された `plan_json`。

    Raises:
        HTTPException: event未存在時404、検証失敗時422、その他障害時500。

    Note:
        eventが存在する場合のみOrchestratorを実行し、retry失敗時はissues付きで422を返す。

    Variables:
        settings: DB接続設定。
        event: 取得したイベント辞書。
        orchestrator: v0.2標準Agent構成。
        plan_json: 生成された保守計画dict。
        saved_plan: DB保存後の計画レコード辞書。
    """
    try:
        # 主要変数: settings はDB接続URLを保持する設定。
        settings = get_settings()
        # 主要変数: event はevent_idに対応するイベント辞書。
        event = fetch_event_by_id(settings.database_url, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="event not found")

        # 主要変数: orchestrator はAgent実行順序とretryを統括する。
        orchestrator = build_default_orchestrator()
        # 主要変数: plan_json は保存対象の最終計画dict。
        plan_json = orchestrator.run(event)
        # 主要変数: saved_plan はDBへ保存した計画レコード。
        saved_plan = insert_plan(
            settings.database_url,
            event_id=event_id,
            plan_json=plan_json,
            status="validated",
        )
        return saved_plan["plan_json"]
    except PlanValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "plan validation failed",
                "retry_count": exc.retry_count,
                "issues": [issue.model_dump() for issue in exc.issues],
            },
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("plan generate failed event_id=%s", event_id)
        raise HTTPException(status_code=500, detail="plan generation failed") from exc


@router.get("/plans/latest")
def get_latest_plan() -> dict:
    """最新の計画JSONを1件返す。

    Returns:
        dict: 最新の `plan_json`。

    Raises:
        HTTPException: 計画未登録時404、取得失敗時500。

    Note:
        plansに1件以上存在する場合のみ `plan_json` を返す。

    Variables:
        settings: DB接続設定。
        latest_plan: 取得した最新計画レコード。
    """
    try:
        # 主要変数: settings はDB接続設定を保持する。
        settings = get_settings()
        # 主要変数: latest_plan はDBから取得した最新計画レコード。
        latest_plan = fetch_latest_plan(settings.database_url)
        if latest_plan is None:
            raise HTTPException(status_code=404, detail="plan not found")
        return latest_plan["plan_json"]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("fetch latest plan failed")
        raise HTTPException(status_code=500, detail="latest plan fetch failed") from exc
