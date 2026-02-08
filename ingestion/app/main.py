"""ingestionサービスの起動エントリポイント。

責務:
    環境変数から設定を読み込み、MQTT購読とAPI転送を開始する。
主な入出力:
    入力: 環境変数（MQTT_HOST, MQTT_PORT, MQTT_TOPIC, API_BASE_URL）
    出力: なし（常駐プロセスとして動作）
重要な制約:
    API転送失敗時のリトライは `ApiForwarder` 側で最大3回までに制限する。
"""

import logging
import os
from dataclasses import dataclass

from app.mqtt import ApiForwarder, MqttSubscriber


@dataclass(frozen=True)
class IngestionSettings:
    """ingestionサービスで利用する設定を保持するクラス。

    責務:
        MQTT接続先とAPI転送先の設定値を不変オブジェクトとして保持する。
    主要メソッドの役割:
        dataclassにより簡潔に設定値を集約する。
    前提・制約:
        `mqtt_port` は整数でなければならない。
    """

    mqtt_host: str
    mqtt_port: int
    mqtt_topic: str
    api_base_url: str


def load_settings() -> IngestionSettings:
    """環境変数からingestion設定を読み込む。

    Returns:
        IngestionSettings: 検証済み設定オブジェクト。

    Raises:
        RuntimeError: `MQTT_PORT` が整数へ変換できない場合。

    Note:
        環境変数が未設定の場合のみ既定値を利用し、`MQTT_PORT` は必ず整数へ変換する。

    Variables:
        mqtt_port_raw: 環境変数から取得したポート文字列。
        mqtt_port: 整数化したMQTTポート。
    """
    # 主要変数: mqtt_port_raw は整数変換前の元文字列。
    mqtt_port_raw = os.getenv("MQTT_PORT", "1883")
    try:
        # 主要変数: mqtt_port は実接続に使用する整数ポート。
        mqtt_port = int(mqtt_port_raw)
    except ValueError as exc:
        raise RuntimeError("MQTT_PORT must be integer") from exc

    return IngestionSettings(
        mqtt_host=os.getenv("MQTT_HOST", "mosquitto"),
        mqtt_port=mqtt_port,
        mqtt_topic=os.getenv("MQTT_TOPIC", "telemetry/#"),
        api_base_url=os.getenv("API_BASE_URL", "http://api:8000"),
    )


def main() -> None:
    """ingestionサービスを起動し、MQTT購読を開始する。

    Returns:
        None

    Note:
        `KeyboardInterrupt` 発生時のみ終了ログを出して終了する。

    Variables:
        settings: 環境変数由来の実行設定。
        forwarder: API転送処理を担うオブジェクト。
        subscriber: MQTT購読を担うオブジェクト。
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # 主要変数: settings はサービス間接続先をまとめた設定オブジェクト。
    settings = load_settings()
    # 主要変数: forwarder は受信イベントのHTTP転送とリトライを担当する。
    forwarder = ApiForwarder(settings.api_base_url, max_retries=3, timeout_sec=5)
    # 主要変数: subscriber はMQTT受信とforwarder呼び出しを仲介する。
    subscriber = MqttSubscriber(
        mqtt_host=settings.mqtt_host,
        mqtt_port=settings.mqtt_port,
        mqtt_topic=settings.mqtt_topic,
        forwarder=forwarder,
    )

    try:
        subscriber.run_forever()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("ingestion stopped by keyboard interrupt")


if __name__ == "__main__":
    main()
