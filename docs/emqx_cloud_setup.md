# EMQX Cloud Serverless setup

EMQX Cloud Serverless is the primary presentation broker. It is fully managed,
supports username/password authentication over verified TLS, and provides a
recurring free monthly quota. Keep the deployment spend limit at `0` so usage
cannot create a charge; EMQX stops the deployment if the free quota is exhausted.

## One-time cloud setup

1. Open the [EMQX Cloud console](https://cloud.emqx.com/) and create an account.
2. Create a **Serverless** deployment, not Dedicated Flex.
3. Leave **Monthly spend limit** at `0`.
4. Wait until the deployment status is **Running**.
5. In **Access Control → Authentication**, add a built-in database user:
   username `team11-client` and a strong project-only password.
6. In **Access Control → Authorization**, allow that user to publish and
   subscribe to `team11/#`.
7. From the deployment overview, copy the TLS endpoint hostname and port 8883.
8. On both laptops run:

   ```bash
   cp .env.mqtt-cloud.example .env.mqtt-cloud
   nano .env.mqtt-cloud
   ```

9. Enter the same endpoint, username and password on both computers. Do not add
   `mqtts://` to the hostname. The real file is ignored by Git.

Official references: [create a Serverless deployment](https://docs.emqx.com/en/cloud/latest/create/serverless.html),
[free quota and spend limit](https://docs.emqx.com/en/cloud/latest/faq/deploy.html),
and [plan limits](https://docs.emqx.com/en/cloud/latest/price/plans.html).

## Start after every boot

Other laptop first:

```bash
./team11.sh cloud-edge
```

Main laptop second:

```bash
TEAM11_DASHBOARD_PORT=8081 ./team11.sh cloud-main
```

Fast repeat without retraining:

```bash
TEAM11_SKIP_TRAIN=1 TEAM11_DASHBOARD_PORT=8081 ./team11.sh cloud-main
```

Repeat a controlled scenario from a second terminal on the main laptop:

```bash
./team11.sh cloud-replay --fault service_failure --limit 40 --delay 0.2
```

The normal cloud launcher uses a delay of 0.15 seconds, keeping the replay
publisher below the Serverless per-client limit of 10 publishes per second.

## Screens

- Other laptop: Node-RED at `http://127.0.0.1:1880`
- Main laptop: project dashboard at `http://127.0.0.1:8081`
- EMQX Cloud console: connection and traffic metrics, with credentials hidden

The telemetry is synthetic and contains no patient or production data.
