# Excel Insights Dashboard + FastAPI

A starter project that reads an Excel workbook, exposes it through a FastAPI REST API, and serves a responsive dashboard with KPI cards, charts, search, filters, and a data table.

## Project structure

```text
excel_api_dashboard/
├── main.py
├── requirements.txt
├── README.md
├── data/
│   └── data.xlsx
└── static/
    └── index.html
```

## 1. Run locally (macOS / VS Code)

Open this folder in VS Code, then use Terminal → New Terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
fastapi dev main.py
```

Open:
- Dashboard: http://127.0.0.1:8000/
- Swagger / interactive API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health
- Data API: http://127.0.0.1:8000/api/data
- Summary API: http://127.0.0.1:8000/api/summary

## 2. Connect your own Excel workbook

Replace `data/data.xlsx` with your workbook, or set `EXCEL_FILE` to its path.

Required column names in the first worksheet:
- `Date` (Excel date or parseable date text)
- `Region`
- `Product`
- `Revenue` (numeric)
- `Cost` (numeric)
- `Units` (numeric)

The API calculates `Profit = Revenue - Cost`. If your spreadsheet has different headers, update `EXPECTED_COLUMNS` and the fields used in `get_summary()` in `main.py`, plus chart/table fields in `static/index.html`.

After replacing the workbook, click **Refresh data** in the dashboard. The API reads the workbook when endpoints are called, so you don't need to restart the server for ordinary workbook updates.

## 3. API endpoints

### GET /api/health
Check whether the service is running and the workbook exists.

### GET /api/data
Returns records as JSON. Optional filters:
- `/api/data?region=West`
- `/api/data?product=Document%20AI`
- `/api/data?search=automation`

Example response:
```json
{
  "count": 1,
  "data": [
    {
      "Date": "2026-10-01",
      "Region": "West",
      "Product": "Automation Suite",
      "Revenue": 18500,
      "Cost": 7200,
      "Units": 5,
      "Profit": 11300
    }
  ]
}
```

### GET /api/summary
Returns totals, profit margin, revenue grouped by region and product, and monthly revenue for visualizations.

## 4. Call it from another project

### Python client
```python
import requests

API_BASE = "http://127.0.0.1:8000"

records = requests.get(f"{API_BASE}/api/data", timeout=15).json()
summary = requests.get(f"{API_BASE}/api/summary", timeout=15).json()

print(records["data"])
print("Revenue:", summary["total_revenue"])
```
Install client dependency in that project with `python -m pip install requests`.

### JavaScript / frontend client
```javascript
const response = await fetch("http://127.0.0.1:8000/api/summary");
if (!response.ok) throw new Error(`API failed: ${response.status}`);
const summary = await response.json();
console.log(summary.total_revenue);
```

### UiPath / other RPA client
Use an HTTP Request activity:
- Method: `GET`
- URL: `http://127.0.0.1:8000/api/data`
- Accept: `application/json`
- Parse the response JSON and use the `data` array.

For a remote third-party project, `127.0.0.1` points to that project's own machine, not your computer. Deploy the API to a server or use a secure tunnel for development, then replace the base URL with the reachable API URL.

## 5. CORS configuration

CORS matters when a browser frontend hosted on a different origin calls this API. Set `CORS_ORIGINS` to a comma-separated list of exact trusted origins before starting the server.

macOS example:
```bash
export CORS_ORIGINS="http://localhost:3000,https://your-app.example.com"
fastapi dev main.py
```

Do not use wildcard origins with credentials in production. This starter disables credentials and only permits the configured origins. CORS does not provide authentication or protect the API from non-browser clients.

## Production notes

- The sample workbook contains illustrative demo data. Replace it with your actual data before using the dashboard for business reporting.
- Add authentication/authorization before exposing sensitive data publicly.
- Use HTTPS, environment-based configuration, logging, and deployment hosting for production.
- Excel is suitable for a starter or low-volume read-only dashboard. For concurrent writes or larger datasets, consider a database.
- Chart.js is loaded from a CDN, so an internet connection is needed to load the charts.
