import osmnx as ox
from osmnx.simplify import simplify_graph


def truncate(graph, centre, distance=2000):
    centre_node = ox.get_nearest_node(graph, centre)
    truncated = ox.core.truncate_graph_dist(
        graph, centre_node, max_distance=distance, weight="length", retain_all=False
    )
    gdf_truncated = ox.save_load.graph_to_gdfs(
        simplify_graph(truncated), nodes=False, edges=True, node_geometry=False, fill_edge_geometry=True
    )
    # we MAY need .to_crs("EPSG:4326")
    return gdf_truncated["geometry"]
