"""CSV analysis (stdlib-light; uses pandas/numpy when available)."""
from __future__ import annotations
from pathlib import Path
from .config import SAMPLES


def analyze_dataframe(df, max_cat: int = 12) -> dict:
    import numpy as np
    import pandas as pd

    n_rows, n_cols = df.shape
    columns, numeric_cols, categorical_cols = [], [], []
    for col in df.columns:
        s = df[col]
        info = {
            "name": str(col),
            "dtype": str(s.dtype),
            "missing": int(s.isna().sum()),
            "missing_pct": 0.0 if len(s) == 0 else round(float(s.isna().mean()) * 100, 1),
            "unique": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s):
            desc = s.describe()
            def _f(v):
                try:
                    f = float(v)
                    return None if (np.isnan(f) or np.isinf(f)) else round(f, 4)
                except Exception:
                    return None
            info.update({"kind": "numeric", "mean": _f(desc.get("mean")), "std": _f(desc.get("std")),
                         "min": _f(desc.get("min")), "median": _f(desc.get("50%")), "max": _f(desc.get("max"))})
            numeric_cols.append(str(col))
        else:
            vc = s.astype(str).value_counts(dropna=True).head(max_cat)
            info.update({"kind": "categorical", "top": [{"value": str(i), "count": int(v)} for i, v in vc.items()]})
            categorical_cols.append(str(col))
        columns.append(info)
    return {"rows": int(n_rows), "cols": int(n_cols), "columns": columns,
            "numeric_cols": numeric_cols, "categorical_cols": categorical_cols}


def analyze_csv_path(path: Path) -> dict:
    import pandas as pd
    try:
        df = pd.read_csv(path, on_bad_lines="warn")
    except Exception:
        df = pd.read_csv(path, engine="python", on_bad_lines="skip")
    result = analyze_dataframe(df)
    result["source"] = path.name
    return result


def analyze_csv_bytes(filename: str, data: bytes) -> dict:
    import io
    import pandas as pd
    try:
        df = pd.read_csv(io.BytesIO(data), on_bad_lines="warn")
    except Exception:
        df = pd.read_csv(io.BytesIO(data), engine="python", on_bad_lines="skip")
    result = analyze_dataframe(df)
    result["source"] = filename
    return result


def list_sample_csvs() -> list[str]:
    if not SAMPLES.exists():
        return []
    return [p.name for p in SAMPLES.glob("*.csv")]
