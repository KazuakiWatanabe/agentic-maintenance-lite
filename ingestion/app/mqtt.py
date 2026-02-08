"""MQTT購読とAPI転送処理を提供するモジュール。

責務:
    MQTTメッセージを受信し、JSONを `/ingest` へ転送する。
主な入出力:
    入力: MQTTトピック上のJSON文字列
    出力: APIへのHTTP POST実行結果（成功/失敗）
重要な制約:
    API失敗時は最大3回までリトライし、それ以上は失敗として扱う。
"""

import json
import logging
import time
from typing import Any, Dict

import paho.mqtt.client as mqtt
import requests

# 主要変数: logger は購読失敗や転送失敗の要約ログを出力する。
logger = logging.getLogger(__name__)


class ApiForwarder:
    """受信イベントをAPIへ転送するクラス。

    責務:
        MQTTから受け取ったイベント辞書を `/ingest` へPOSTする。
    主要メソッドの役割:
        `forward` がリトライ制御付きでHTTP送信を行う。
    前提・制約:
        失敗時のリトライは `max_retries` 回まで。
    """

    def __init__(self, api_base_url: str, max_retries: int = 3, timeout_sec: int = 5):
        """転送先とリトライ設定を初期化する。

        Args:
            api_base_url: APIベースURL（例: http://api:8000）。
            max_retries: API失敗時の最大試行回数。
            timeout_sec: 各リクエストのタイムアウト秒。

        Returns:
            None

        Note:
            `api_base_url` の末尾 `/` は正規化してからエンドポイントを生成する。

        Variables:
            normalized_base_url: 末尾スラッシュを除去したベースURL。
        """
        # 主要変数: normalized_base_url はURL連結時の二重スラッシュ防止に使う。
        normalized_base_url = api_base_url.rstrip("/")
        self._endpoint = f"{normalized_base_url}/ingest"
        self._max_retries = max_retries
        self._timeout_sec = timeout_sec

    def forward(self, event: Dict[str, Any]) -> bool:
        """イベントをAPIへ送信する。

        Args:
            event: `/ingest` へ送信するイベント辞書。

        Returns:
            bool: 送信成功ならTrue、最大回数まで失敗したらFalse。

        Note:
            HTTPエラーまたは通信例外が発生した場合のみリトライし、最大試行回数で打ち切る。

        Variables:
            attempt: 現在の試行回数。
            response: APIからのHTTPレスポンス。
        """
        for attempt in range(1, self._max_retries + 1):
            try:
                # 主要変数: response はHTTPステータスを判定するための応答オブジェクト。
                response = requests.post(
                    self._endpoint,
                    json=event,
                    timeout=self._timeout_sec,
                )
                if response.ok:
                    return True
                logger.warning(
                    "ingest request failed status=%s attempt=%s",
                    response.status_code,
                    attempt,
                )
            except requests.RequestException as exc:
                logger.warning(
                    "ingest request exception attempt=%s error=%s", attempt, exc
                )

            if attempt < self._max_retries:
                time.sleep(float(attempt))

        return False


class MqttSubscriber:
    """MQTT受信とイベント転送の制御を行うクラス。

    責務:
        MQTTブローカーへ接続し、対象トピックのメッセージを受け取ってAPI転送する。
    主要メソッドの役割:
        `run_forever` が接続開始、`_on_message` が受信処理を担当する。
    前提・制約:
        受信payloadはJSONオブジェクトであることを前提とし、違反時は破棄する。
    """

    def __init__(
        self,
        mqtt_host: str,
        mqtt_port: int,
        mqtt_topic: str,
        forwarder: ApiForwarder,
    ):
        """購読設定とコールバックを初期化する。

        Args:
            mqtt_host: MQTTブローカーのホスト名。
            mqtt_port: MQTTブローカーのポート番号。
            mqtt_topic: 購読対象トピック。
            forwarder: API転送処理オブジェクト。

        Returns:
            None

        Note:
            MQTT接続後の購読は `_on_connect` で実行するため、ここではコールバック登録のみ行う。

        Variables:
            client: paho-mqttのクライアント本体。
        """
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._mqtt_topic = mqtt_topic
        self._forwarder = forwarder

        # 主要変数: client はMQTT接続とコールバック管理を担う。
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        self._client = client

    def run_forever(self) -> None:
        """MQTT購読を開始して無限ループで待機する。

        Returns:
            None

        Raises:
            OSError: 接続失敗時に送出される場合がある。

        Note:
            接続成功後のみ `loop_forever` を開始する。

        Variables:
            なし。
        """
        self._client.connect(self._mqtt_host, self._mqtt_port, keepalive=60)
        self._client.loop_forever()

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        """MQTT接続完了時に購読を開始する。

        Args:
            client: paho-mqttクライアント。
            userdata: ユーザーデータ（未使用）。
            flags: 接続フラグ（未使用）。
            reason_code: 接続結果コード。
            properties: MQTT v5プロパティ（未使用）。

        Returns:
            None

        Note:
            reason_codeが成功コード（0）の場合のみ購読を開始し、失敗時はログ出力のみ行う。

        Variables:
            reason_value: `ReasonCode` または数値を整数へ正規化した接続結果コード。
        """
        # 主要変数: reason_value は型差分を吸収して成功判定に使う整数コード。
        reason_value = (
            int(reason_code.value)
            if hasattr(reason_code, "value")
            else int(reason_code)
        )
        if reason_value == 0:
            client.subscribe(self._mqtt_topic)
            logger.info("subscribed topic=%s", self._mqtt_topic)
            return
        logger.error("mqtt connect failed reason_code=%s", reason_value)

    def _on_message(self, client, userdata, message) -> None:
        """受信メッセージをJSONとして解釈し、APIへ転送する。

        Args:
            client: paho-mqttクライアント（未使用）。
            userdata: ユーザーデータ（未使用）。
            message: 受信メッセージ。

        Returns:
            None

        Note:
            JSONデコード失敗または辞書でないpayloadは破棄し、転送失敗時はエラーログを残す。

        Variables:
            decoded_payload: UTF-8デコードした文字列payload。
            parsed_payload: JSON解析後のpayload。
            forwarded: API転送の成否。
        """
        try:
            # 主要変数: decoded_payload はJSONパース前の生文字列。
            decoded_payload = message.payload.decode("utf-8")
            # 主要変数: parsed_payload は転送対象として扱うJSONオブジェクト。
            parsed_payload = json.loads(decoded_payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("invalid mqtt payload topic=%s error=%s", message.topic, exc)
            return

        if not isinstance(parsed_payload, dict):
            logger.warning("mqtt payload is not object topic=%s", message.topic)
            return

        # 主要変数: forwarded はAPI転送の最終成否。
        forwarded = self._forwarder.forward(parsed_payload)
        if not forwarded:
            logger.error("forward failed topic=%s", message.topic)
