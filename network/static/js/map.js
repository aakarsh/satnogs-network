/*global mapboxgl*/

$(document).ready(function() {
    'use strict';

    var mapboxtoken = $('div#map').data('mapboxtoken');
    var stations = $('div#map').data('stations');

    mapboxgl.accessToken = mapboxtoken;

    var map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/pierros/cj8kftshl4zll2slbelhkndwo',
        zoom: 2,
        minZoom: 2,
        center: [10,29]
    });

    map.touchZoomRotate.disableRotation();
    map.dragRotate.disable();
    if (!('ontouchstart' in window)) {
        map.addControl(new mapboxgl.NavigationControl());
    }

    map.on('load', function () {

        map.loadImage('/static/img/online.png', function(error, image) {
            map.addImage('online', image);
        });

        map.loadImage('/static/img/testing.png', function(error, image) {
            map.addImage('testing', image);
        });

        map.loadImage('/static/img/offline.png', function(error, image) {
            map.addImage('offline', image);
        });

        var online_points = {
            'id': 'online-points',
            'type': 'symbol',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'FeatureCollection',
                    'features': []
                }
            },
            'layout': {
                'icon-image': 'online',
                'icon-size': 0.25,
                'icon-allow-overlap': true
            }
        };

        var testing_points = {
            'id': 'testing-points',
            'type': 'symbol',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'FeatureCollection',
                    'features': []
                }
            },
            'layout': {
                'icon-image': 'testing',
                'icon-size': 0.25,
                'icon-allow-overlap': true
            }
        };

        var offline_points = {
            'id': 'offline-points',
            'type': 'symbol',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'FeatureCollection',
                    'features': []
                }
            },
            'layout': {
                'icon-image': 'offline',
                'icon-size': 0.25,
                'icon-allow-overlap': true
            }
        };

        $.ajax({
            url: stations
        }).done(function(data) {
            data.forEach(function(m) {
                if (m.status == 1){
                    testing_points.source.data.features.push({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [
                                parseFloat(m.lng),
                                parseFloat(m.lat)]
                        },
                        'properties': {
                            'description': '<a href="/stations/' + m.id + '">' + m.id + ' - ' + m.name + '</a>',
                        }
                    });
                } else if (m.status == 2) {
                    online_points.source.data.features.push({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [
                                parseFloat(m.lng),
                                parseFloat(m.lat)]
                        },
                        'properties': {
                            'description': '<a href="/stations/' + m.id + '">' + m.id + ' - ' + m.name + '</a>',
                        }
                    });
                } else if (m.status == 0) {
                    offline_points.source.data.features.push({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [
                                parseFloat(m.lng),
                                parseFloat(m.lat)]
                        },
                        'properties': {
                            'description': '<a href="/stations/' + m.id + '">' + m.id + ' - ' + m.name + '</a>',
                        }
                    });
                }
            });

            // Add layers to map
            map.addLayer(testing_points);
            map.addLayer(online_points);
            map.addLayer(offline_points);

            // Set offline layer to invisble
            map.setLayoutProperty(offline_points.id, 'visibility', 'none');
            map.repaint = false;

            // Register keys for toggling visibility of layers
            $(document).bind('keyup', function(event){
                if (event.which == 79) {
                    toggle_layer(map, offline_points);
                } else if (event.which == 78 ) {
                    toggle_layer(map, online_points);
                } else if (event.which == 84 ) {
                    toggle_layer(map, testing_points);
                }
            });

        });
    });

    // Toggle map layer
    function toggle_layer(map, layer) {
        var visibility = map.getLayoutProperty(layer.id, 'visibility');

        //Check if layer is already visible
        if (visibility === 'visible') {
            map.setLayoutProperty(layer.id, 'visibility', 'none');
            layer.className = '';
        } else {
            layer.className = 'active';
            map.setLayoutProperty(layer.id, 'visibility', 'visible');
        }
    }

    // Create a popup, but don't add it to the map yet.
    var popup = new mapboxgl.Popup({
        closeButton: false,
        closeOnClick: true
    });

    map.on('mouseenter', 'online-points', function(e) {
        // Change the cursor style as a UI indicator.
        map.getCanvas().style.cursor = 'pointer';

        // Populate the popup and set its coordinates
        // based on the feature found.
        popup.setLngLat(e.features[0].geometry.coordinates)
            .setHTML(e.features[0].properties.description)
            .addTo(map);
    });

    map.on('mouseenter','testing-points', function(e) {
        // Change the cursor style as a UI indicator.
        map.getCanvas().style.cursor = 'pointer';

        // Populate the popup and set its coordinates
        // based on the feature found.
        popup.setLngLat(e.features[0].geometry.coordinates)
            .setHTML(e.features[0].properties.description)
            .addTo(map);
    });

    map.on('mouseenter','offline-points', function(e) {
        // Change the cursor style as a UI indicator.
        map.getCanvas().style.cursor = 'pointer';

        // Populate the popup and set its coordinates
        // based on the feature found.
        popup.setLngLat(e.features[0].geometry.coordinates)
            .setHTML(e.features[0].properties.description)
            .addTo(map);
    });

    // Resize map for Stations modal
    $('#MapModal').on('shown.bs.modal', function () {
        map.resize();
    });
});
