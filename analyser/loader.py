"""Load and normalize JMeter JTL/CSV into an analysis-ready DataFrame."""

from __future__ import annotations

import re
import warnings
from typing import Any

import pandas as pd

_TX_LABEL_RE = re.compile(r"^T\d+_", re.IGNORECASE)


def _transaction_label_mask(labels: pd.Series) -> pd.Series:
    def ok_one(lab: Any) -> bool:
        s = str(lab) if lab is not None else ""
        if not _TX_LABEL_RE.match(s):
            return False
        if "__R" in s:
            return False
        if re.search(r"_R\d+_", s):
            return False
        if "_/app" in s or "_app/" in s:
            return False
        return True

    return labels.map(ok_one)


def _err_type_from_code(code: Any) -> str:
    s = str(code).strip()
    su = s.upper()
    if "NOHTTP" in su or "CONNECTION" in su:
        return "connection"
    if s in {"400", "401", "403", "404", "405", "410", "422"}:
        return "4xx"
    if s in {"500", "502", "503", "504"}:
        return "5xx"
    return "none"


class JMeterLoader:
    REQUIRED_COLS = [
        "timeStamp",
        "elapsed",
        "label",
        "responseCode",
        "success",
        "allThreads",
        "Latency",
        "Connect",
        "bytes",
        "sentBytes",
    ]

    LOAD_BINS = [0, 30, 60, 120, 180, 240, 300]
    LOAD_LABELS = ["1–30", "31–60", "61–120", "121–180", "181–240", "241–300"]

    def load(self, filepath: str, run_id: str) -> pd.DataFrame:
        df = pd.read_csv(filepath, low_memory=False)

        missing = [c for c in self.REQUIRED_COLS if c not in df.columns]
        if missing:
            warnings.warn(
                f"Missing required columns; filling defaults: {missing}",
                UserWarning,
                stacklevel=2,
            )
        if "timeStamp" not in df.columns:
            df["timeStamp"] = 0
        if "elapsed" not in df.columns:
            df["elapsed"] = 0
        if "label" not in df.columns:
            df["label"] = ""
        if "responseCode" not in df.columns:
            df["responseCode"] = "200"
        if "success" not in df.columns:
            df["success"] = True
        if "allThreads" not in df.columns:
            df["allThreads"] = 0
        if "Latency" not in df.columns:
            df["Latency"] = 0
        if "Connect" not in df.columns:
            df["Connect"] = 0
        if "bytes" not in df.columns:
            df["bytes"] = 0
        if "sentBytes" not in df.columns:
            df["sentBytes"] = 0

        df = df.copy()
        df["responseCode"] = df["responseCode"].astype(str)
        for col in ("elapsed", "allThreads", "Latency", "Connect", "bytes", "sentBytes"):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        ts = pd.to_datetime(df["timeStamp"], unit="ms", errors="coerce")
        if ts.isna().mean() > 0.5:
            ts = pd.to_datetime(df["timeStamp"], errors="coerce")
        df["ts"] = ts
        df["minute"] = df["ts"].dt.floor("1min")

        threads = df["allThreads"].clip(lower=0)
        df["load_band"] = pd.cut(
            threads,
            bins=self.LOAD_BINS,
            labels=self.LOAD_LABELS,
            include_lowest=True,
            right=True,
        )

        df["is_transaction"] = _transaction_label_mask(df["label"])
        df["err_type"] = df["responseCode"].map(_err_type_from_code)
        df["success"] = df["success"].map(
            lambda x: str(x).lower() in ("true", "1", "yes") if pd.notna(x) else False
        )

        df["run_id"] = str(run_id)
        df.attrs["run_id"] = str(run_id)
        df.attrs["source_path"] = filepath
        return df

    def from_dataframe(self, df: pd.DataFrame, run_id: str, source_path: str = "") -> pd.DataFrame:
        """
        Apply the same normalization/enrichment as load() to an in-memory DataFrame
        (e.g. built from JTLParserV2 records). Expects JMeter-style column names.
        """
        if df is None or len(df) == 0:
            out = pd.DataFrame()
            out.attrs["run_id"] = str(run_id)
            out.attrs["source_path"] = str(source_path)
            return out

        df = df.copy()
        missing = [c for c in self.REQUIRED_COLS if c not in df.columns]
        if missing:
            warnings.warn(
                f"Missing required columns; filling defaults: {missing}",
                UserWarning,
                stacklevel=2,
            )
        if "timeStamp" not in df.columns:
            df["timeStamp"] = 0
        if "elapsed" not in df.columns:
            df["elapsed"] = 0
        if "label" not in df.columns:
            df["label"] = ""
        if "responseCode" not in df.columns:
            df["responseCode"] = "200"
        if "success" not in df.columns:
            df["success"] = True
        if "allThreads" not in df.columns:
            df["allThreads"] = 0
        if "Latency" not in df.columns:
            df["Latency"] = 0
        if "Connect" not in df.columns:
            df["Connect"] = 0
        if "bytes" not in df.columns:
            df["bytes"] = 0
        if "sentBytes" not in df.columns:
            df["sentBytes"] = 0

        df["responseCode"] = df["responseCode"].astype(str)
        for col in ("elapsed", "allThreads", "Latency", "Connect", "bytes", "sentBytes"):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        df["timeStamp"] = pd.to_numeric(df["timeStamp"], errors="coerce").fillna(0).astype("int64")

        ts = pd.to_datetime(df["timeStamp"], unit="ms", errors="coerce")
        if ts.isna().mean() > 0.5:
            ts = pd.to_datetime(df["timeStamp"], errors="coerce")
        df["ts"] = ts
        df["minute"] = df["ts"].dt.floor("1min")

        threads = df["allThreads"].clip(lower=0)
        df["load_band"] = pd.cut(
            threads,
            bins=self.LOAD_BINS,
            labels=self.LOAD_LABELS,
            include_lowest=True,
            right=True,
        )

        df["is_transaction"] = _transaction_label_mask(df["label"])
        df["err_type"] = df["responseCode"].map(_err_type_from_code)
        df["success"] = df["success"].map(
            lambda x: str(x).lower() in ("true", "1", "yes") if pd.notna(x) else False
        )

        df["run_id"] = str(run_id)
        df.attrs["run_id"] = str(run_id)
        df.attrs["source_path"] = str(source_path)
        return df
