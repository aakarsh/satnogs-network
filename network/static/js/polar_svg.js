/* global satellite moment */
/* exported calcPolarPlotSVG */

/**
 * @typedef {Object} timeframe
 * @property {Date} start - Start of the observation.
 * @property {Date} end - End of the observation.
 */

/**
 * Returns a polar plot of a pass at the given groundstation as SVG in a string.
 *
 * @param {timeframe} Timeframe of the oberservation.
 * @param {groundstation} The observing groundstation.
 * @param {tleLine1} TLE line 1 of the observed satellite.
 * @param {tleLine2} TLE line 2 of the observed satellite.
 */
function calcPolarPlotSVG(timeframe, groundstation, tleLine1, tleLine2) {
    'use strict';

    const pi = Math.PI;
    const deg2rad = pi / 180.0;
    const rad2deg = 180 / pi;

    // Get the observer at lat/lon in RADIANS, altitude in km above ground (NOTE: BUG, should be elevation?)
    var observerGd = {
        longitude: groundstation.lon * deg2rad,
        latitude: groundstation.lat * deg2rad,
        height: groundstation.alt / 1000
    };

    var polarGetXY = function(az, el) {
        var ret = new Object();
        ret.x = (90 - el) * Math.sin(az * deg2rad);
        ret.y = (el - 90) * Math.cos(az * deg2rad);
        return ret;
    };

    var svg_namespace = 'http://www.w3.org/2000/svg';
    var polarOrbit = document.createElementNS(svg_namespace, 'path');
    polarOrbit.setAttributeNS(null, 'fill', 'none');
    polarOrbit.setAttributeNS(null, 'stroke', 'blue');
    polarOrbit.setAttributeNS(null, 'stroke-opacity', '1.0');
    polarOrbit.setAttributeNS(null, 'stroke-width', '3');

    // Initialize the satellite record
    var satrec = satellite.twoline2satrec(tleLine1, tleLine2);

    function polarGetAzEl(t) {
        var positionAndVelocity = satellite.propagate(satrec, t.toDate());

        var gmst = satellite.gstime(t.toDate());
        var positionEci   = positionAndVelocity.position;
        var positionEcf   = satellite.eciToEcf(positionEci, gmst);

        var lookAngles    = satellite.ecfToLookAngles(observerGd, positionEcf);

        return {'azimuth':   lookAngles.azimuth * rad2deg,
            'elevation': lookAngles.elevation * rad2deg};
    }


    // Draw the orbit pass on the polar az/el plot
    var g = '';
    for (var t = moment(timeframe.start); t < moment(timeframe.end); t.add(20, 's')) {
        var sky_position = polarGetAzEl(t);
        var coord = polarGetXY(sky_position.azimuth, sky_position.elevation);

        if (g == '') {
            // Start of line
            g += 'M';
        } else {
            // Continue line
            g += ' L';
        }
        g += coord.x + ' ' + coord.y;
    }
    polarOrbit.setAttribute('d', g);

    // Draw observation start
    var point_start = document.createElementNS(svg_namespace, 'circle');
    point_start.setAttributeNS(null, 'fill', 'lightgreen');
    point_start.setAttributeNS(null, 'stroke', 'black');
    point_start.setAttributeNS(null, 'stroke-width', '1');

    var sky_position_rise = polarGetAzEl(moment(timeframe.start));
    var coord_rise = polarGetXY(sky_position_rise.azimuth, sky_position_rise.elevation);

    point_start.setAttribute('cx', coord_rise.x);
    point_start.setAttribute('cy', coord_rise.y);
    point_start.setAttribute('r', 7);

    // Draw oberservation end
    var point_end = document.createElementNS(svg_namespace, 'circle');
    point_end.setAttributeNS(null, 'fill', 'red');
    point_end.setAttributeNS(null, 'stroke', 'black');
    point_end.setAttributeNS(null, 'stroke-width', '1');

    var sky_position_set = polarGetAzEl(moment(timeframe.end));
    var coord_set = polarGetXY(sky_position_set.azimuth, sky_position_set.elevation);

    point_end.setAttribute('cx', coord_set.x);
    point_end.setAttribute('cy', coord_set.y);
    point_end.setAttribute('r', 7);


    return [polarOrbit, point_start, point_end];
}
