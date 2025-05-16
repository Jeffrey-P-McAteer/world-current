
# World-CURRENT (Computational Utility for Rapid Renewable Energy Network Topologies)

`world-current.py` is a data-collection and model-generation tool.

Usage is as follows:

```
uv run world-current.py ./path/to/config.toml
```

`config.toml` contains all inputs to the model. If unspecified, a template like the
following will be dumped to the screen:

```toml
model_name = "Your Model's Name"

# At least one region_* definition must be given; if a file or layer of data is specified, ALL contents
# of the file/layer will be used to select regions of the world for processing.

# The bounding box is specified as MinX, MinY, MaxX, MaxY in WGS84 coordinates
region_bbox = [-82.9657830472, 7.2205414901, -77.2425664944, 9.61161001224]

# If this is used all polygons in the file will be used to select region
region_geojson = "./path/to/layer.geojson"

# region_wkt may also contain inline POLYGON() wkt instead of a file-path to a text file.
# In this case whitespace will be removed from the string before parsing.
region_wkt = "./path/to/wkt.txt"


```




