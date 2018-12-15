/* jshint esversion: 6 */

$(document).ready(function() {
    'use strict';

    $('.stations-totals .label-offline').html($('span.station.label-offline').length);
    $('.stations-totals .label-future').html($('span.station.label-future').length);

    $('.station-row:has(\'.label-offline\')').hide();
    $('.station-row:has(\'.label-future\')').hide();

    $('#stations-online').click(function() {
        $('.station-row:has(\'.label-online\')').toggle();
        $(this).toggleClass('active');
    });

    $('#stations-testing').click(function() {
        $('.station-row:has(\'.label-testing\')').toggle();
        $(this).toggleClass('active');
    });

    $('#stations-offline').click(function() {
        $('.station-row:has(\'.label-offline\')').toggle();
        $(this).toggleClass('active');
    });

    $('#stations-future').click(function() {
        $('.station-row:has(\'.label-future\')').toggle();
        $(this).toggleClass('active');
    });

});
