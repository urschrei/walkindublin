import osmnx as ox


def truncate(graph, centre, distance=2000):
    centre_node = ox.get_nearest_node(graph, centre)
    truncated = ox.core.truncate_graph_dist(
        graph, centre_node, max_distance=distance, weight="length", retain_all=False
    )
    gdf_truncated = ox.save_load.graph_to_gdfs(
        truncated, edges=True, node_geometry=False, fill_edge_geometry=True
    )
    # we MAY need .to_crs("EPSG:4326")
    gdf_truncated[1][["geometry"]].to_file("static/trunc.geojson", driver="GeoJSON")
    return list(gdf_truncated[1].total_bounds)
