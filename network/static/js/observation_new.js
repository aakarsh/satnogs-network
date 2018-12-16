/* global moment, d3, Slider, calcPolarPlotSVG */

$(document).ready( function(){
    function select_proper_transmitters(filters, callback){
        var url = '/transmitters/' + filters.satellite + '/';
        if (filters.station) {
            url = '/transmitters/' + filters.satellite + '/' + filters.station + '/';
        }

        $.ajax({
            url: url
        }).done(function(data) {
            var transmitters_options = '';
            var max_good_count = 0;
            var max_good_val = '';
            $.each(data.transmitters, function (i, transmitter) {
                if (max_good_count <= transmitter.good_count) {
                    max_good_count = transmitter.good_count;
                    max_good_val = transmitter.uuid;
                }
                transmitters_options += `
                    <option data-satellite="` + filters.satellite + `"
                            value="` + transmitter.uuid + `"
                            data-success-rate="` + transmitter.success_rate + `"
                            data-content='<div class="transmitter-option">
                                            <div class="transmitter-description">
                                              ` + transmitter.description + ' - ' + (transmitter.downlink_low/1e6).toFixed(3) + ' MHz - ' + transmitter.mode +
                                            `</div>
                                            <div class="progress">
                                              <div class="progress-bar progress-bar-success transmitter-good"
                                                data-toggle="tooltip" data-placement="bottom"
                                                title="` + transmitter.success_rate + '% (' + transmitter.good_count + `) Good"
                                                style="width:` + transmitter.success_rate + `%"></div>
                                              <div class="progress-bar progress-bar-warning transmitter-unvetted"
                                                data-toggle="tooltip" data-placement="bottom"
                                                title="` + transmitter.unvetted_rate + '% (' + transmitter.unvetted_count + `) Unvetted"
                                                style="width:` + transmitter.unvetted_rate + `%"></div>
                                              <div class="progress-bar progress-bar-danger transmitter-bad"
                                                data-toggle="tooltip" data-placement="bottom"
                                                title="` + transmitter.bad_rate + '% (' + transmitter.bad_count + `) Bad"
                                                style="width:` + transmitter.bad_rate + `%"></div>
                                            </div>
                                          </div>'>
                    </option>
                `;
            });
            if (data.transmitters.length > 0) {
                $('#transmitter-selection').html(transmitters_options).prop('disabled', false);
                $('#transmitter-selection').selectpicker('refresh');
                if (filters.value && data.transmitters.findIndex(tr => tr.uuid == filters.value) > -1) {
                    $('#transmitter-selection').selectpicker('val', filters.value);
                } else {
                    $('#transmitter-selection').selectpicker('val', max_good_val);
                }

                $('.tle').hide();
                $('.tle[data-norad="' + filters.satellite + '"]').show();
            } else {
                $('#transmitter-selection').html(`<option id="no-transmitter"
                                                          value="" selected>
                                                    No transmitter available
                                                  </option>`).prop('disabled', true);
                $('#transmitter-selection').selectpicker('refresh');
            }
            if (callback) {
                callback();
            }
        });
    }

    var suggested_data = [];
    var elevation_slider = new Slider('#elevation-filter', { id: 'elevation-filter', min: 0, max: 90, step: 1, range: true, value: [0, 90] });

    function filter_observations() {
        var elmin = elevation_slider.getValue()[0];
        var elmax = elevation_slider.getValue()[1];

        $.each(suggested_data, function(i, station){
            $.each(station.times, function(j, observation){
                var obs_rect = $('#' + observation.id);
                if(observation.elev_max > elmax || observation.elev_max < elmin){
                    observation.selected = false;
                    obs_rect.toggleClass('unselected-obs', true);
                    obs_rect.toggleClass('filtered-out', true);
                    obs_rect.css('cursor', 'default');
                } else {
                    obs_rect.toggleClass('filtered-out', false);
                    obs_rect.css('cursor', 'pointer');
                }
                if(!obs_rect.hasClass('filtered-out') && !observation.selected){
                    station.selectedAll = false;
                }
            });
        });
    }

    elevation_slider.on('slideStop', function() {
        filter_observations();
    });

    $('#select-all-observations').on('click', function(){
        $.each(suggested_data, function(i, station){
            $.each(station.times, function(j, observation){
                if(!$('#' + observation.id).hasClass('filtered-out')){
                    observation.selected = true;
                    $('#' + observation.id).toggleClass('unselected-obs', false);
                }
            });
            station.selectedAll = true;
        });
    });

    $('#select-none-observations').on('click', function(){
        $.each(suggested_data, function(i, station){
            $.each(station.times, function(j, observation){
                observation.selected = false;
                $('#' + observation.id).toggleClass('unselected-obs', true);
            });
            station.selectedAll = false;
        });
    });

    $('#form-obs').on('submit', function() {
        var obs_counter = 0;
        $.each(suggested_data, function(i, station){
            $.each(station.times, function(j, observation){
                if(observation.selected){
                    var start = moment.utc(observation.starting_time).format('YYYY-MM-DD HH:mm:ss.SSS');
                    var end = moment.utc(observation.ending_time).format('YYYY-MM-DD HH:mm:ss.SSS');
                    $('#windows-data').append('<input type="hidden" name="' + obs_counter + '-starting_time" value="' + start + '">');
                    $('#windows-data').append('<input type="hidden" name="' + obs_counter + '-ending_time" value="' + end + '">');
                    $('#windows-data').append('<input type="hidden" name="' + obs_counter + '-station" value="' + station.id + '">');
                    obs_counter += 1;
                }
            });
        });
        $('#windows-data').append('<input type="hidden" name="total" value="' + obs_counter + '">');
    });

    var obs_filter = $('#form-obs').data('obs-filter');
    var obs_filter_dates = $('#form-obs').data('obs-filter-dates');
    var obs_filter_station = $('#form-obs').data('obs-filter-station');
    var obs_filter_satellite = $('#form-obs').data('obs-filter-satellite');
    var obs_filter_transmitter = $('#form-obs').data('obs-filter-transmitter');

    if (!obs_filter_dates) {
        var minStart = $('#datetimepicker-start').data('date-minstart');
        var minEnd = $('#datetimepicker-end').data('date-minend');
        var maxRange = $('#datetimepicker-end').data('date-maxrange');
        var minRange = minEnd - minStart;
        var minStartDate = moment().utc().add(minStart, 'm').format('YYYY-MM-DD HH:mm');
        var maxStartDate = moment().utc().add(minStart + maxRange - minRange, 'm').format('YYYY-MM-DD HH:mm');
        var minEndDate = moment().utc().add(minEnd, 'm').format('YYYY-MM-DD HH:mm');
        var maxEndDate = moment().utc().add(minStart + maxRange, 'm').format('YYYY-MM-DD HH:mm');
        $('#datetimepicker-start').datetimepicker({
            useCurrent: false //https://github.com/Eonasdan/bootstrap-datetimepicker/issues/1075
        });
        $('#datetimepicker-start').data('DateTimePicker').date(minStartDate);
        $('#datetimepicker-start').data('DateTimePicker').minDate(minStartDate);
        $('#datetimepicker-start').data('DateTimePicker').maxDate(maxStartDate);
        $('#datetimepicker-end').datetimepicker({
            useCurrent: false //https://github.com/Eonasdan/bootstrap-datetimepicker/issues/1075
        });
        $('#datetimepicker-end').data('DateTimePicker').date(minEndDate);
        $('#datetimepicker-end').data('DateTimePicker').minDate(minEndDate);
        $('#datetimepicker-end').data('DateTimePicker').maxDate(maxEndDate);
        $('#datetimepicker-start').on('dp.change',function (e) {
            var newMinEndDate = e.date.clone().add(minRange, 'm');
            if ($('#datetimepicker-end').data('DateTimePicker').date() < newMinEndDate) {
                $('#datetimepicker-end').data('DateTimePicker').date(newMinEndDate);
            }
            $('#datetimepicker-end').data('DateTimePicker').minDate(newMinEndDate);
        });
    }

    $('#satellite-selection').on('changed.bs.select', function() {
        var satellite = $(this).find(':selected').data('norad');
        var station = $('#form-obs').data('obs-filter-station');
        select_proper_transmitters({
            satellite: satellite,
            station: station
        });
        $('.calculation-result').hide();
        $('#timeline').empty();
        $('#hover-obs').hide();
        $('#windows-data').empty();
    });

    function sort_stations(a, b){
        if( a.status > b.status){
            return -1;
        } else {
            return a.id - b.id;
        }
    }

    function calculate_observation(){
        $('.calculation-result').show();
        $('#obs-selection-tools').hide();
        $('#timeline').empty();
        $('#hover-obs').hide();
        $('#windows-data').empty();
        var start_time = $('#datetimepicker-start input').val();
        var end_time = $('#datetimepicker-end input').val();
        var transmitter = $('#transmitter-selection').find(':selected').val();
        var satellite = $('#satellite-selection').val();

        var url = '/prediction_windows/' + satellite + '/' + transmitter + '/' + start_time + '/' + end_time + '/';

        if (obs_filter_station) {
            url = '/prediction_windows/' + satellite + '/' + transmitter + '/' + start_time + '/' + end_time + '/' + obs_filter_station + '/';
        }
        if (satellite.length == 0) {
            $('#windows-data').html('<span class="text-danger">You should select a Satellite first.</span>');
            return;
        } else if (transmitter.length == 0) {
            $('#windows-data').html('<span class="text-danger">You should select a Transmitter first.</span>');
            return;
        }

        $.ajax({
            url: url,
            beforeSend: function() { $('#loading').show(); }
        }).done(function(data) {
            $('#loading').hide();
            if (data.length == 1 && data[0].error) {
                var error_msg = data[0].error;
                $('#windows-data').html('<span class="text-danger">' + error_msg + '</span>');
            } else {
                suggested_data = [];
                var dc = 0; // Data counter
                $('#windows-data').empty();
                data.sort(sort_stations);
                $.each(data, function(i, k){
                    var label = k.id + ' - ' + k.name;
                    var times = [];
                    var selectedAll = true;
                    $.each(k.window, function(m, n){
                        if(!n.overlapped || obs_filter_station){
                            var starting_time = moment.utc(n.start).valueOf();
                            var ending_time = moment.utc(n.end).valueOf();
                            var selected = false;
                            if(k.status !== 1 || obs_filter_station){
                                selected = true;
                            }
                            selectedAll = selectedAll && selected;
                            times.push({
                                starting_time: starting_time,
                                ending_time: ending_time,
                                az_start: n.az_start,
                                az_end: n.az_end,
                                elev_max: n.elev_max,
                                tle0: n.tle0,
                                tle1: n.tle1,
                                tle2: n.tle2,
                                selected: selected,
                                id: k.id + '_' + times.length
                            });

                            dc = dc + 1;
                        }
                    });
                    if(times.length > 0){
                        suggested_data.push({
                            label: label,
                            id: k.id,
                            lat: k.lat,
                            lon: k.lng,
                            alt: k.alt,
                            selectedAll: selectedAll,
                            times: times
                        });
                    }
                });

                if (dc > 0) {
                    timeline_init(start_time, end_time, suggested_data);
                } else {
                    var empty_msg = 'No Ground Station available for this observation window';
                    $('#windows-data').html('<span class="text-danger">' + empty_msg + '</span>');
                }
            }
        });
    }

    function timeline_init(start, end, payload){
        var start_time_timeline = moment.utc(start).valueOf();
        var end_time_timeline = moment.utc(end).valueOf();
        var period = end_time_timeline - start_time_timeline;
        var tick_interval = 15;
        var tick_time = d3.time.minutes;

        if(period >= 86400000){
            tick_interval = 2;
            tick_time = d3.time.hours;
        } else if(period >= 43200000){
            tick_interval = 1;
            tick_time = d3.time.hours;
        } else if(period >= 21600000){
            tick_interval = 30;
        }

        $('#hover-obs').hide();
        $('#timeline').empty();

        var chart = d3.timeline()
            .beginning(start_time_timeline)
            .ending(end_time_timeline)
            .mouseout(function () {
                $('#hover-obs').fadeOut(100);
            })
            .hover(function (d, i, datum) {
                if(!$('#' + d.id).hasClass('filtered-out')){
                    var div = $('#hover-obs');
                    div.fadeIn(300);
                    var colors = chart.colors();
                    div.find('.coloredDiv').css('background-color', colors(i));
                    div.find('#name').text(datum.label);
                    div.find('#start-time').text(moment.utc(d.starting_time).format('YYYY-MM-DD HH:mm:ss'));
                    div.find('#end-time').text(moment.utc(d.ending_time).format('YYYY-MM-DD HH:mm:ss'));
                    div.find('#details').text('⤉ ' + d.az_start + '° ⇴ ' + d.elev_max + '° ⤈ ' + d.az_end + '°');
                    const groundstation = {
                        lat: datum.lat,
                        lon: datum.lon,
                        alt: datum.alt
                    };
                    const timeframe = {
                        start: new Date(d.starting_time),
                        end: new Date(d.ending_time)
                    };
                    const polarPlotSVG = calcPolarPlotSVG(timeframe,
                        groundstation,
                        d.tle1,
                        d.tle2);
                    const polarPlotAxes = `
                        <path fill="none" stroke="black" stroke-width="1" d="M 0 -95 v 190 M -95 0 h 190"/>
                        <circle fill="none" stroke="black" cx="0" cy="0" r="30"/>
                        <circle fill="none" stroke="black" cx="0" cy="0" r="60"/>
                        <circle fill="none" stroke="black" cx="0" cy="0" r="90"/>
                        <text x="-4" y="-96">N</text>
                        <text x="-4" y="105">S</text>
                        <text x="96" y="4">E</text>
                        <text x="-106" y="4">W</text>
                    `;
                    $('#polar-plot').html(polarPlotAxes);
                    $('#polar-plot').append(polarPlotSVG);
                }
            })
            .click(function(d, i, datum){
                if ($('rect').length == 1) {
                    return;
                }
                if(Array.isArray(d)){
                    $.each(datum.times, function(i, observation){
                        if(!$('#' + observation.id).hasClass('filtered-out')){
                            observation.selected = !datum.selectedAll;
                            $('#' + observation.id).toggleClass('unselected-obs', !observation.selected);
                        }
                    });
                    datum.selectedAll = !datum.selectedAll;
                } else {
                    var obs = $('#' + d.id);
                    if(!obs.hasClass('filtered-out')){
                        d.selected = !d.selected;
                        obs.toggleClass('unselected-obs', !d.selected);
                        if(!d.selected){
                            datum.selectedAll = false;
                        } else {
                            datum.selectedAll = true;
                            for(var j in datum.times){
                                if(!datum.times[j].selected){
                                    datum.selectedAll = false;
                                    break;
                                }
                            }
                        }
                    }
                }
            })
            .margin({left:140, right:10, top:0, bottom:50})
            .tickFormat({format: d3.time.format.utc('%H:%M'), tickTime: tick_time, tickInterval: tick_interval, tickSize: 6})
            .stack();

        var svg_width = 1140;
        if (screen.width < 1200) { svg_width = 940; }
        if (screen.width < 992) { svg_width = 720; }
        if (screen.width < 768) { svg_width = screen.width - 30; }
        d3.select('#timeline').append('svg').attr('width', svg_width)
            .datum(payload).call(chart);

        $('g').find('rect').css({'stroke': 'black', 'cursor': 'pointer'});

        $.each(suggested_data, function(i, station){
            $.each(station.times, function(j, obs){
                if(!obs.selected){
                    $('#' + obs.id).addClass('unselected-obs');
                }
            });
        });
        $('#schedule-observation').removeAttr('disabled');
        if ($('rect').length > 1) {
            $('#obs-selection-tools').show();
        }
    }

    $('#calculate-observation').click( function(){
        calculate_observation();
    });

    if (obs_filter) {
        select_proper_transmitters({
            satellite: obs_filter_satellite,
            value: obs_filter_transmitter,
            station: obs_filter_station
        }, function(){
            if (obs_filter_dates && obs_filter_station && obs_filter_satellite){
                $('#calculate-observation').hide();
                $('#obs-selection-tools').hide();
                calculate_observation();
            }
        });
    }

    // Hotkeys bindings
    $(document).bind('keyup', function(event){
        if(document.activeElement.tagName != 'INPUT'){
            if (event.which == 67) {
                calculate_observation();
            } else if (event.which == 83) {
                var link_schedule = $('#schedule-observation');
                link_schedule[0].click();
            }
        }
    });
});
