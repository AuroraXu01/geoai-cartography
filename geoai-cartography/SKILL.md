---
name: geoai-cartography
description: Generate publication-ready maps from local vector, raster, or tabular geospatial files. Use when the user provides .shp, .gpkg, .geojson, .tif, .tiff, .csv, .tsv, .cst, .xls, or .xlsx data and asks to convert coordinate fields into point Shapefiles/GeoPackages/GeoJSON, unique-value coloring, classified choropleth maps, continuous raster maps, scale bars, north arrows, legends, CRS-aware layout, or PNG/PDF/SVG/TIFF map exports.
---

# GeoAI Cartography

Use this skill to make reproducible local maps from geospatial files. Prefer the bundled scripts for deterministic inspection, tabular point conversion, and rendering.

## Supported Inputs

- Vector: `.shp`, `.gpkg`, `.geojson`
- Raster: `.tif`, `.tiff`
- Tabular points: `.csv`, `.tsv`, `.cst`, `.xls`, `.xlsx`
- Outputs: `.png`, `.jpg`, `.jpeg`, `.pdf`, `.svg`, `.tif`, `.tiff`
- Vector conversion outputs: `.shp`, `.gpkg`, `.geojson`

## Workflow

1. Inspect the file first:

```bash
python scripts/inspect_spatial_file.py /path/to/input.shp
```

2. If the input is a table with coordinate fields, convert it to a point vector file:

```bash
python scripts/tabular_to_points.py points.csv --x lon --y lat --crs EPSG:4326 --output points.shp
python scripts/tabular_to_points.py samples.xlsx --sheet Sheet1 --x longitude --y latitude --output samples.gpkg
python scripts/tabular_to_points.py stations.cst --x X --y Y --crs EPSG:32650 --output stations.geojson
```

The script can auto-detect common coordinate field names such as `lon`, `lng`, `longitude`, `x`, `lat`, `latitude`, and `y`, but explicit `--x` and `--y` are safer.

3. Choose map mode:

- `unique`: categorical vector field or categorical raster values.
- `classified`: numeric vector field or continuous raster grouped into classes.
- `continuous`: continuous raster or numeric vector field with a gradient colorbar.

4. Render with `scripts/render_map.py`.

Vector examples:

```bash
python scripts/render_map.py input.shp --field landuse --mode unique --basemap naturalearth --output map.pdf
python scripts/render_map.py input.gpkg --field population --mode classified --classes 5 --scheme quantile --basemap online --tile-source OpenStreetMap.Mapnik --output map.png
python scripts/render_map.py input.geojson --field ndvi --mode continuous --cmap viridis --output map.svg
python scripts/render_map.py input.shp --field height --mode classified --scheme manual --breaks "0,0.1,0.5,1,5,10" --cmap risk_orange --north-arrow compass --scale-style alternating --output map.jpg
python scripts/render_map.py input.shp --field population --mode classified --scheme log --classes 6 --basemap naturalearth-gray --output population_log.jpg
python scripts/render_map.py input.shp --field value --mode classified --projection equal_earth --output world_equal_area.jpg
python scripts/render_map.py input.shp --field value --mode classified --projection usa_albers --output usa_albers.jpg
python scripts/render_map.py input.shp --field value --mode classified --target-crs EPSG:3857 --basemap online --output web_tiles.jpg
```

Raster examples:

```bash
python scripts/render_map.py rainfall.tif --mode classified --classes 7 --scheme natural_breaks --cmap YlGnBu --output rainfall.pdf
python scripts/render_map.py landcover.tif --mode unique --output landcover.png
python scripts/render_map.py temperature.tif --mode continuous --cmap inferno --output temperature.tiff --dpi 600
```

5. Batch render when a project needs multiple maps:

```bash
python scripts/batch_render.py examples/batch_render.example.json
```

6. Compose rendered maps into layouts:

```bash
python scripts/compose_layout.py --images map_a.jpg map_b.jpg --layout side-by-side --labels A B --output comparison.jpg
python scripts/compose_layout.py --images main.jpg inset_a.jpg inset_b.jpg --layout main-sub --labels A B C --output figure_layout.jpg
python scripts/compose_layout.py --images a.jpg b.jpg c.jpg d.jpg --layout grid --cols 2 --labels A B C D --output grid.jpg
```

7. Verify the output visually. Check that:

- Features or pixels are not clipped.
- Legend labels are readable.
- Scale bar is present and plausible.
- North arrow does not cover important map content.
- CRS note and data source text do not collide with the map.

## Rendering Defaults

- If data CRS is geographic, the script estimates a local UTM projection for scale bar and layout calculations.
- Scale bars are drawn in metric units.
- North arrow is placed in the upper-right corner by default.
- Legends are outside the map frame when possible.
- Figure background is white.
- Exports use `bbox_inches=tight`.
- `--basemap naturalearth` draws bundled Natural Earth 1:110m land and country boundaries before the thematic layer.
- Offline basemap styles: `naturalearth`, `naturalearth-muted`, `naturalearth-gray`, `naturalearth-dark`.
- `--basemap online` uses `contextily`/XYZ tiles when network access is available. Always respect provider terms and attribution.
- North arrow styles: `simple`, `triangle`, `compass`, `none`.
- Scale bar styles: `line`, `alternating`, `ticks`, `none`.
- Built-in color aliases live in `assets/palettes.json`; examples include `risk_orange`, `risk_red`, `geo_seq`, `geo_div`, `geo_cat`, and `landuse`.
- Classification supports `equal_interval`, `quantile`, `natural_breaks`, `jenks`, `log`, and `manual`.
- Projection aliases include `auto_utm`, `web_mercator`, `equal_earth`, `robinson`, `mollweide`, `usa_albers`, `europe_laea`, `china_albers`, polar stereographic projections, and more. `--target-crs` accepts custom EPSG/PROJ CRS strings.

## Dependency Handling

If dependencies are missing, ask the user whether to install them in their preferred environment. Required Python packages:

```bash
pip install geopandas rasterio matplotlib numpy pyproj shapely mapclassify pandas openpyxl contextily xyzservices
```

`mapclassify` is optional. If absent, the script falls back to built-in equal interval and quantile classification. `openpyxl` is needed only for `.xlsx` input. `contextily` and `xyzservices` are needed only for online basemaps.

## Cartographic Rules

Load `references/cartographic_rules.md` when deciding projection, scale bar placement, classification, or map layout. Load `references/color_palettes.md` when choosing colors for categorical or sequential maps. Load `references/basemaps.md` when selecting or updating bundled basemap assets. Load `references/styles.md` for north arrow, scale bar, palette, basemap, and layout options. Load `references/classification.md` for manual/log classification choices. Load `references/projections.md` when choosing a projection or custom CRS.
