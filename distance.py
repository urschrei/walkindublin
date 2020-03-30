import os
from flask import Flask
from flask import render_template
from flask import jsonify, request

import logging

# OSMnx config
import osmnx as ox

ox.config(use_cache=True)
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon

# pyproj config
from pyproj import CRS

crs = CRS.from_epsg(4326)
utm = CRS.from_epsg(32629)

# this file includes edge lengths as the 'length' property
# ox assumes a "data" directory in which this file is located tsk tsk
G = ox.load_graphml("dublin.graphml")
# G_projected = ox.project_graph(G)

from walk_limits import truncate

# TODO: incoming lon, lat coords must be projected to correct UTM (EPSG:32629)
# TODO: build Point from projected point coords

app = Flask(__name__)

# load configs
app.config.from_pyfile("config/common.py")
# actual CSRF secret key and db connection string go in here
try:
    app.config.from_pyfile("config/sensitive.py")
except IOError:
    pass
if os.getenv("DEV_CONFIGURATION"):
    app.config.from_envvar("DEV_CONFIGURATION")

# set up logging
if not app.debug:
    log_format = logging.Formatter(
        """
---
Message type:       %(levelname)s
Location:           %(pathname)s:%(lineno)d
Module:             %(module)s
Time:               %(asctime)s

%(message)s

"""
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_format)
    app.logger.addHandler(stream_handler)


@app.route("/")
def index():
    return render_template("index.jinja")


@app.route("/streets", methods=["POST"])
def streets():
    js = request.get_json(force=True)
    # calculate street network
    if js.get("coords", None):
        bounds = truncate(G, (js["coords"]["latitude"], js["coords"]["longitude"]))
        return jsonify(bounds)


if __name__ == "__main__":
    app.run()
