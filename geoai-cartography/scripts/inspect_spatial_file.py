#!/usr/bin/env python3
"""Inspect local vector or raster geospatial files."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


VECTOR_EXTENSIONS = {".shp", ".gpkg", ".geojson", ".json"}
RASTER_EXTENSIONS = {".tif", ".tiff"}
TABLE_EXTENSIONS = {".csv", ".tsv", ".cst", ".txt", ".xls", ".xlsx"}


def require(module_name: str, install_name: str | None = None):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        package = install_name or module_name
        raise SystemExit(
            f"Missing dependency '{module_name}'. Install with: pip install {package}"
        ) from exc


def inspect_vector(path: Path) -> dict:
    gpd = require("geopandas")
    gdf = gpd.read_file(path)
    info = {
        "type": "vector",
        "path": str(path),
        "driver_hint": path.suffix.lower(),
        "feature_count": int(len(gdf)),
        "crs": str(gdf.crs) if gdf.crs else None,
        "bounds": [float(v) for v in gdf.total_bounds],
        "geometry_types": sorted(str(v) for v in gdf.geometry.geom_type.dropna().unique()),
        "fields": {},
    }
    for column in gdf.columns:
        if column == gdf.geometry.name:
            continue
        series = gdf[column]
        field = {
            "dtype": str(series.dtype),
            "non_null": int(series.notna().sum()),
            "unique_count": int(series.nunique(dropna=True)),
        }
        if series.nunique(dropna=True) <= 20:
            field["sample_values"] = [str(v) for v in series.dropna().unique()[:20]]
        if hasattr(series, "min") and str(series.dtype) != "geometry":
            try:
                if series.dtype.kind in "biufc":
                    field["min"] = float(series.min())
                    field["max"] = float(series.max())
            except Exception:
                pass
        info["fields"][column] = field
    return info


def inspect_raster(path: Path) -> dict:
    rasterio = require("rasterio")
    np = require("numpy")
    with rasterio.open(path) as src:
        sample = src.read(1, masked=True)
        compressed = sample.compressed()
        unique_values = []
        if compressed.size and compressed.size <= 2_000_000:
            values = np.unique(compressed)
            if values.size <= 30:
                unique_values = [float(v) if np.issubdtype(values.dtype, np.number) else str(v) for v in values]
        info = {
            "type": "raster",
            "path": str(path),
            "driver": src.driver,
            "width": int(src.width),
            "height": int(src.height),
            "count": int(src.count),
            "dtype": str(src.dtypes[0]),
            "crs": str(src.crs) if src.crs else None,
            "bounds": [float(src.bounds.left), float(src.bounds.bottom), float(src.bounds.right), float(src.bounds.top)],
            "resolution": [float(src.res[0]), float(src.res[1])],
            "nodata": src.nodata,
            "band1_min": float(compressed.min()) if compressed.size else None,
            "band1_max": float(compressed.max()) if compressed.size else None,
            "band1_unique_values_if_small": unique_values,
        }
    return info


def inspect_table(path: Path) -> dict:
    pd = require("pandas")
    suffix = path.suffix.lower()
    if suffix in {".xls", ".xlsx"}:
        df = pd.read_excel(path, nrows=100)
    elif suffix == ".tsv":
        df = pd.read_csv(path, sep="\t", nrows=100)
    elif suffix == ".cst":
        df = pd.read_csv(path, sep=None, engine="python", nrows=100)
    else:
        df = pd.read_csv(path, nrows=100)
    info = {
        "type": "table",
        "path": str(path),
        "driver_hint": suffix,
        "sample_row_count": int(len(df)),
        "columns": [str(column) for column in df.columns],
        "fields": {},
    }
    for column in df.columns:
        series = df[column]
        field = {
            "dtype": str(series.dtype),
            "sample_non_null": int(series.notna().sum()),
            "sample_unique_count": int(series.nunique(dropna=True)),
        }
        if series.nunique(dropna=True) <= 20:
            field["sample_values"] = [str(v) for v in series.dropna().unique()[:20]]
        info["fields"][str(column)] = field
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a local geospatial file.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    path = args.input.expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Input does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix in VECTOR_EXTENSIONS:
        info = inspect_vector(path)
    elif suffix in RASTER_EXTENSIONS:
        info = inspect_raster(path)
    elif suffix in TABLE_EXTENSIONS:
        info = inspect_table(path)
    else:
        raise SystemExit(f"Unsupported file extension: {suffix}")

    text = json.dumps(info, ensure_ascii=False, indent=2)
    print(text)
    if args.output_json:
        args.output_json.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
