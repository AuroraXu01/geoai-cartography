#!/usr/bin/env python3
"""Render publication-ready maps from local vector or raster files."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from pathlib import Path


VECTOR_EXTENSIONS = {".shp", ".gpkg", ".geojson", ".json"}
RASTER_EXTENSIONS = {".tif", ".tiff"}
SKILL_DIR = Path(__file__).resolve().parents[1]
BASEMAP_DIR = SKILL_DIR / "assets" / "basemaps" / "natural_earth_110m"
PALETTES_PATH = SKILL_DIR / "assets" / "palettes.json"
BASEMAP_STYLES = {
    "naturalearth": {"land": "#f1efe9", "boundary": "#a9a9a9"},
    "naturalearth-muted": {"land": "#f4f3ee", "boundary": "#c7c7c7"},
    "naturalearth-gray": {"land": "#eeeeee", "boundary": "#999999"},
    "naturalearth-dark": {"land": "#30343b", "boundary": "#707782"},
}
PROJECTION_ALIASES = {
    "auto_utm": "Auto-estimated local UTM",
    "local_utm": "Auto-estimated local UTM",
    "keep": "Keep source CRS",
    "web_mercator": "EPSG:3857",
    "plate_carree": "EPSG:4326",
    "wgs84": "EPSG:4326",
    "equal_earth": "+proj=eqearth +datum=WGS84 +units=m +no_defs",
    "robinson": "+proj=robin +datum=WGS84 +units=m +no_defs",
    "mollweide": "+proj=moll +datum=WGS84 +units=m +no_defs",
    "world_mercator": "EPSG:3395",
    "world_cylindrical_equal_area": "EPSG:6933",
    "north_polar_stereo": "EPSG:3413",
    "south_polar_stereo": "EPSG:3031",
    "usa_albers": "EPSG:5070",
    "conus_albers": "EPSG:5070",
    "europe_laea": "EPSG:3035",
    "china_albers": "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs",
    "asia_lambert": "+proj=lcc +lat_1=30 +lat_2=60 +lat_0=0 +lon_0=100 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs",
}


def require(module_name: str, install_name: str | None = None):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        package = install_name or module_name
        raise SystemExit(
            f"Missing dependency '{module_name}'. Install with: pip install {package}"
        ) from exc


def estimate_utm_crs(bounds, crs):
    pyproj = require("pyproj")
    source = pyproj.CRS.from_user_input(crs) if crs else None
    if source and source.is_projected:
        return source
    lon = (bounds[0] + bounds[2]) / 2
    lat = (bounds[1] + bounds[3]) / 2
    zone = int((lon + 180) / 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return pyproj.CRS.from_epsg(epsg)


def resolve_target_crs(bounds, source_crs, projection="auto_utm", target_crs=None):
    pyproj = require("pyproj")
    source = pyproj.CRS.from_user_input(source_crs) if source_crs else None
    if target_crs:
        return pyproj.CRS.from_user_input(target_crs)
    projection = (projection or "auto_utm").lower()
    if projection in {"auto_utm", "local_utm"}:
        return estimate_utm_crs(bounds, source_crs)
    if projection == "keep":
        return source or estimate_utm_crs(bounds, source_crs)
    if projection not in PROJECTION_ALIASES:
        valid = ", ".join(sorted(PROJECTION_ALIASES))
        raise SystemExit(f"Unknown projection '{projection}'. Use --target-crs for custom CRS or one of: {valid}")
    return pyproj.CRS.from_user_input(PROJECTION_ALIASES[projection])


def nice_number(value):
    if value <= 0:
        return 1
    exponent = math.floor(math.log10(value))
    fraction = value / 10**exponent
    if fraction < 1.5:
        nice = 1
    elif fraction < 3.5:
        nice = 2
    elif fraction < 7.5:
        nice = 5
    else:
        nice = 10
    return nice * 10**exponent


def load_palette(name):
    if not name:
        return None
    if PALETTES_PATH.exists():
        palettes = json.loads(PALETTES_PATH.read_text(encoding="utf-8"))
        if name in palettes:
            colors = palettes[name]
            matplotlib = require("matplotlib")
            return matplotlib.colors.ListedColormap(colors, name=name)
    return name


def resolve_cmap(name=None, fallback=None, lut=None):
    plt = require("matplotlib.pyplot", "matplotlib")
    matplotlib = require("matplotlib")
    cmap = load_palette(name) or load_palette(fallback) or fallback
    if isinstance(cmap, matplotlib.colors.Colormap):
        if lut is None:
            return cmap
        samples = [cmap(i / max(lut - 1, 1)) for i in range(lut)]
        return matplotlib.colors.ListedColormap(samples, name=f"{cmap.name}_{lut}")
    return plt.get_cmap(cmap, lut) if lut is not None else plt.get_cmap(cmap)


def parse_breaks(text):
    if not text:
        raise SystemExit("--scheme manual requires --breaks, for example --breaks '0,1,5,10'.")
    try:
        breaks = [float(part.strip()) for part in text.split(",") if part.strip()]
    except ValueError as exc:
        raise SystemExit("--breaks must be a comma-separated numeric list.") from exc
    if len(breaks) < 2:
        raise SystemExit("--breaks must contain at least two numbers.")
    if any(breaks[i] >= breaks[i + 1] for i in range(len(breaks) - 1)):
        raise SystemExit("--breaks must be strictly ascending.")
    np = require("numpy")
    return np.asarray(breaks, dtype=float)


def classify_values(values, classes=5, scheme="equal_interval", manual_breaks=None):
    np = require("numpy")
    clean = np.asarray(values)
    clean = clean[np.isfinite(clean)]
    if clean.size == 0:
        raise SystemExit("No finite values available for classification.")
    classes = max(2, int(classes))
    scheme = scheme.lower()
    if scheme == "manual":
        breaks = parse_breaks(manual_breaks)
    elif scheme == "log":
        positive = clean[clean > 0]
        if positive.size == 0:
            raise SystemExit("Log classification requires positive values.")
        breaks = np.geomspace(positive.min(), positive.max(), classes + 1)
    elif scheme == "quantile":
        breaks = np.quantile(clean, np.linspace(0, 1, classes + 1))
    elif scheme in {"natural_breaks", "jenks"}:
        try:
            mapclassify = require("mapclassify")
            nb = mapclassify.NaturalBreaks(clean, k=classes)
            breaks = np.concatenate(([clean.min()], nb.bins))
        except SystemExit:
            breaks = np.linspace(clean.min(), clean.max(), classes + 1)
    else:
        breaks = np.linspace(clean.min(), clean.max(), classes + 1)
    breaks = np.unique(breaks)
    if breaks.size < 3:
        breaks = np.linspace(clean.min(), clean.max(), min(classes, 2) + 1)
    return breaks


def format_distance(meters):
    if meters >= 1000:
        return f"{meters / 1000:g} km"
    return f"{meters:g} m"


def add_scale_bar(ax, bounds, length=None, location=(0.08, 0.06)):
    add_scale_bar_style(ax, bounds, length=length, location=location, style="line")


def add_scale_bar_style(ax, bounds, length=None, location=(0.08, 0.06), style="line"):
    if style == "none":
        return
    xmin, ymin, xmax, ymax = bounds
    width = xmax - xmin
    height = ymax - ymin
    if length is None:
        length = nice_number(width / 5)
    x0 = xmin + width * location[0]
    y0 = ymin + height * location[1]
    if style == "alternating":
        bar_height = height * 0.012
        half = length / 2
        ax.add_patch(require("matplotlib.patches", "matplotlib").Rectangle((x0, y0), half, bar_height, facecolor="black", edgecolor="black", zorder=10))
        ax.add_patch(require("matplotlib.patches", "matplotlib").Rectangle((x0 + half, y0), half, bar_height, facecolor="white", edgecolor="black", zorder=10))
    else:
        linewidth = 3 if style == "line" else 1.8
        ax.plot([x0, x0 + length], [y0, y0], color="black", linewidth=linewidth, solid_capstyle="butt", zorder=10)
    ax.plot([x0, x0], [y0 - height * 0.01, y0 + height * 0.01], color="black", linewidth=2, zorder=10)
    ax.plot([x0 + length, x0 + length], [y0 - height * 0.01, y0 + height * 0.01], color="black", linewidth=2, zorder=10)
    ax.text(x0 + length / 2, y0 + height * 0.025, format_distance(length), ha="center", va="bottom", fontsize=9, zorder=10)


def add_north_arrow(ax, location=(0.93, 0.9)):
    add_north_arrow_style(ax, location=location, style="simple")


def add_north_arrow_style(ax, location=(0.93, 0.9), style="simple"):
    if style == "none":
        return
    if style == "triangle":
        ax.annotate("N", xy=(location[0], location[1] + 0.035), xycoords="axes fraction", ha="center", va="center", fontsize=13, fontweight="bold")
        ax.scatter([location[0]], [location[1] - 0.055], transform=ax.transAxes, marker="^", s=850, color="black", zorder=12)
        return
    if style == "compass":
        x, y = location
        ax.annotate("N", xy=(x, y + 0.04), xycoords="axes fraction", ha="center", va="center", fontsize=12, fontweight="bold")
        ax.annotate("", xy=(x, y - 0.015), xytext=(x, y - 0.13), xycoords="axes fraction", arrowprops=dict(facecolor="black", edgecolor="black", width=3, headwidth=11, headlength=13))
        ax.annotate("", xy=(x + 0.055, y - 0.075), xytext=(x - 0.055, y - 0.075), xycoords="axes fraction", arrowprops=dict(arrowstyle="<->", color="black", linewidth=1.5))
        return
    ax.annotate(
        "N",
        xy=location,
        xycoords="axes fraction",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
    )
    ax.annotate(
        "",
        xy=(location[0], location[1] - 0.035),
        xytext=(location[0], location[1] - 0.13),
        xycoords="axes fraction",
        arrowprops=dict(facecolor="black", edgecolor="black", width=4, headwidth=13, headlength=16),
    )


def setup_axis(ax, title=None, note=None):
    ax.set_aspect("equal")
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    if note:
        ax.text(0.0, -0.035, note, transform=ax.transAxes, fontsize=8, ha="left", va="top", color="#333333")


def plot_naturalearth_basemap(ax, target_crs, bounds, land_color="#f1efe9", boundary_color="#a9a9a9"):
    gpd = require("geopandas")
    land_path = BASEMAP_DIR / "ne_110m_land.shp"
    countries_path = BASEMAP_DIR / "ne_110m_admin_0_countries.shp"
    if not land_path.exists() or not countries_path.exists():
        raise SystemExit(f"Natural Earth basemap files are missing from {BASEMAP_DIR}")

    land = gpd.read_file(land_path).to_crs(target_crs)
    countries = gpd.read_file(countries_path).to_crs(target_crs)
    x0, y0, x1, y1 = bounds
    xpad = (x1 - x0) * 0.08
    ypad = (y1 - y0) * 0.08
    view = (x0 - xpad, y0 - ypad, x1 + xpad, y1 + ypad)
    land.plot(ax=ax, color=land_color, edgecolor="none", zorder=0)
    countries.boundary.plot(ax=ax, color=boundary_color, linewidth=0.35, zorder=1)
    ax.set_xlim(view[0], view[2])
    ax.set_ylim(view[1], view[3])


def plot_online_basemap(ax, target_crs, tile_source=None, tile_zoom=None):
    contextily = require("contextily")
    source = tile_source or "OpenStreetMap.Mapnik"
    zoom = "auto" if tile_zoom is None else tile_zoom
    contextily.add_basemap(
        ax,
        crs=target_crs.to_string() if hasattr(target_crs, "to_string") else target_crs,
        source=source,
        zoom=zoom,
        attribution_size=6,
        reset_extent=False,
    )


def plot_basemap(ax, args, target_crs, bounds):
    if args.basemap in BASEMAP_STYLES:
        style = BASEMAP_STYLES[args.basemap]
        plot_naturalearth_basemap(ax, target_crs, bounds, style["land"], style["boundary"])
    elif args.basemap == "online":
        x0, y0, x1, y1 = bounds
        xpad = (x1 - x0) * 0.08
        ypad = (y1 - y0) * 0.08
        ax.set_xlim(x0 - xpad, x1 + xpad)
        ax.set_ylim(y0 - ypad, y1 + ypad)
        plot_online_basemap(ax, target_crs, args.tile_source, args.tile_zoom)


def render_vector(args, path):
    gpd = require("geopandas")
    np = require("numpy")
    plt = require("matplotlib.pyplot", "matplotlib")
    matplotlib = require("matplotlib")

    gdf = gpd.read_file(path)
    if gdf.empty:
        raise SystemExit("Vector file has no features.")
    if args.field and args.field not in gdf.columns:
        raise SystemExit(f"Field '{args.field}' not found. Available fields: {', '.join(map(str, gdf.columns))}")

    target_crs = resolve_target_crs(gdf.total_bounds, gdf.crs, args.projection, args.target_crs)
    plot_gdf = gdf.to_crs(target_crs) if gdf.crs else gdf
    bounds = plot_gdf.total_bounds

    fig, ax = plt.subplots(figsize=(args.width, args.height), dpi=args.dpi)
    note = args.note or f"CRS: {target_crs.to_string() if hasattr(target_crs, 'to_string') else target_crs}"

    if not args.field:
        plot_basemap(ax, args, target_crs, bounds)
        plot_gdf.plot(ax=ax, facecolor=args.fill_color, edgecolor=args.edge_color, linewidth=args.linewidth)
    elif args.mode == "unique":
        plot_basemap(ax, args, target_crs, bounds)
        plot_gdf[args.field] = plot_gdf[args.field].astype("category")
        plot_gdf.plot(
            column=args.field,
            categorical=True,
            cmap=resolve_cmap(args.cmap, "geo_cat"),
            legend=True,
            ax=ax,
            edgecolor=args.edge_color,
            linewidth=args.linewidth,
            legend_kwds={"loc": "center left", "bbox_to_anchor": (1.02, 0.5), "frameon": False},
        )
    elif args.mode == "classified":
        plot_basemap(ax, args, target_crs, bounds)
        values = plot_gdf[args.field].astype(float).to_numpy()
        breaks = classify_values(values, args.classes, args.scheme, args.breaks)
        labels = [f"{breaks[i]:.3g} - {breaks[i + 1]:.3g}" for i in range(len(breaks) - 1)]
        bins = np.digitize(values, breaks[1:-1], right=True)
        plot_gdf["_carto_class"] = [labels[i] for i in bins]
        plot_gdf.plot(
            column="_carto_class",
            categorical=True,
            cmap=resolve_cmap(args.cmap, "geo_seq"),
            legend=True,
            ax=ax,
            edgecolor=args.edge_color,
            linewidth=args.linewidth,
            legend_kwds={"title": args.field, "loc": "center left", "bbox_to_anchor": (1.02, 0.5), "frameon": False},
        )
    else:
        plot_basemap(ax, args, target_crs, bounds)
        plot_gdf.plot(
            column=args.field,
            cmap=resolve_cmap(args.cmap, "viridis"),
            legend=True,
            ax=ax,
            edgecolor=args.edge_color,
            linewidth=args.linewidth,
            legend_kwds={"label": args.field, "shrink": 0.72},
        )

    setup_axis(ax, args.title, note)
    add_scale_bar_style(ax, bounds, args.scale_length, style=args.scale_style)
    add_north_arrow_style(ax, style=args.north_arrow)
    save_figure(fig, args.output, args.dpi)
    write_metadata(args, path, "vector", note)


def raster_to_projected_array(src, target_crs):
    rasterio = require("rasterio")
    np = require("numpy")
    from rasterio.warp import Resampling, calculate_default_transform, reproject

    transform, width, height = calculate_default_transform(src.crs, target_crs, src.width, src.height, *src.bounds)
    destination = np.full((height, width), src.nodata if src.nodata is not None else np.nan, dtype="float32")
    reproject(
        source=rasterio.band(src, 1),
        destination=destination,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=transform,
        dst_crs=target_crs,
        resampling=Resampling.nearest,
    )
    left = transform.c
    top = transform.f
    right = left + transform.a * width
    bottom = top + transform.e * height
    return destination, (left, right, bottom, top)


def render_raster(args, path):
    rasterio = require("rasterio")
    np = require("numpy")
    plt = require("matplotlib.pyplot", "matplotlib")
    matplotlib = require("matplotlib")
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch

    with rasterio.open(path) as src:
        source_bounds = [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top]
        target_crs = resolve_target_crs(source_bounds, src.crs, args.projection, args.target_crs)
        if src.crs and not src.crs.is_projected:
            data, extent = raster_to_projected_array(src, target_crs)
        else:
            data = src.read(1).astype("float32")
            extent = (src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top)
        nodata = src.nodata

    masked = np.ma.masked_invalid(data)
    if nodata is not None:
        masked = np.ma.masked_where(data == nodata, masked)
    values = masked.compressed()
    if values.size == 0:
        raise SystemExit("Raster has no finite, non-nodata values in band 1.")

    fig, ax = plt.subplots(figsize=(args.width, args.height), dpi=args.dpi)
    note = args.note or f"CRS: {target_crs.to_string() if hasattr(target_crs, 'to_string') else target_crs}"

    if args.mode == "unique":
        unique_values = np.unique(values)
        if unique_values.size > 30:
            raise SystemExit("Unique raster mode found more than 30 classes. Use classified or continuous mode.")
        base = resolve_cmap(args.cmap, "geo_cat", unique_values.size)
        cmap = ListedColormap([base(i) for i in range(unique_values.size)])
        index = np.full(masked.shape, np.nan)
        for i, value in enumerate(unique_values):
            index[np.asarray(masked == value)] = i
        ax.imshow(index, extent=extent, origin="upper", cmap=cmap, interpolation="nearest")
        handles = [Patch(facecolor=cmap(i), edgecolor="none", label=f"{v:g}") for i, v in enumerate(unique_values)]
        ax.legend(handles=handles, title=args.legend_title or "Class", loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    elif args.mode == "classified":
        breaks = classify_values(values, args.classes, args.scheme, args.breaks)
        cmap = resolve_cmap(args.cmap, "geo_seq", len(breaks) - 1)
        norm = BoundaryNorm(breaks, cmap.N)
        image = ax.imshow(masked, extent=extent, origin="upper", cmap=cmap, norm=norm, interpolation="nearest")
        cbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.025)
        cbar.set_label(args.legend_title or "Value")
        cbar.set_ticks(breaks)
        cbar.ax.set_yticklabels([f"{v:.3g}" for v in breaks])
    else:
        image = ax.imshow(masked, extent=extent, origin="upper", cmap=resolve_cmap(args.cmap, "viridis"), interpolation="nearest")
        cbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.025)
        cbar.set_label(args.legend_title or "Value")

    bounds = (extent[0], extent[2], extent[1], extent[3])
    setup_axis(ax, args.title, note)
    add_scale_bar_style(ax, bounds, args.scale_length, style=args.scale_style)
    add_north_arrow_style(ax, style=args.north_arrow)
    save_figure(fig, args.output, args.dpi)
    write_metadata(args, path, "raster", note)


def save_figure(fig, output, dpi):
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, bbox_inches="tight", facecolor="white")
    print(f"Wrote {output}")


def write_metadata(args, path, input_type, note):
    metadata_path = Path(str(args.output) + ".metadata.json").expanduser().resolve()
    metadata = {
        "input": str(path),
        "input_type": input_type,
        "output": str(Path(args.output).expanduser().resolve()),
        "mode": args.mode,
        "field": args.field,
        "scheme": args.scheme,
        "breaks": args.breaks,
        "classes": args.classes,
        "cmap": args.cmap,
        "dpi": args.dpi,
        "title": args.title,
        "note": note,
        "projection": args.projection,
        "target_crs": args.target_crs,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {metadata_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a local vector or raster geospatial map.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True)
    parser.add_argument("--field")
    parser.add_argument("--mode", choices=["unique", "classified", "continuous"], default="continuous")
    parser.add_argument("--scheme", choices=["equal_interval", "quantile", "natural_breaks", "jenks", "log", "manual"], default="equal_interval")
    parser.add_argument("--classes", type=int, default=5)
    parser.add_argument("--breaks", help="Comma-separated manual breaks for --scheme manual, for example '0,1,5,10'.")
    parser.add_argument("--cmap")
    parser.add_argument("--title")
    parser.add_argument("--legend-title")
    parser.add_argument("--note")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--width", type=float, default=7.5)
    parser.add_argument("--height", type=float, default=6.0)
    parser.add_argument("--scale-length", type=float)
    parser.add_argument(
        "--projection",
        choices=sorted(PROJECTION_ALIASES),
        default="auto_utm",
        help="Named projection alias. Use --target-crs for any EPSG/PROJ/custom CRS.",
    )
    parser.add_argument("--target-crs", help="Custom output CRS, for example EPSG:3857 or a PROJ string. Overrides --projection.")
    parser.add_argument("--basemap", choices=["none", "naturalearth", "naturalearth-muted", "naturalearth-gray", "naturalearth-dark", "online"], default="none")
    parser.add_argument("--tile-source", default="OpenStreetMap.Mapnik", help="contextily/xyzservices tile source for --basemap online.")
    parser.add_argument("--tile-zoom", type=int, help="Tile zoom for --basemap online. Default: auto.")
    parser.add_argument("--north-arrow", choices=["simple", "triangle", "compass", "none"], default="simple")
    parser.add_argument("--scale-style", choices=["line", "alternating", "ticks", "none"], default="line")
    parser.add_argument("--fill-color", default="#d9d9d9")
    parser.add_argument("--edge-color", default="#333333")
    parser.add_argument("--linewidth", type=float, default=0.35)
    args = parser.parse_args()

    path = args.input.expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Input does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix in VECTOR_EXTENSIONS:
        render_vector(args, path)
    elif suffix in RASTER_EXTENSIONS:
        render_raster(args, path)
    else:
        raise SystemExit(f"Unsupported file extension: {suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
