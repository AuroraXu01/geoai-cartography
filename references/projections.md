# Projections

Use `--projection` for common aliases, or `--target-crs` for any EPSG/PROJ/custom CRS string.

Common aliases:

- `auto_utm` / `local_utm`: estimate a local UTM zone from the data centroid. Best for city/regional maps and scale bars.
- `keep`: keep the source CRS. Use only when the source CRS is already appropriate.
- `web_mercator`: EPSG:3857. Best for online tile basemaps.
- `plate_carree` / `wgs84`: EPSG:4326. Best for simple longitude/latitude display, not distance-accurate scale bars.
- `equal_earth`: global equal-area compromise map.
- `robinson`: global compromise atlas-style map.
- `mollweide`: global equal-area map.
- `world_mercator`: EPSG:3395. Global conformal Mercator.
- `world_cylindrical_equal_area`: EPSG:6933. Global equal-area cylindrical projection.
- `north_polar_stereo`: EPSG:3413. Arctic maps.
- `south_polar_stereo`: EPSG:3031. Antarctic maps.
- `usa_albers` / `conus_albers`: EPSG:5070. Continental United States thematic maps.
- `europe_laea`: EPSG:3035. Europe equal-area maps.
- `china_albers`: Albers Equal Area centered for China.
- `asia_lambert`: Lambert Conformal Conic centered for Asia.

Examples:

```bash
python scripts/render_map.py input.shp --field value --mode classified --projection usa_albers --output usa_map.jpg
python scripts/render_map.py input.shp --field value --mode classified --projection equal_earth --output world_equal_area.jpg
python scripts/render_map.py input.shp --field value --mode classified --target-crs EPSG:4490 --output custom_crs.jpg
```

Guidance:

- Use equal-area projections for area-based choropleths.
- Use local UTM for distance, buffers, and regional point maps.
- Use Web Mercator when aligning with online XYZ tiles.
- Avoid using EPSG:4326 for final scale bars unless the map is explicitly a longitude/latitude reference display.
