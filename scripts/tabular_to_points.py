#!/usr/bin/env python3
"""Convert tabular coordinate data to point vector files."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path


TABLE_EXTENSIONS = {".csv", ".tsv", ".cst", ".txt", ".xls", ".xlsx"}
VECTOR_EXTENSIONS = {".shp", ".gpkg", ".geojson", ".json"}
X_CANDIDATES = ("lon", "lng", "long", "longitude", "x", "xcoord", "x_coord", "easting")
Y_CANDIDATES = ("lat", "latitude", "y", "ycoord", "y_coord", "northing")


def require(module_name: str, install_name: str | None = None):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        package = install_name or module_name
        raise SystemExit(
            f"Missing dependency '{module_name}'. Install with: pip install {package}"
        ) from exc


def normalized(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name).strip().lower())


def read_table(path: Path, sheet=None, delimiter=None):
    pd = require("pandas")
    suffix = path.suffix.lower()
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path, sheet_name=sheet or 0)
    if delimiter:
        return pd.read_csv(path, sep=delimiter)
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    if suffix == ".cst":
        return pd.read_csv(path, sep=None, engine="python")
    return pd.read_csv(path)


def detect_column(columns, candidates):
    lookup = {normalized(column): column for column in columns}
    for candidate in candidates:
        key = normalized(candidate)
        if key in lookup:
            return lookup[key]
    return None


def output_driver(output: Path):
    suffix = output.suffix.lower()
    if suffix == ".shp":
        return "ESRI Shapefile"
    if suffix == ".gpkg":
        return "GPKG"
    if suffix in {".geojson", ".json"}:
        return "GeoJSON"
    raise SystemExit(f"Unsupported output extension: {suffix}. Use .shp, .gpkg, or .geojson.")


def trim_shapefile_columns(df):
    """Keep Shapefile DBF names deterministic and within the 10-character limit."""
    used = set()
    rename = {}
    for column in df.columns:
        base = re.sub(r"[^A-Za-z0-9_]+", "_", str(column)).strip("_") or "field"
        base = base[:10]
        name = base
        i = 1
        while name.lower() in used:
            suffix = str(i)
            name = f"{base[:10 - len(suffix)]}{suffix}"
            i += 1
        used.add(name.lower())
        rename[column] = name
    return df.rename(columns=rename), rename


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert CSV/TSV/CST/Excel coordinate fields to point vector data.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--x", help="X/longitude/easting field name.")
    parser.add_argument("--y", help="Y/latitude/northing field name.")
    parser.add_argument("--crs", default="EPSG:4326", help="Input coordinate CRS. Default: EPSG:4326.")
    parser.add_argument("--to-crs", help="Optional output CRS, for example EPSG:32650.")
    parser.add_argument("--sheet", help="Excel sheet name or index. Default: first sheet.")
    parser.add_argument("--delimiter", help="Optional delimiter for text tables, for example ',' or '\\t'.")
    parser.add_argument("--drop-invalid", action="store_true", help="Drop rows with missing or nonnumeric coordinates.")
    parser.add_argument("--layer", help="Layer name for GeoPackage output.")
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input does not exist: {input_path}")
    if input_path.suffix.lower() not in TABLE_EXTENSIONS:
        raise SystemExit(f"Unsupported input extension: {input_path.suffix}")
    if output_path.suffix.lower() not in VECTOR_EXTENSIONS:
        raise SystemExit(f"Unsupported output extension: {output_path.suffix}")

    pd = require("pandas")
    gpd = require("geopandas")

    sheet = int(args.sheet) if args.sheet and args.sheet.isdigit() else args.sheet
    df = read_table(input_path, sheet=sheet, delimiter=args.delimiter)
    if df.empty:
        raise SystemExit("Input table has no rows.")

    x_col = args.x or detect_column(df.columns, X_CANDIDATES)
    y_col = args.y or detect_column(df.columns, Y_CANDIDATES)
    if not x_col or not y_col:
        raise SystemExit(
            "Could not detect coordinate fields. Use --x and --y. "
            f"Available columns: {', '.join(map(str, df.columns))}"
        )
    if x_col not in df.columns or y_col not in df.columns:
        raise SystemExit(f"Coordinate fields not found. Available columns: {', '.join(map(str, df.columns))}")

    df = df.copy()
    df[x_col] = pd.to_numeric(df[x_col], errors="coerce")
    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
    invalid = df[x_col].isna() | df[y_col].isna()
    if invalid.any():
        if args.drop_invalid:
            df = df.loc[~invalid].copy()
        else:
            raise SystemExit(
                f"Found {int(invalid.sum())} rows with invalid coordinates. "
                "Re-run with --drop-invalid to omit them."
            )
    if df.empty:
        raise SystemExit("No rows remain after dropping invalid coordinates.")

    geometry = gpd.points_from_xy(df[x_col], df[y_col], crs=args.crs)
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=args.crs)
    if args.to_crs:
        gdf = gdf.to_crs(args.to_crs)

    rename_map = None
    if output_path.suffix.lower() == ".shp":
        geometry_name = gdf.geometry.name
        attrs = gdf.drop(columns=[geometry_name])
        attrs, rename_map = trim_shapefile_columns(attrs)
        gdf = gpd.GeoDataFrame(attrs, geometry=gdf.geometry, crs=gdf.crs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    driver = output_driver(output_path)
    write_kwargs = {"driver": driver}
    if output_path.suffix.lower() == ".gpkg" and args.layer:
        write_kwargs["layer"] = args.layer
    gdf.to_file(output_path, **write_kwargs)

    metadata = {
        "input": str(input_path),
        "output": str(output_path),
        "rows_written": int(len(gdf)),
        "x_field": x_col,
        "y_field": y_col,
        "input_crs": args.crs,
        "output_crs": str(gdf.crs) if gdf.crs else None,
        "renamed_fields_for_shapefile": rename_map,
    }
    metadata_path = Path(str(output_path) + ".metadata.json")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    print(f"Wrote {metadata_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
