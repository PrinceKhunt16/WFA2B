from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Metrics:
    mae: float | None
    rmse: float | None
    bias: float | None
    matched_intervals: int


def calculate_metrics(rows: list[dict[str, Any]]) -> Metrics:
    """Calculate error metrics from valid matched rows only.

    Error convention is forecast minus actual. Missing values are excluded,
    never converted to zero.
    """
    frame = pd.DataFrame(rows)
    if frame.empty or not {"forecast_generation", "actual_generation"}.issubset(frame):
        return Metrics(None, None, None, 0)

    numeric = frame[["forecast_generation", "actual_generation"]].apply(
        pd.to_numeric,
        errors="coerce",
    ).dropna()
    if numeric.empty:
        return Metrics(None, None, None, 0)

    errors = numeric["forecast_generation"] - numeric["actual_generation"]
    return Metrics(
        mae=float(np.mean(np.abs(errors))),
        rmse=float(np.sqrt(np.mean(np.square(errors)))),
        bias=float(np.mean(errors)),
        matched_intervals=int(len(errors)),
    )


def compare_records(
    forecasts: list[dict[str, Any]],
    actuals: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Match selected hourly forecasts with half-hourly actuals.

    FUELHH contains half-hourly average MW values. WINDFOR is hourly in the
    observed API response, so actuals are averaged by UTC delivery hour.
    """
    forecast_frame = _forecast_frame(forecasts)
    actual_frame = _actual_hourly_frame(actuals)
    if forecast_frame.empty:
        missing_rows = [
            {
                "delivery_time": row["delivery_time"],
                "forecast_generation": None,
                "actual_generation": row["actual_generation"],
                "error": None,
                "absolute_error": None,
                "squared_error": None,
                "forecast_publication_time": None,
                "cutoff_satisfied": False,
                "status": "missing_forecast",
                "reason": "no_forecast_before_cutoff",
                "units": "MW",
            }
            for row in actual_frame.to_dict(orient="records")
        ]
        return missing_rows, [{"reason": "no_eligible_forecasts"}]

    merged = forecast_frame.merge(actual_frame, on="delivery_time", how="outer", indicator=True)
    results: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []

    for row in merged.to_dict(orient="records"):
        status = "matched"
        reason = None
        if row.get("_merge") == "left_only":
            status, reason = "missing_actual", "no_actual_for_delivery_interval"
        elif row.get("_merge") == "right_only":
            status, reason = "missing_forecast", "no_forecast_before_cutoff"

        forecast = row.get("forecast_generation")
        actual = row.get("actual_generation")
        error = None if forecast is None or actual is None else forecast - actual
        result = {
            "delivery_time": row["delivery_time"],
            "forecast_generation": forecast,
            "actual_generation": actual,
            "error": error,
            "absolute_error": None if error is None else abs(error),
            "squared_error": None if error is None else error**2,
            "forecast_publication_time": row.get("forecast_publication_time"),
            "cutoff_satisfied": bool(row.get("cutoff_satisfied", False)),
            "status": status,
            "reason": reason,
            "units": "MW",
        }
        results.append(result)
        if reason:
            exclusions.append({"delivery_time": row["delivery_time"], "reason": reason})

    results.sort(key=lambda row: row["delivery_time"])
    return results, exclusions


def _forecast_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [
        {
            "delivery_time": _utc_timestamp(record["delivery_time"]),
            "forecast_generation": record["generation"],
            "forecast_publication_time": _utc_timestamp(record["publication_time"]),
            "cutoff_satisfied": True,
        }
        for record in records
    ]
    return pd.DataFrame(rows)


def _actual_hourly_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        try:
            timestamp = pd.Timestamp(record["startTime"])
            if timestamp.tzinfo is None:
                continue
            rows.append(
                {
                    "interval_time": timestamp.tz_convert("UTC"),
                    "actual_generation_value": float(record["generation"]),
                    "publish_time": _utc_timestamp(record.get("publishTime", timestamp)),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=["delivery_time", "actual_generation"])
    frame = frame.sort_values("publish_time").drop_duplicates(
        subset=["interval_time"],
        keep="last",
    )
    return (
        frame.assign(delivery_time=frame["interval_time"].dt.floor("h"))
        .groupby("delivery_time", as_index=False)["actual_generation_value"]
        .mean()
        .rename(columns={"actual_generation_value": "actual_generation"})
    )


def _utc_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")
