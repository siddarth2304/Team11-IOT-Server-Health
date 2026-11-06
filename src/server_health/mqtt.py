"""Shared secure MQTT client configuration for local and cloud deployments."""

from __future__ import annotations

import os
import ssl
from dataclasses import dataclass


def _enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class MQTTSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    tls: bool

    @classmethod
    def from_environment(cls, host: str, port: int) -> "MQTTSettings":
        username = os.getenv("MQTT_USERNAME") or None
        password = os.getenv("MQTT_PASSWORD") or None
        if bool(username) != bool(password):
            raise ValueError("MQTT_USERNAME and MQTT_PASSWORD must be provided together")
        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            tls=_enabled(os.getenv("MQTT_TLS")),
        )


def create_client(client_id: str, host: str, port: int):
    """Create a Paho client using optional TLS and credentials from the environment."""
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit("Install MQTT support with: python3 -m pip install paho-mqtt") from exc

    settings = MQTTSettings.from_environment(host, port)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if settings.username:
        client.username_pw_set(settings.username, settings.password)
    if settings.tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        client.tls_insecure_set(False)
    return client


def connection_label(host: str, port: int) -> str:
    scheme = "mqtts" if _enabled(os.getenv("MQTT_TLS")) else "mqtt"
    return f"{scheme}://{host}:{port}"
