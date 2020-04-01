"""
Adapted from code by Heidi M Hurst:
https://github.com/heidimhurst/osmnx/blob/master/osmnx/route.py
"""

import osmnx as ox
import networkx as nx

ox.config(use_cache=True)
import numpy as np
import time
from osmnx.geo_utils import get_nearest_node, add_edge_bearings, get_bearing
from osmnx.core import graph_from_point
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon


def seg_attribute(graph, start, finish, attribute="length"):
    """
    Used to work around one way streets; returns value of attribute for edge.
    Parameters
    ----------
    graph : networkx graph object
        graph containing OSM data for area of interest
    start : int
        id of start node
    finish : int
        id of finish node
    attribute : string
        name of attribute to be obtained (default: length)
    Returns
    -------
    length : float
    """
    try:
        attr = graph[start][finish][0][attribute]
    except KeyError:
        try:
            attr = graph[finish][start][0][attribute]
        except KeyError:
            attr = 0
    return attr


def outbound_optimization(
    attributes={}, importance=[0.3, 0.3, 0.25, 0.1, 0.05], pct_remaining=0, *args
):
    """
    This is the core function for outbound optimization.
    Provided with a dictionary of attributes for an edge, this section scores each attribute and takes a weighted
    average of attribute weights.  The resultant score ranges from 1 to 10 and describes how good of a fit the
    edge in question is for the given route objectives.
    Parameters
    ----------
    attributes : dictionary
        contains attributes of each edge, including at minimum ['bearing','traveled','frequency','length']
    importance : list
        list of floats containing relative importance of traveled, frequency, previous_bearing,
        home_bearing, and length (in that order).  Should, but does not have to, sum to 1.
    pct_remaining : 0
        dummy variable to facilitate inbound_optimization; should be removed in future iterations
    Returns
    -------
    suitability : float
    """

    # setup mapping for previous bearing
    if "previous_bearing" in attributes.keys():
        try:
            previous_bearing = int(
                np.interp(
                    abs(attributes["bearing"] - attributes["previous_bearing"]),
                    [0, 180],
                    [10, 1],
                )
            )
        except ValueError:
            previous_bearing = 5
    else:
        previous_bearing = 5

    # mapping for bearing to home point
    if "home_bearing" in attributes.keys():
        try:
            home_bearing = int(
                np.interp(
                    abs(attributes["bearing"] - attributes["home_bearing"]),
                    [0, 180],
                    [10, 1],
                )
            )
        except ValueError:
            home_bearing = 5
    else:
        home_bearing = 5

    # setup mapping for previous traversals
    traveled = 1 if attributes["traveled"] else 10
    freq = 10 if attributes["frequency"] > 0 else 1

    # length? scale...
    length = int(np.interp(attributes["length"], [0, 50], [1, 10]))

    # weight all these 1-10 scales by relative importance
    suitability = (
        importance[0] * traveled
        + importance[1] * freq
        + importance[2] * previous_bearing
        + importance[3] * home_bearing
        + importance[4] * length
    )

    return suitability


def evaluate_edges(
    graph,
    route,
    freq={},
    eval_function=lambda x: x["length"],
    pct_remaining=0,
    *args,
    **kwargs
):
    """
    This function evaluates edges based on some evaluation function, returning the id of the best next node.
    Parameters
    ----------
    graph : networkx graph object
        graph containing OSM data for area of interest
    route : list
        list of nodes traversed by a route
    freq : dict
        dictionary of frequency of traversal, where keys are in format (startnode, endnode, 0)
    Returns
    -------
    next_node : int
        id of next best node
    """
    # get all neighbors of current node
    current_node = route[-1]

    # get all adjacent edges
    adj_edges = graph.out_edges(iter([current_node]), data=True)

    # ensure that you cannot revisit the previous nodes
    if len(route) > 1:
        previous_node = route[-2]
        candidate_edges = [x for x in adj_edges if x[1] != previous_node]
        if len(candidate_edges) > 0:
            adj_edges = candidate_edges

    # remove neighbor nodes that are dead ends (only point to one node)(?)
    n = []
    badnodes = []
    goodnodes = []
    for edge in adj_edges:
        edge_end = edge[1]
        nneighbor = [neighbor for neighbor in nx.all_neighbors(graph, edge_end)]
        if len(set(nneighbor)) > 1:
            n.append(edge)
            goodnodes.append(edge)
        else:
            badnodes.append(edge)
            # adj_edges.remove(edge) TODO FIX THIS
    # print(badnode)

    # initialize suitability list
    suitability = []
    n_edge = []

    # for each edge, query edge attributes
    for edge in goodnodes:
        # set dict of attributes
        attributes = edge[-1]

        # add attributes that aren't included by default
        # has it been traveled before on this trip?
        attributes["traveled"] = edge[0:-1] in zip(
            route, route[1:], [0] * (len(route) - 2)
        )

        if (edge[0], edge[1], 0) in freq.keys():
            attributes["frequency"] = freq[(edge[0], edge[1], 0)]
        else:
            attributes["frequency"] = 0

        if len(route) > 1:
            # get bearing of previous segment
            attributes["previous_bearing"] = graph[previous_node][current_node][0][
                "bearing"
            ]
            # get bearing from current node to home
            attributes["home_bearing"] = get_bearing(
                (graph.nodes[current_node]["y"], graph.nodes[current_node]["x"]),
                (graph.nodes[edge[1]]["y"], graph.nodes[edge[1]]["x"]),
            )

        suitability.append(
            eval_function(attributes=attributes, pct_remaining=pct_remaining)
        )
        n_edge.append(edge[1])
    # this is a terrible hack
    # ¯\_(ツ)_/¯
    if not len(n_edge):
        return badnodes[0][1]

    # select index randomly with probability proportional evaulation function
    suitability = [i / sum(suitability) for i in suitability]
    index = np.random.choice(list(range(len(suitability))), 1, suitability)[0].astype(
        np.int64
    )
    # pick edge with the lowest index
    next_node = n_edge[index]

    return next_node


