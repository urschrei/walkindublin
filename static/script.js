import mapboxgl from 'mapbox-gl';
// import nearestPoint from '@turf/nearest-point'
import buffer from '@turf/buffer'
import {
//     point,
    featureCollection
} from '@turf/helpers'
import 'bootstrap';
import './style.scss'

import jQuery from 'jquery';
var $ = jQuery;

mapboxgl.accessToken = 'pk.eyJ1IjoidXJzY2hyZWkiLCJhIjoiY2s4Z2NseHRnMDA2cTNucGE4Z2U0ZTcwMyJ9.WKza9QLjoub4Z48taKuQ-Q';

const dbounds = [
    [-6.3868511, 53.2990801],
    [-6.1188691, 53.4100279]
];

const map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/urschrei/cjtg2ckwn0ggj1gpxzclgj7eu',
    zoom: 13.0,
    minZoom: 11,
    center: {
        lng: -6.258955,
        lat: 53.347311
    },
    bounds: dbounds
});

const point_style = {
    "id": "start_point_style",
    "type": "circle",
    "source": "point",
    "paint": {
        "circle-color": "red",
        "circle-stroke-color": "#5b5b5b",
        "circle-stroke-width": 2.5,
        "circle-opacity": 0.5,
        "circle-radius": 30.0,
        "circle-pitch-alignment": "map"
    }
}

const routes_lines = {
    "id": "routes_lines",
    "type": "line",
    "source": "routes",
    "minzoom": 7,
    "paint": {
        "line-width": 3.0,
        "line-color": "#008080",
        "line-opacity": 0.75
    }
}

const routes_fill = {
    "id": "routes_fill_extrusion",
    "type": "fill-extrusion",
    "source": "routes",
    "minzoom": 7,
    "paint": {
        "fill-extrusion-color": "#FF0000",
        "fill-extrusion-height": 10,
        "fill-extrusion-opacity": 0.9
    },
    "light": {
        "intensity": 1.0
    }
}

const dataSources = {
    "routes": {
        "line_layer": routes_lines,
        "fill_layer": routes_fill
    }
};

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


$("#allstreets").click(function() {
    navigator.geolocation.getCurrentPosition(glStreetsSuccess, glError, {
        enableHighAccuracy: true,
        timeout: 2500
    });
    // var pc = {"coords": {"latitude": 53.3318, "longitude": -6.2717}};
    // glStreetsSuccess(pc);

});

$("#buildwalk").click(function() {
    navigator.geolocation.getCurrentPosition(glWalkSuccess, glError, {
        enableHighAccuracy: true,
        timeout: 2500
    });
    // var pc = {"coords": {"latitude": 53.3318, "longitude": -6.2717}};
    // glWalkSuccess(pc);
})

// If we can't geolocate for some reason
function glError() {
    $("#feedback").addClass("is-invalid");
    $("#feedback").text("We couldn't geolocate you!");
}

function glStreetsSuccess(pc) {
    var crd = {
        "lon": pc.coords.longitude,
        "lat": pc.coords.latitude
    };
    $("#allstreets").attr('value', 'Wait…').text('Wait…');
    $.post("/streets", JSON.stringify(crd))
        .done(function(data) {
            addToMap(pc, data);
            $("#allstreets").attr('value', 'Show All Streets').text("Show All Streets");
        })
        .fail(function(data) {
            $("#feedback").text(data.responseJSON.message);
        });
}

function glWalkSuccess(pc) {
    var crd = {
        "lon": pc.coords.longitude,
        "lat": pc.coords.latitude
    };
    $("#buildwalk").attr('value', 'Wait…').text('Wait…');
    $.post("/route", JSON.stringify(crd))
        .done(function(data) {
            addToMap(pc, data);
            $("#buildwalk").attr('value', 'Show All Streets').text("Show All Streets");
        })
        .fail(function(data) {
            $("#feedback").addClass("is-invalid");
            $("#feedback").text(data.responseJSON.message);
        });
}

function addToMap(pc, data) {
    var geojson = {
        'type': 'FeatureCollection',
        'features': [{
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [pc.coords.longitude, pc.coords.latitude]
            }
        }]
    };
    if (!map.getSource("point")) {
        map.addSource('point', {
            'type': 'geojson',
            'data': geojson
        });
        map.addLayer(point_style);
    } else {
        map.getSource("point").setData(geojson);
    }
    // check if Source exists, add if not
    // first, build a Turf featureCollection, so we can buffer it
    var fc = featureCollection(data[0]['features']);
    if (!map.getSource("routes")) {
        map.addSource("routes", {
                "type": "geojson",
                "data": buffer(fc, 0.001)
            })
    } else {
        map.getSource("routes").setData(buffer(fc, 0.001));
    }
    if (!map.getLayer(dataSources["routes"]["fill_layer"])) {
        map.addLayer(dataSources["routes"]["fill_layer"]);
    }
    map.flyTo({
        bearing: Math.floor(Math.random() * (360 - 1 + 1)) + 1,
        pitch: Math.floor(Math.random() * (70.0 - 1.0 + 1.0)) + 50.0,
        center: [pc.coords.longitude, pc.coords.latitude],
        curve: 1,
        zoom: 16
    });
    $("#feedback").text("");
}
