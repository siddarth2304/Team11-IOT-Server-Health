# HiveMQ Cloud setup for the two-laptop demonstration

HiveMQ Cloud is the primary presentation broker. The project uses authenticated
MQTT over verified TLS on port 8883. The original Mosquitto mode remains as an
offline fallback.

## One-time HiveMQ Cloud setup

1. Sign in to the [HiveMQ Cloud console](https://console.hivemq.cloud/).
2. Create a Serverless cluster, or select an existing running cluster.
3. In **Access Management**, create an access credential with publish and
   subscribe permission for `team11/#`.
4. Copy the cluster hostname from its connection details. Do not include
   `mqtts://` in the hostname.
5. On both laptops, create the private configuration:

   ```bash
   cp .env.hivemq.example .env.hivemq
   nano .env.hivemq
   ```

6. Enter the same hostname, username and password on both laptops. The real
   `.env.hivemq` file is excluded from Git.

HiveMQ Cloud requires TLS. The Python clients verify the server certificate and
Node-RED uses its verified TLS configuration. See the official
[HiveMQ Cloud quick start](https://docs.hivemq.com/hivemq-cloud/quick-start-guide.html)
and [access-credential guide](https://docs.hivemq.com/hivemq-platform/connect/create-access-credentials.html).

## Start after every boot

Other laptop first:

```bash
./team11.sh hivemq-edge
```

Main laptop second:

```bash
TEAM11_DASHBOARD_PORT=8081 ./team11.sh hivemq-main
```

For a fast repeat that reuses saved models:

```bash
TEAM11_SKIP_TRAIN=1 TEAM11_DASHBOARD_PORT=8081 ./team11.sh hivemq-main
```

Open Node-RED at `http://127.0.0.1:1880` on the other laptop and the project
dashboard at `http://127.0.0.1:8081` on the main laptop. Unlike local Mosquitto,
HiveMQ Cloud does not require both laptops to share the same LAN; both only need
working internet access.

## Security boundary

- Never commit `.env.hivemq` or paste its password into screenshots/reports.
- Use a project-only credential, not a personal password.
- Rotate the credential after the evaluation if it was exposed.
- The classroom topics contain synthetic server telemetry, not patient or
  production data.
