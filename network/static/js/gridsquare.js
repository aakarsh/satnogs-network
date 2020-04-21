/* This script calculates the grid locator based on the Maidenhead
 * Locator System.  It references the longitude and latitude fields
 * in the Station Add/Edit view, calculating the grid square and adding
 * that to the location field if both lat/lon values exist and are
 * valid.
*/

$(document).ready(function() {
    'use strict';

    function gridsquare() {
        var FIELD_IDENTIFIERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'];

        // starting points, the fields from the Station form
        var latitude = $('#lat').val();
        var longitude = $('#lng').val();

        // this gets called any time one of the two lat/long fields
        // have been changed. We only need to do the work if both
        // fields have been entered with a proper entry, otherwise
        // skip the cycles
        if ((latitude !== '') &&
                (latitude <= 90) &&
                (latitude >= -90) &&
                (longitude !== '') &&
                (longitude <= 180) &&
                (longitude >= -180)) {

            // to figure out the individual grid identifiers we make a mess
            // of the longitude and latitude
            var working_lon = ((+longitude + 180) % 20);
            var lon_field = FIELD_IDENTIFIERS[Math.floor((+longitude + 180) / 20)];
            var lon_square = Math.floor(working_lon / 2);
            working_lon = Math.floor((working_lon % 2) * 12);
            var lon_subsquare = FIELD_IDENTIFIERS[working_lon];

            var working_lat = ((+latitude + 90) % 10);
            var lat_field = FIELD_IDENTIFIERS[Math.floor((+latitude + 90) / 10)];
            var lat_square = Math.floor(working_lat);
            working_lat = Math.floor((working_lat - Math.floor(working_lat)) * 24);
            var lat_subsquare = FIELD_IDENTIFIERS[working_lat];

            // write the result, like EM69uf, to qthlocator field
            var qthlocator = $('#qthlocator');
            qthlocator.val('' + lon_field + lat_field + lon_square + lat_square +
                lon_subsquare.toLowerCase() + lat_subsquare.toLowerCase());
        }
    }

    $('input#lat').change(function() {
        gridsquare();
    });

    $('input#lng').change(function() {
        gridsquare();
    });

    gridsquare();
});
