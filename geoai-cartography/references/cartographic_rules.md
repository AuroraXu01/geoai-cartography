# Cartographic Rules

- Always inspect CRS before rendering.
- For scale bars, use projected coordinates in meters. If source data is longitude/latitude, estimate a local UTM CRS from the dataset centroid and reproject for plotting.
- Use `unique` mode for nominal categories such as land use, administrative type, soil class, or classified land cover rasters.
- Use `classified` mode for numeric variables where class breaks communicate the story better than a smooth gradient.
- Use `continuous` mode for smooth surfaces such as temperature, elevation, NDVI, probability, or model uncertainty.
- Prefer 5 to 7 classes for publication maps. Use fewer classes when the legend labels are long or the data range is narrow.
- Avoid rainbow color maps for ordered data.
- Keep the north arrow small and unobtrusive.
- Place the scale bar near a map corner where it does not obscure important features.
- Include CRS and source notes when the map is meant for publication or reproducible analysis.
- For categorical maps with many classes, warn the user when there are more than 12 categories and consider grouping rare classes.