def next_outbound_node(graph, route, freq={}, *args, **kwargs):
    """
    Wrapper for outbound optimization algorithm.
    Parameters
    ----------
    graph : networkx graph object
        graph containing OSM data for area of interest
    route : list
        list of nodes traversed by a route
    freq : dict
        dictionary of frequency of traversal, where keys are in format (startnode, endnode, 0)
    Returns
    -------
    next_node : int
        integer ID of next best node
    """

    # call evaluate edges with inbound node parameters?
    next_node = evaluate_edges(
        graph=graph, route=route, freq=freq, eval_function=outbound_optimization
    )

    return next_node


def next_inbound_node(graph, route, pct_remaining=0, freq={}, *args, **kwargs):
    """
    Wrapper for inbound optimization algorithm.
    Parameters
    ----------
    graph : networkx graph object
        graph containing OSM data for area of interest
    route : list
        list of nodes traversed by a route
    freq : dict
        dictionary of frequency of traversal, where keys are in format (startnode, endnode, 0)
    Returns
    -------
    next_node : int
        integer ID of next best node
    """
    # call evaluate edges with inbound node parameters?
    next_node = evaluate_edges(
        graph=graph,
        route=route,
        freq=freq,
        eval_function=inbound_optimization,
        pct_remaining=pct_remaining,
    )

    return next_node


def inbound_optimization(
    attributes={}, importance=[0.3, 0.3, 0.20, 0.1], pct_remaining=0
):
    """
    This is the core function for inbound optimization.
    Provided with a dictionary of attributes for an edge, this section scores each attribute and takes a weighted
    average of attribute weights.  The resultant score ranges from 1 to 10 and describes how good of a fit the
    edge in question is for the given route objectives.  This value changes depending on what percent of the route
    remains; as the route length reaches the goal length, more importance is placed on selecting edges that take
    the user towards home.
    Parameters
    ----------
    attributes : dictionary
        contains attributes of each edge, including at minimum ['bearing','traveled','frequency','length']
    importance : list
        list of floats containing relative importance of traveled, frequency, previous_bearing,
        and length (in that order).  Should, but does not have to, sum to 1.
    pct_remaining : 0
        what percent of the route goal length is remaining?
    Returns
    -------
    suitability : float
    """

    # setup mapping for previous bearing
    if "previous_bearing" in attributes.keys():
        try:
            previous_bearing = int(
                np.interp(
                    abs(attributes["bearing"] - attributes["previous_bearing"]),
                    [0, 180],
                    [10, 1],
                )
            )
        # we've got a NaN
        except ValueError:
            previous_bearing = 5
    else:
        previous_bearing = 5

    # mapping for bearing to home point
    if "home_bearing" in attributes.keys():
        try:
            home_bearing = int(
                np.interp(
                    abs(attributes["bearing"] - attributes["home_bearing"]),
                    [0, 180],
                    [1, 10],
                )
            )
        except ValueError:
            home_bearing = 5
    else:
        home_bearing = 5

    # setup mapping for previous traversals
    traveled = 1 if attributes["traveled"] else 10
    freq = 10 if attributes["frequency"] > 0 else 1

    # length? scale...
    length = int(np.interp(attributes["length"], [0, 50], [1, 10]))

    # weight all these 1-10 scales by relative importance
    suitability = (
        pct_remaining
        * (
            importance[0] * traveled
            + importance[1] * freq
            + importance[2] * previous_bearing
            + importance[3] * length
        )
        + (1 - pct_remaining) * home_bearing
    )

    return suitability


