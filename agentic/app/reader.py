"""イベント情報から要約文を生成するReader Agentモジュール。

責務:
    events行の辞書データを読み取り、Plannerが扱いやすい短い要約へ変換する。
主な入出力:
    入力: `event_type`, `payload`, `ts`, `device_id` を含むイベント辞書
    出力: 100〜300文字程度の日本語サマリー文字列
重要な制約:
    payloadキー不足や型不一致があっても失敗させず、unknownで補完して継続する。
"""

from typing import Any


class ReaderAgent:
    """イベント辞書を要約テキストへ変換するクラス。

    責務:
        欠損耐性を持つ要約生成を提供し、後段Agentへ情報を受け渡す。
    主要メソッドの役割:
        `read_event` がイベント辞書を読み取り、固定フォーマットで要約を作る。
    前提・制約:
        入力辞書に欠損があっても処理を止めない。
    """

    def read_event(self, event: dict[str, Any]) -> str:
        """イベント辞書から要約文を生成する。

        Args:
            event: DBから取得したイベント辞書。

        Returns:
            str: 100〜300文字程度の要約文。

        Note:
            payloadが辞書でない場合やキー不足時は `unknown` を補完して要約を継続する。

        Variables:
            payload: payloadを辞書として正規化した値。
            payload_keys: payloadに存在するキー一覧文字列。
            summary: Plannerへ渡す最終要約文字列。
        """
        # 主要変数: payload は欠損に耐えるため辞書へ正規化したイベント詳細。
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        # 主要変数: payload_keys は観測項目を短く示すためのキー一覧。
        payload_keys = ",".join(sorted(payload.keys())) if payload else "unknown"

        # 主要変数: summary は以降のAgent処理で使う一次要約。
        summary = (
            f"{event.get('ts', 'unknown')} に device={event.get('device_id', 'unknown')} で "
            f"{event.get('event_type', 'unknown')} を検知した。payloadキーは {payload_keys}、"
            f"主要値は value={payload.get('value', 'unknown')} である。"
            "現地の安全確保を優先し、センサー状態・周辺設備・運転条件を順に確認する前提で"
            "保守計画を組み立てる。"
        )

        if len(summary) < 100:
            summary += " 追加情報不足時はunknownを維持しつつ、確認手順を保守側へ引き継ぐ。"
        if len(summary) > 300:
            summary = summary[:297] + "..."
        return summary
