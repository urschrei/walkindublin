import mapboxgl from 'mapbox-gl';
// import nearestPoint from '@turf/nearest-point'
// import {
//     point,
//     featureCollection
// } from '@turf/helpers'
import 'bootstrap';
import './style.scss'

import jQuery from 'jquery';
var $ = jQuery;

mapboxgl.accessToken = 'pk.eyJ1IjoidXJzY2hyZWkiLCJhIjoiY2pubHJsaGZjMWl1dzNrbzM3eDBuNzN3eiJ9.5xEWTiavcSRbv7LYZoAmUg';

const dbounds = [
    [-6.3868511, 53.2990801],
    [-6.1188691, 53.4100279]
];

const map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/light-v9',
    zoom: 13.0,
    minZoom: 11,
    center: {
        lng: -6.258955,
        lat: 53.347311
    },
    bounds: dbounds
});

const routes_polygons = {
    "id": "routes_polygons",
    "type": "line",
    "source": "routes",
    "minzoom": 7,
    "paint": {
        "line-width": 3.0,
        "line-color": "red",
        "line-opacity": 0.2
    }
}

const dataSources = {
    "routes": {
        "url": "static/trunc.geojson",
        "polygon_layer": routes_polygons
    }
};

// Add GeoJSON layers to map, and make them available to turf
async function getRoutes(m) {
    var promises = [];
    promises.push(
        Object.keys(dataSources).forEach(function(item) {
            fetch(dataSources[item]["url"])
                .then(response => response.json())
                .then(data => {
                    // check if Source exists, add if not
                    if (!map.getSource(item)) {
                        m.addSource(item, {
                                "type": "geojson",
                                "data": data
                            })
                            .addLayer(dataSources[item]["polygon_layer"]);
                    } else {
                        m.getSource(item).setData(data);
                    }
                })
        })
    );
    await Promise.all(promises);
}

map.on('load', function() {
    // getBranches(this);
    if ("geolocation" in navigator) {
        // do nothing
    } else {
        $('#locate').fadeOut(500);
    }
});

// ['routes'].forEach(function(chain) {
//     // When a click event occurs on a feature in the point layer, open a popup at the
//     // location of the feature, with post code and authority text from its properties.
//     map.on('click', chain + '_points', function(e) {
//         var coordinates = e.features[0].geometry.coordinates.slice();
//         var description = `<p>Post Code: ${e.features[0].properties.PostCode} in ${e.features[0].properties.LocalAuthorityName}</p><p>FHRS Rating, Feb 2020: ${e.features[0].properties.RatingValue}</p>`;

//         // Ensure that if the map is zoomed out such that multiple
//         // copies of the feature are visible, the popup appears
//         // over the copy being pointed to.
//         while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
//             coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
//         }

//         new mapboxgl.Popup()
//             .setLngLat(coordinates)
//             .setHTML(description)
//             .addTo(map);
//     });

//     // Change the cursor to a pointer when the mouse is over the places layer
//     map.on('mouseenter', chain + '_points', function() {
//         map.getCanvas().style.cursor = 'pointer';
//     });

//     // Change it back to a pointer when it leaves
//     map.on('mouseleave', chain + '_points', function() {
//         map.getCanvas().style.cursor = '';
//     });
// })

// Locate nearest chain if geolocation is successful
function glSuccess(position) {
    // var p = point([position.coords.longitude, position.coords.latitude]);
    // var nearest = nearestPoint(p, gdata[active_chain]);
    map.flyTo({
        center: position.coords,
        zoom: 13,
        curve: 1,
        essential: true
    });
}

// If we can't geolocate for some reason
function glError() {
    $(".invalid-feedback").text("We Couldn't geolocate you!");
}

$("#locate").click(function() {
    var pc = {
        coords: {
            latitude: 53.331953,
            longitude: -6.271830
        }
    };
    $.post("/streets", JSON.stringify(pc))
        .done(function(data) {
            map.fitBounds(data);
            getRoutes(map);
            // tell map to load new geojson layer
        })
        .fail(function() {
            $(".invalid-feedback").text("Hmm. Something went wrong");
        });
});