def no_duplicates(route):
    """
    This function removes duplicate nodes that may be present in a route, ensuring it can be plotted.
    Parameters
    ----------
    route : list
        list of nodes traversed by route, in order
    Returns
    -------
    route : list
        list of nodes traversed by route, in order, with any immediate duplicates removed
    """
    if not len(route):
        return route
    if len(route) > 3:
        try:
            for i in range(len(route) - 2):
                if route[i] == route[i + 1]:
                    del route[i]
        except IndexError:
            return route
    return route


def novelty_score(graph, route, freq={}):
    """
    Returns information about how novel a route is based on a frequency dictionary.
    Parameters
    ----------
    graph : networkx graph object
        graph containing OSM data for area of interest
    route : list
        list of nodes traversed by a route
    freq : dict
        dictionary of frequency of traversal, where keys are in format (startnode, endnode, 0)
    Returns
    -------
    novel_segments : int
        number of total segments on the route that have not been previously traveled
    novel_length : float
        length (in graph length terms, usually meters) of novel road segments
    """
    # iterate through all edges traversed
    novel_segments = 0
    novel_length = 0
    for i in range(len(route) - 1):
        if not (
            (route[i], route[i + 1], 0) in freq.keys()
            or (route[i + 1], route[i], 0) in freq.keys()
        ):
            novel_segments += 1
            novel_length += seg_attribute(graph, route[i], route[i + 1])
    return novel_segments, novel_length


def generate_route(
    lat,
    lon,
    goal_length,
    tolerance=0.5,
    length_unit="km",
    freq={},
    graph=None,
    *args,
    **kwargs
):
    """
    This function generates a loop route of specified length within a tolerance for a given start point.
    This is accomplished by breaking the route creation process into two phases: outbound and inbound.
    For the outbound phase, route segments are chosen based on the maximum outbound_optimization score
    until the total route length has reached one half of the goal length.
    The route then heads for home and begins the inbound phase.
    For the inbound phase, the inbound_optimization
    Parameters
    ----------
    lat : float
        latitude of start point
    lon : float
        longitude of start point
    goal_length : float
        goal length of route
    tolerance : float
        amount of allowable error in route
    length_unit : string
        unit that goal_length and tolerance are specified in - default km
    freq: dictionary
        dictionary of frequency of traversal, where keys are in format (startnode, endnode, 0)
    graph : networkx multidigraph
        graph over which network will be created. needs to be network_type walk.
    Returns
    -------
    route : list
        list of nodes traversed by route
    """
    # initialize timing for route finding
    start_time = time.time()

    # convert km to meters
    if length_unit == "km":
        goal_length = 1000 * goal_length
        tolerance = 1000 * tolerance

    # get graph of area
    # TODO: modify to load from point id?
    if graph:
        streets = graph
    else:
        graph_time = time.time()
    #   streets = graph_from_point((lat, lon), distance=goal_length / 1.75, network_type='walk')

    #     # simplify topology, if possible
    #     try:
    #         simplify_graph(streets)
    #     except Exception:
    #         log('Unable to simplify graph further')
    #         pass
    #     # add length attribute to all nodes
    #     core.add_edge_lengths(streets)
    add_edge_bearings(streets)

    # get start node
    start_node = get_nearest_node(streets, (lat, lon))

    # setup
    route_length = 0
    route = [start_node]

    # outbound portion
    out_time = time.time()
    while route_length < goal_length / 2:

        # select node based on inbound optimization function
        next_node = next_outbound_node(streets, route, freq, *args, **kwargs)

        # augment route length
        if type(next_node) == int:
            route_length += seg_attribute(streets, route[-1], next_node)
            route.append(next_node)
        else:
            # add new node to route
            route.extend(next_node)
            # todo: remove retraced edge(s)

    return_time = time.time()
    # inbound portion (return)
    while route[-1] != start_node and route_length < goal_length + tolerance:
        quick_return_length = route_length + nx.shortest_path_length(
            streets, route[-1], route[0], "length"
        )

        if quick_return_length < goal_length - 0.5 * tolerance:
            # select node based on inbound optimization function
            next_node = next_inbound_node(
                graph=streets,
                route=route,
                freq=freq,
                pct_remaining=route_length / goal_length,
            )

            # augment route length
            if type(next_node) == int:
                route_length += seg_attribute(streets, route[-1], next_node)
                route.append(next_node)
            else:
                # add new node to route
                route.extend(next_node)
                # todo: remove retraced edge(s)

        elif quick_return_length <= goal_length + tolerance:
            next_node = nx.shortest_path(streets, route[-1], route[0], "length")
            route.extend(next_node)
            break

        # prevent function for running forever
        elif route_length > goal_length + tolerance:
            route = [start_node]
            break

    # remove duplicates
    route = no_duplicates(route)
    # get route stats
    novel_segments, novel_length = novelty_score(streets, route, freq)
    return route
