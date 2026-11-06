import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from server_health.mqtt import MQTTSettings, connection_label


class MQTTConfigurationTests(unittest.TestCase):
    def test_local_defaults_remain_unencrypted_and_anonymous(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = MQTTSettings.from_environment("127.0.0.1", 1883)
            self.assertFalse(settings.tls)
            self.assertIsNone(settings.username)
            self.assertEqual(connection_label(settings.host, settings.port), "mqtt://127.0.0.1:1883")

    def test_hivemq_cloud_uses_tls_and_credentials(self):
        environment = {
            "MQTT_TLS": "1",
            "MQTT_USERNAME": "team11-client",
            "MQTT_PASSWORD": "secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = MQTTSettings.from_environment("cluster.hivemq.cloud", 8883)
            self.assertTrue(settings.tls)
            self.assertEqual(settings.username, "team11-client")
            self.assertEqual(connection_label(settings.host, settings.port), "mqtts://cluster.hivemq.cloud:8883")

    def test_partial_credentials_are_rejected(self):
        with patch.dict(os.environ, {"MQTT_USERNAME": "incomplete"}, clear=True):
            with self.assertRaises(ValueError):
                MQTTSettings.from_environment("cluster.hivemq.cloud", 8883)


if __name__ == "__main__":
    unittest.main()
