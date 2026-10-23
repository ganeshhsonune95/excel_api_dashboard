import os
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = Path(os.getenv("EXCEL_FILE", BASE_DIR / "data" / "data.xlsx"))
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Excel Analytics API",
    description="Serves Excel workbook data and summary metrics to dashboards and third-party applications.",
    version="1.0.0",
)

# Configure allowed browser origins with CORS_ORIGINS, comma-separated.
# Example: CORS_ORIGINS=http://localhost:3000,https://your-app.example.com
origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500")
allowed_origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

EXPECTED_COLUMNS = ["Date", "Region", "Product", "Revenue", "Cost", "Units"]

def load_dataframe() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Excel file not found at {DATA_FILE}. Put your workbook there or set EXCEL_FILE."
        )
    try:
        df = pd.read_excel(DATA_FILE)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read Excel file: {exc}")
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Excel file is missing required columns: {missing}. Expected columns: {EXPECTED_COLUMNS}"
        )
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Revenue", "Cost", "Units"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["Profit"] = df["Revenue"] - df["Cost"]
    df = df.dropna(subset=["Date"])
    return df

def clean_records(df: pd.DataFrame):
    out = df.copy()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    out = out.where(pd.notnull(out), None)
    return out.to_dict(orient="records")

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "Excel Analytics API",
        "excel_file": DATA_FILE.name,
        "excel_file_exists": DATA_FILE.exists(),
    }

@app.get("/api/data")
def get_data(
    region: Optional[str] = Query(default=None, description="Filter by exact region"),
    product: Optional[str] = Query(default=None, description="Filter by exact product"),
    search: Optional[str] = Query(default=None, description="Search region or product"),
):
    df = load_dataframe()
    if region:
        df = df[df["Region"].astype(str).str.casefold() == region.casefold()]
    if product:
        df = df[df["Product"].astype(str).str.casefold() == product.casefold()]
    if search:
        term = search.casefold()
        df = df[
            df["Region"].astype(str).str.casefold().str.contains(term, na=False)
            | df["Product"].astype(str).str.casefold().str.contains(term, na=False)
        ]
    df = df.sort_values("Date", ascending=False)
    return {"count": int(len(df)), "data": clean_records(df)}

@app.get("/api/summary")
def get_summary():
    df = load_dataframe()
    revenue = float(df["Revenue"].sum())
    cost = float(df["Cost"].sum())
    profit = float(df["Profit"].sum())
    region_revenue = (
        df.groupby("Region", dropna=False)["Revenue"].sum().sort_values(ascending=False)
        .rename_axis("region").reset_index(name="revenue").to_dict(orient="records")
    )
    product_revenue = (
        df.groupby("Product", dropna=False)["Revenue"].sum().sort_values(ascending=False)
        .rename_axis("product").reset_index(name="revenue").to_dict(orient="records")
    )
    monthly = df.assign(Month=df["Date"].dt.to_period("M").astype(str)).groupby("Month")["Revenue"].sum()
    monthly_revenue = [{"month": str(k), "revenue": float(v)} for k, v in monthly.items()]
    return {
        "total_records": int(len(df)),
        "total_revenue": revenue,
        "total_cost": cost,
        "total_profit": profit,
        "profit_margin_percent": round((profit / revenue * 100), 2) if revenue else 0,
        "total_units": int(df["Units"].sum()),
        "region_revenue": region_revenue,
        "product_revenue": product_revenue,
        "monthly_revenue": monthly_revenue,
        "last_updated": pd.Timestamp.now().isoformat(timespec="seconds"),
    }

# Serve the dashboard at http://127.0.0.1:8000/
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

from fastapi.responses import FileResponse

@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")
