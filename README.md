# Log Anomaly Detection

## Models and algorithms

The project uses two detectors and combines their results:

- **Isolation Forest algorithm/model:** unsupervised detection of unusual metric combinations.
- **Rule-based detection algorithm:** explainable threshold checks for known violations.
- **Hybrid detection strategy:** an event is anomalous when either detector reports it; events reported by both receive high severity.
- **Synthetic anomaly injection:** controlled CPU, memory, login, latency, and error anomalies for repeatable testing.

The evaluation script reports precision, recall, F1-score, and a confusion matrix:

```bash
python evaluation/evaluate_detector.py
```

Run the automated detector tests with:

```bash
pytest
```

## Runtime architecture

```text
Synthetic logs -> Kafka -> Isolation Forest + rules -> PostgreSQL -> Grafana
```

PostgreSQL is the system's active anomaly store. Streamlit is an optional
Python dashboard and reads the same PostgreSQL data when run separately.

## Grafana dashboard

Start the services from the repository root:

```bash
docker compose up -d
```

In Codespaces, open the forwarded port `3000` from VS Code's **Ports** tab. The
dashboard is provisioned automatically at **Dashboards -> Log Anomaly
Detection -> IT Log Anomaly Monitoring**. The direct dashboard path is:

```text
/d/log-anomaly-monitoring/it-log-anomaly-monitoring
```

Grafana connects to PostgreSQL using the Docker service name `postgres` and the
`anomalies` database. The dashboard refreshes every 5 seconds and displays
anomaly totals, high-severity events, affected servers, metric trends, severity
counts, and recent detected anomalies.

Default development login: `admin` / `admin`.

Run the live detector separately to populate the dashboard:

```bash
python main.py
```

## One-command demo

The complete demo can run without separate Python terminals:

```bash
docker compose up -d --build
```

Do not run `python main.py` directly unless PostgreSQL and Kafka are already
running on the host. The Docker command above configures the detector to use
the container services (`postgres` and `kafka`). Running `python main.py`
without those services causes a PostgreSQL connection-refused error.

This starts Kafka, PostgreSQL, the synthetic log producer, the anomaly
detector, Grafana, and pgAdmin.

Open the forwarded ports in VS Code:

- `3000`: Grafana monitoring dashboard. Login with `admin` / `admin`.
- `5050`: pgAdmin database UI. Login with `admin@example.com` / `admin`.

In pgAdmin, select **Log Anomaly PostgreSQL**, open **Databases -> anomalies ->
Schemas -> public -> Tables -> anomalies**, and choose **View/Edit Data**.
The saved anomaly records are the same records used by Grafana.

Use Grafana for the project presentation and real-time monitoring. Use pgAdmin
when you need to inspect the PostgreSQL database directly. Streamlit is an
optional custom Python view of the same data.

## Alerts and user notification

The detector always prints an alert to its service log and stores the event in
PostgreSQL. Grafana displays the stored anomaly history and severity. Optional
Slack notifications are sent only when a real Slack incoming-webhook URL is
provided through `SLACK_WEBHOOK_URL`; the placeholder text
`your-slack-webhook-url` is not a valid URL and should not be used.