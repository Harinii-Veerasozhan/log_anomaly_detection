# Log Anomaly Detection

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

This starts Kafka, PostgreSQL, the synthetic log producer, the anomaly
detector, Grafana, and pgAdmin.

Open the forwarded ports in VS Code:

- `3000`: Grafana monitoring dashboard. Login with `admin` / `admin`.
- `5050`: pgAdmin database UI. Login with `admin@example.com` / `admin`.

In pgAdmin, select **Log Anomaly PostgreSQL**, open **Databases -> anomalies ->
Schemas -> public -> Tables -> anomalies**, and choose **View/Edit Data**.
The saved anomaly records are the same records used by Grafana.

Use Grafana for the project presentation and real-time monitoring. Use pgAdmin
when you need to inspect the PostgreSQL database directly. Streamlit remains a
possible custom Python UI, but it is not the primary live dashboard because the
current pipeline writes to PostgreSQL and Grafana is already connected to it.