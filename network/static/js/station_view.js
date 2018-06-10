/* global mapboxgl, polarplot, moment, Slider, calcPolarPlotSVG  */
/* jshint esversion: 6 */

$(document).ready(function() {
    'use strict';

    // Render Station success rate
    var success_rate = $('.gs.progress-bar-success').data('success-rate');
    var percentagerest = $('.gs.progress-bar-danger').data('percentagerest');
    $('.gs.progress-bar-success').css('width', success_rate + '%');
    $('.gs.progress-bar-danger').css('width', percentagerest + '%');

    // Reading data for station
    var station_info = $('#station-info').data();

    // Confirm station deletion
    var message = 'Do you really want to delete this Ground Station?';
    var actions = $('#station-delete');
    if (actions.length) {
        actions[0].addEventListener('click', function(e) {
            if (! confirm(message)) {
                e.preventDefault();
            }
        });
    }

    // Init the map
    var mapboxtoken = $('div#map-station').data('mapboxtoken');
    mapboxgl.accessToken = mapboxtoken;
    var map = new mapboxgl.Map({
        container: 'map-station',
        style: 'mapbox://styles/pierros/cj8kftshl4zll2slbelhkndwo',
        zoom: 5,
        minZoom: 2,
        center: [parseFloat(station_info.lng),parseFloat(station_info.lat)]
    });
    map.addControl(new mapboxgl.NavigationControl());
    map.on('load', function () {
        map.loadImage('/static/img/pin.png', function(error, image) {
            map.addImage('pin', image);
        });
        var map_points = {
            'id': 'points',
            'type': 'symbol',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'FeatureCollection',
                    'features': [{
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [
                                parseFloat(station_info.lng),
                                parseFloat(station_info.lat)]
                        },
                        'properties': {
                            'description': '<a href="/stations/' + station_info.id + '">' + station_info.id + ' - ' + station_info.name + '</a>',
                            'icon': 'circle'
                        }
                    }]
                }
            },
            'layout': {
                'icon-image': 'pin',
                'icon-size': 0.4,
                'icon-allow-overlap': true
            }
        };
        map.addLayer(map_points);
        map.repaint = true;
    });

    // Slider filters for pass predictions
    var success_slider = new Slider('#success-filter', { id: 'success-filter', min: 0, max: 100, step: 5, range: true, value: [0, 100] });
    var elevation_slider = new Slider('#elevation-filter', { id: 'elevation-filter', min: 0, max: 90, step: 1, range: true, value: [0, 90] });
    var overlap_slider = new Slider('#overlap-filter', { id: 'overlap-filter', min: 0, max: 100, step: 1, range: true, value: [0, 100] });

    function filter_passes() {
        var elmin = elevation_slider.getValue()[0];
        var elmax = elevation_slider.getValue()[1];
        var sumin = success_slider.getValue()[0];
        var sumax = success_slider.getValue()[1];
        var ovmin = overlap_slider.getValue()[0];
        var ovmax = overlap_slider.getValue()[1];

        $('tr.pass').each(function(k, v) {
            var passmax = $(v).find('td.max-elevation').data('max');
            var success = $(v).find('td.success-rate').data('suc');
            var over = $(v).data('overlap');
            var visibility = true;
            if ( passmax < elmin || passmax > elmax ) {
                visibility = false;
            }
            if ( success < sumin || success > sumax ) {
                visibility = false;
            }
            if ( over < ovmin || over > ovmax ) {
                visibility = false;
            }
            if (visibility) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });

        // Update count of predictions visible
        var filtered_count = $('tr.pass:visible').length;
        $('#prediction_results_count').html(filtered_count);
    }

    elevation_slider.on('slideStop', function() {
        filter_passes();
    });

    success_slider.on('slideStop', function() {
        filter_passes();
    });

    overlap_slider.on('slideStop', function() {
        filter_passes();
    });

    // Filters
    $('#antenna-filter').submit(function () {
        var the_form = $(this);

        the_form.find('input[type="checkbox"]').each( function () {
            var the_checkbox = $(this);

            if( the_checkbox.is(':checked') === true ) {
                the_checkbox.attr('value','1');
            } else {
                the_checkbox.prop('checked',true);
                // Check the checkbox but change it's value to 0
                the_checkbox.attr('value','0');
            }
        });
    });

    $('#antenna-filter input[type=checkbox]').change(function() {
        $('#antenna-filter').submit();
    });

    // Function for overlap check
    function check_overlap(jobs, passstart, passend) {
        var overlap = 0;
        for (var i in jobs) {
            var job_start = moment(jobs[i].start);
            var job_end = moment(jobs[i].end);
            // If scheduled ends before predicion, skip!
            if (job_end.isBefore(passstart)) {continue;}

            // If scheduled starts after prediction, skip!
            if (job_start.isAfter(passend)) {continue;}

            // If scheduled start is in prediction, calculate overlap
            if (job_start.isBetween(passstart, passend, null, '[]')) {
                overlap = Math.round((job_start.diff(passstart) / passend.diff(passstart)) * 100);
                overlap = 100 - overlap;
            }

            // If scheduled end is in prediction, calculate overlap
            if (job_end.isBetween(passstart, passend, null, '[]')) {
                overlap = Math.round((passend.diff(job_end) / passend.diff(passstart)) * 100);
                overlap = 100 - overlap;
            }

            // If prediction is within job, total overlap
            if (job_start.isBefore(passstart) && job_end.isAfter(passend)) {
                overlap = 100;
            }
        }
        return overlap;
    }

    // Pass predictions loading
    $('#loading-image').show();
    $.ajax({
        url: '/pass_predictions/' + $('#station-info').attr('data-id') + '/',
        cache: false,
        success: function(data){
            var len = data.nextpasses.length - 1;
            var new_obs = $('#station-info').attr('data-new-obs');
            var station = $('#station-info').attr('data-id');
            var can_schedule =  $('#station-info').data('schedule');

            var jobs = [];

            $.ajax({
                url: '/api/jobs/?ground_station=' + $('#station-info').attr('data-id'),
                cache: false,
                async: false,
                success: function(data){
                    jobs = data;
                },
                complete: function(){
                }
            });

            for (var i = 0; i <= len; i++) {
                var schedulable = data.nextpasses[i].valid && can_schedule;
                var json_polar_data = JSON.stringify(data.nextpasses[i].polar_data);
                var tr = moment(data.nextpasses[i].tr).format('YYYY/MM/DD HH:mm');
                var ts = moment(data.nextpasses[i].ts).format('YYYY/MM/DD HH:mm');
                var tr_display_date = moment(data.nextpasses[i].tr).format('YYYY-MM-DD');
                var tr_display_time = moment(data.nextpasses[i].tr).format('HH:mm');
                var ts_display_date = moment(data.nextpasses[i].ts).format('YYYY-MM-DD');
                var ts_display_time = moment(data.nextpasses[i].ts).format('HH:mm');
                var tr_svg = moment.utc(data.nextpasses[i].tr).format();
                var ts_svg = moment.utc(data.nextpasses[i].ts).format();

                var overlap_style = null;
                var overlap = check_overlap(jobs, moment.utc(data.nextpasses[i].tr), moment.utc(data.nextpasses[i].ts));
                if (overlap >= 50) {
                    overlap_style = 'overlap';
                }
                $('#pass_predictions').append(`
                  <tr class="pass ${overlap_style}" data-overlap="${overlap}">
                    <td class="success-rate" data-suc="${data.nextpasses[i].success_rate}">
                      <a href="#" data-toggle="modal" data-target="#SatelliteModal" data-id="${data.nextpasses[i].norad_cat_id}">
                        ${data.nextpasses[i].norad_cat_id} - ${data.nextpasses[i].name}
                      </a>
                      <div class="progress satellite-success">
                        <div class="progress-bar progress-bar-success" style="width: ${data.nextpasses[i].success_rate}%"
                             data-toggle="tooltip" data-placement="bottom" title="${data.nextpasses[i].success_rate}% (${data.nextpasses[i].good_count}) Good">
                          <span class="sr-only">${data.nextpasses[i].success_rate}% Good</span>
                        </div>
                        <div class="progress-bar progress-bar-warning" style="width: ${data.nextpasses[i].unknown_rate}%"
                             data-toggle="tooltip" data-placement="bottom" title="${data.nextpasses[i].unknown_rate}% (${data.nextpasses[i].unknown_count}) Unknown">
                          <span class="sr-only">${data.nextpasses[i].unknown_rate}% Unknown</span>
                        </div>
                        <div class="progress-bar progress-bar-danger" style="width: ${data.nextpasses[i].bad_rate}%"
                             data-toggle="tooltip" data-placement="bottom" title="${data.nextpasses[i].bad_rate}% (${data.nextpasses[i].bad_count}) Bad">
                          <span class="sr-only">${data.nextpasses[i].bad_rate}% Bad</span>
                        </div>
                      </div>
                    </td>
                    <td class="pass-datetime">
                      <span class="pass-time">${tr_display_time}</span>
                      <span class="pass-date">${tr_display_date}</span>
                    </td>
                    <td class="pass-datetime">
                      <span class="pass-time">${ts_display_time}</span>
                      <span class="pass-date">${ts_display_date}</span>
                    </td>
                    <td class="max-elevation" data-max="${data.nextpasses[i].altt}">
                      <span class="polar-deg" aria-hidden="true"
                            data-toggle="tooltip" data-placement="left"
                            title="AOS degrees">
                          <span class="lightgreen">⤉</span>${data.nextpasses[i].azr}°
                      </span>
                      <span class="polar-deg" aria-hidden="true"
                            data-toggle="tooltip" data-placement="left"
                            title="TCA degrees">
                          ⇴${data.nextpasses[i].altt}°<br>
                      </span>
                      <span class="polar-deg" aria-hidden="true"
                            data-toggle="tooltip" data-placement="left"
                            title="LOS degrees">
                          <span class="red">⤈</span>${data.nextpasses[i].azs}°
                      </span>
                    </td>
                    <td>
                      <div id="polar_plot">
                        <svg
                            xmlns="http://www.w3.org/2000/svg" version="1.1"
                            id="polar${i}"
                            data-tle1="${data.nextpasses[i].tle1}"
                            data-tle2="${data.nextpasses[i].tle2}"
                            data-timeframe-start="${tr_svg}"
                            data-timeframe-end="${ts_svg}"
                            data-groundstation-lat="${data.ground_station.lat}"
                            data-groundstation-lon="${data.ground_station.lng}"
                            data-groundstation-alt="${data.ground_station.alt}"
                            width="120px" height="120px"
                            viewBox="-110 -110 220 220"
                            overflow="hidden">
                            <path
                                fill="none" stroke="black" stroke-width="1"
                                d="M 0 -95 v 190 M -95 0 h 190"
                                />
                            <circle
                                fill="none" stroke="black"
                                cx="0" cy="0" r="30"
                                />
                            <circle
                                fill="none" stroke="black"
                                cx="0" cy="0" r="60"
                                />
                            <circle
                                fill="none" stroke="black"
                                cx="0" cy="0" r="90"
                                />
                            <text x="-4" y="-96">
                                N
                            </text>
                            <text x="-4" y="105">
                                S
                            </text>
                            <text x="96" y="4">
                                E
                            </text>
                            <text x="-106" y="4">
                                W
                            </text>
                        </svg>
                      </div>
                      <!-- <canvas class="polar-plot" width="100" height="100" data-points="${json_polar_data}"></canvas> -->
                    </td>
                    <td class="pass-schedule">
                      ${overlap ? `<div class="overlap-ribbon" aria-hidden="true"
                                        data-toggle="tooltip" data-placement="bottom"
                                        title="A scheduled observation overlaps">
                                        ${overlap}% overlap</div><br>
                      ` : `
                      `}
                      ${schedulable ? `<a href="${new_obs}?norad=${data.nextpasses[i].norad_cat_id}&ground_station=${station}&start_date=${tr}&end_date=${ts}"
                           class="btn btn-default schedulable"
                           target="_blank">
                           schedule
                           <span class="glyphicon glyphicon-new-window" aria-hidden="true"></span>
                         </a>
                      ` : `
                        <a class="btn btn-default" disabled>
                          schedule
                          <span class="glyphicon glyphicon-new-window" aria-hidden="true"></span>
                        </a>
                      `}
                    </td>
                  </tr>
                `);

                // Draw orbit in polar plot
                var tleLine1 = $('svg#polar' + i.toString()).data('tle1');
                var tleLine2 = $('svg#polar' + i.toString()).data('tle2');

                var timeframe = {
                    start: new Date($('svg#polar' + i.toString()).data('timeframe-start')),
                    end: new Date($('svg#polar' + i.toString()).data('timeframe-end'))
                };

                var groundstation = {
                    lon: $('svg#polar' + i.toString()).data('groundstation-lon'),
                    lat: $('svg#polar' + i.toString()).data('groundstation-lat'),
                    alt: $('svg#polar' + i.toString()).data('groundstation-alt')
                };

                const polarPlotSVG = calcPolarPlotSVG(timeframe,
                    groundstation,
                    tleLine1,
                    tleLine2);

                $('svg#polar' + i.toString()).append(polarPlotSVG);
            }
            //polarplot();

            // Show predicion results count
            $('#prediction_results').show();
            $('#prediction_results_count').html(data.nextpasses.length);
        },
        complete: function(){
            $('#loading-image').hide();
        }
    });

    // Open all visible predictions for scheduling
    $('#open-all').click(function() {
        $('tr.pass:visible a.schedulable').each(function() {
            window.open($(this).attr('href'));
        });
    });

    // Expand Station image
    $('.img-expand').click(function() {
        $('#modal-lightbox').show('slow');
    });
    $('#modal-lightbox .close').click(function() {
        $('#modal-lightbox').hide('slow');
    });
});
