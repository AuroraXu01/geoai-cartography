# Basemaps

Bundled offline basemap:

- Natural Earth 1:110m land: `assets/basemaps/natural_earth_110m/ne_110m_land.*`
- Natural Earth 1:110m countries: `assets/basemaps/natural_earth_110m/ne_110m_admin_0_countries.*`
- GeoJSON copies are included for lightweight non-GIS rendering.

Use `--basemap naturalearth` for regional or global context maps. The bundled data is public domain and suitable for redistribution with this skill.

Online basemap:

- Use `--basemap online --tile-source OpenStreetMap.Mapnik` for a general road/reference basemap.
- Other providers can be passed as xyzservices names or URL templates when supported by `contextily`.
- Online tiles require network access and must follow provider attribution and usage terms.
- Prefer offline Natural Earth for reproducible manuscripts; use online tiles for exploration, city-scale context, or presentation maps.
