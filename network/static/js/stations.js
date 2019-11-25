/* jshint esversion: 6 */

$(document).ready(function() {
    'use strict';

    $('#stations-online').click(function() {
        $('.station-row:has(\'.label-online\')').toggle();
        $(this).toggleClass('active').blur();
    });

    $('#stations-testing').click(function() {
        $('.station-row:has(\'.label-testing\')').toggle();
        $(this).toggleClass('active').blur();
    });

    $('#stations-offline').click(function() {
        $('.station-row:has(\'.label-offline\')').toggle();
        $(this).toggleClass('active').blur();
    });

    $('#stations-future').click(function() {
        $('.station-row:has(\'.label-future\')').toggle();
        $(this).toggleClass('active').blur();
    });

});
