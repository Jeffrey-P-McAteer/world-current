
# World-CURRENT (Computational Utility for Rapid Robust Energy Network Topologies)

`world-current.py` is a data-collection and model-generation tool.

Usage is as follows:

```bash
uv run world-current.py ./path/to/config.toml

# For faster number-crunching
PYTHON_EXECUTABLE=/usr/bin/pypy3 uv run world-current.py ./data/config.toml

```

`config.toml` contains all inputs to the model. If unspecified, a template like the
following will be dumped to the screen:

```toml
model_name = "Your Model's Name"

# At exactly one of the region definitions below must be given; if a file or layer of data is specified, ALL contents
# of the file/layer will be used to select regions of the world for processing.

# The bounding box is specified as MinX, MinY, MaxX, MaxY in WGS84 coordinates
region = [-82.9657830472, 7.2205414901, -77.2425664944, 9.61161001224]

# If this is used all polygons in the file will be used to select region; formats supported are
# everything that geopandas supports.
region = "./path/to/layer.geojson"

# region may also contain inline POLYGON() wkt instead of a file-path to a text file.
# In this case whitespace will be removed from the string before parsing.
region = """
POLYGON(-82.9657830472 7.2205414901, -77.2425664944 9.61161001224, -77.1425664944 9.41161001224, -77.0325664944 9.11161001224, -82.9657830472 7.2205414901)
"""

# Download a .zip from https://datasets.wri.org/datasets/global-power-plant-database and set this to point to the .csv
path_to_global_power_plant_database = "./path/to/global_power_plant_database.csv"

# Specify an output file + details

```




