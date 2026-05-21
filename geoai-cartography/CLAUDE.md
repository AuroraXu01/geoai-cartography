# CLAUDE.md

This repository is an AI-agent-friendly GeoAI cartography toolkit. It is also a Codex skill, but the Python scripts can be used by Claude, Claude Code, local terminals, notebooks, and other agents.

## How To Approach Tasks

1. Read `README.md` first for supported inputs, outputs, examples, and dependencies.
2. Use the scripts instead of rewriting map logic from scratch.
3. Keep outputs in an explicit user-provided output directory, or create an `outputs/` directory in the working project.
4. After rendering, verify that the expected image/vector files exist. If possible, visually inspect the output.
5. Preserve attribution for online basemaps.

## Main Scripts

- `scripts/inspect_spatial_file.py`: inspect vector, raster, or tabular input metadata.
- `scripts/tabular_to_points.py`: convert CSV/TSV/CST/Excel coordinate fields to point vector data.
- `scripts/render_map.py`: render vector or raster maps with classification, palettes, basemaps, projections, scale bars, north arrows, and metadata.
- `scripts/batch_render.py`: run multiple map jobs from a JSON configuration.
- `scripts/compose_layout.py`: compose rendered map images into multi-panel figures.

## Common Workflows

Inspect first:

```bash
python scripts/inspect_spatial_file.py data/input.shp
```

Convert tabular coordinates to points:

```bash
python scripts/tabular_to_points.py data/points.tsv \
  --x Longitude \
  --y Latitude \
  --crs EPSG:4326 \
  --output outputs/points.shp
```

Render a classified map:

```bash
python scripts/render_map.py outputs/points.shp \
  --field HEIGHT_M \
  --mode classified \
  --scheme quantile \
  --classes 5 \
  --cmap risk_orange \
  --basemap naturalearth-muted \
  --projection auto_utm \
  --north-arrow triangle \
  --scale-style alternating \
  --output outputs/map.jpg
```

Use online basemap tiles:

```bash
python scripts/render_map.py outputs/points.shp \
  --field HEIGHT_M \
  --mode classified \
  --basemap online \
  --projection web_mercator \
  --tile-source OpenStreetMap.Mapnik \
  --output outputs/map_osm.jpg
```

Compose layouts:

```bash
python scripts/compose_layout.py \
  --images outputs/map_a.jpg outputs/map_b.jpg \
  --layout side-by-side \
  --labels A B \
  --output outputs/comparison.jpg
```

## Dependency Guidance

If dependencies are missing, tell the user exactly which group is needed.

Minimal tabular/layout work:

```bash
pip install pandas numpy pillow
```

Full GIS rendering:

```bash
pip install geopandas rasterio matplotlib pyproj shapely mapclassify
```

Excel and online basemaps:

```bash
pip install openpyxl contextily xyzservices
```

Do not silently install dependencies unless the environment and user instructions allow it.

## Style Parameters

Basemaps:

- `none`
- `naturalearth`
- `naturalearth-muted`
- `naturalearth-gray`
- `naturalearth-dark`
- `online`

Palettes:

- Sequential: `geo_seq`, `water`, `terrain_soft`, `risk_orange`, `risk_red`, `green`
- Diverging: `geo_div`, `residual`, `change`
- Categorical: `geo_cat`, `landuse`
- Any Matplotlib colormap can also be used.

Classification:

- `equal_interval`
- `quantile`
- `natural_breaks`
- `jenks`
- `log`
- `manual` with `--breaks "0,1,5,10"`

Projections:

- Use `auto_utm` for most local/regional maps.
- Use `web_mercator` for online tile basemaps.
- Use equal-area projections for choropleths.
- Use `--target-crs` for custom EPSG/PROJ strings.

North arrows:

- `simple`
- `triangle`
- `compass`
- `none`

Scale bars:

- `line`
- `alternating`
- `ticks`
- `none`

## Safety And Quality Checks

Before final response:

- Confirm output file paths.
- Confirm the number of converted/rendered features if available.
- Mention if the map uses online tiles and include attribution.
- Mention if CRS/projection was inferred.
- Mention any skipped rows, missing values, or unsupported features.

Do not claim a map is publication-ready without checking the rendered output visually or at least confirming file creation and metadata.

## Repository Notes

- `SKILL.md` and `agents/openai.yaml` are Codex-specific entrypoints.
- `CLAUDE.md`, `README.md`, scripts, references, and assets are usable by any agent.
- Bundled Natural Earth basemap data is public domain.
- Repository code is MIT licensed.
