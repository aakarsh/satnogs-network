$(document).ready(function() {
    'use strict';

    $('.selectpicker').selectpicker();

    var horizon_value = $('#horizon').val();
    $('#horizon').slider({
        id: 'horizon_value',
        min: 0,
        max: 90,
        step: 1,
        value: horizon_value});

    var utilization_value = $('#utilization').val();
    $('#utilization').slider({
        id: 'utilization_value',
        min: 0,
        max: 100,
        step: 1,
        value: utilization_value});

    var station_image = $('#station-image').data('existing');
    if(station_image === undefined){
        $('#station-image').fileinput();
    } else {
        $('#station-image').fileinput({
            initialPreview: station_image,
            initialPreviewAsData: true,
        });
    }
});
