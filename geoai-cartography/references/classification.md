# Classification

Supported schemes:

- `equal_interval`: equal-width classes.
- `quantile`: equal feature counts per class.
- `natural_breaks` / `jenks`: data-adaptive breaks through `mapclassify` when installed.
- `log`: logarithmic breaks for strictly positive skewed values.
- `manual`: user-provided class breaks.

Manual breaks:

```bash
python scripts/render_map.py input.shp --field height --mode classified --scheme manual --breaks "0,0.1,0.5,1,5,10"
```

Rules:

- Manual breaks must be ascending.
- Log classification requires positive values.
- For highly skewed hazards, population, GDP, and flow variables, prefer `log` or manual breaks.
- For publication maps, state the classification method in the caption or metadata.
