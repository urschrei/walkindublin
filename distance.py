import os
from flask import Flask
from flask import render_template
from flask import jsonify, request
import json

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
full_graph_gdf = ox.save_load.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)

from walk_limits import truncate
from route_utils import generate_route

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


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(e):
    # note that we set the 403 status explicitly
    return render_template("403.html"), 403


@app.errorhandler(500)
def app_error(e):
    # note that we set the 500 status explicitly
    return render_template("500.html"), 500


@app.route("/")
def index():
    return render_template("index.jinja")


@app.route("/streets", methods=["POST"])
def streets():
    js = request.get_json(force=True)
    # first, ensure we're within bounds
    tb = full_graph_gdf.total_bounds
    if (
        js.get("lon", -6.4) < tb[0]
        or js.get("lon", -6.0) > tb[2]
        or js.get("lat", 53.32) < tb[1]
        or js.get("lat", 53.45) > tb[3]
    ):
        raise InvalidUsage("Your coordinates are out of bounds.", status_code=400)
    # calculate street network
    if js.get("lat", None) and js.get("lon", None):
        gdf_t = truncate(G, (js["lat"], js["lon"]))
        resp = [
            gdf_t.__geo_interface__,
            list(gdf_t.total_bounds),
        ]
        response = app.response_class(
            response=json.dumps(resp), mimetype="application/json"
        )
        return response
    else:
        raise InvalidUsage(
            "Something went wrong with your coordinates", status_code=400
        )


@app.route("/route", methods=["POST"])
def route():
    js = request.get_json(force=True)
    # first, ensure we're within bounds
    tb = full_graph_gdf.total_bounds
    if (
        js.get("lon", -6.4) < tb[0]
        or js.get("lon", -6.0) > tb[2]
        or js.get("lat", 53.32) < tb[1]
        or js.get("lat", 53.45) > tb[3]
    ):
        raise InvalidUsage("Your coordinates are out of bounds.", status_code=400)
    # calculate a route
    if js.get("lat", None) and js.get("lon", None):
        route_nodes = generate_route(js["lat"], js["lon"], 4, graph=G)
        route_nodes = list(zip(route_nodes[:-1], route_nodes[1:]))
        index = [
            full_graph_gdf[
                (full_graph_gdf["u"] == u) & (full_graph_gdf["v"] == v)
            ].index[0]
            for u, v in route_nodes
        ]
        gdf_route_edges = full_graph_gdf.loc[index]
        # we'd ordinarily just call to_json, but since we need to send the bounds too
        # we have to manually build the json from a list containing both
        resp = [
            gdf_route_edges.geometry.__geo_interface__,
            list(gdf_route_edges.total_bounds),
        ]
        response = app.response_class(
            response=json.dumps(resp), mimetype="application/json"
        )
        return response
    else:
        raise InvalidUsage(
            "Something went wrong with your coordinates", status_code=400
        )


if __name__ == "__main__":
    app.run()
