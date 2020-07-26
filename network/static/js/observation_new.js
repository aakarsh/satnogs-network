/* global moment, d3, Slider, calcPolarPlotSVG */

$(document).ready( function(){
    $('#advanced-options').click(function(){
        if($('button span').hasClass('glyphicon-chevron-down')) {
            $(this).html('<span class="glyphicon glyphicon-chevron-up"></span> Hide Advanced Options');
        } else {
            $(this).html('<span class="glyphicon glyphicon-chevron-down"></span> Show Advanced Options');
        }
    });

    $('#default-horizon').click(function() {
        $('#min-horizon').slider('destroy');
        $('#min-horizon').remove();
    });

    $('#custom-horizon').click(function() {
        $('#horizon-status').append('<input type="hidden" name="min-horizon" id="min-horizon"/>');
        $('#min-horizon').slider({
            id: 'min-horizon-slider',
            min: 0,
            max: 90,
            step: 1,
            value: 0,
            ticks: [0, 30, 60, 90],
            ticks_labels: ['0', '30', '60', '90']
        });
    });

    function create_station_option(station){
        return `
            <option value="` + station.id + `"
                    data-content='<div class="station-option">
                                    <span class="label label-` + station.status_display.toLowerCase() +`">
                                      ` + station.id +
                                    `</span>
                                    <span class="station-description">
                                      ` + station.name +
                                    `</span>
                                  </div>'>
            </option>
        `;
    }

    function select_proper_stations(filters, callback){
        var url = '/scheduling_stations/';
        var data = {'transmitter': filters.transmitter};
        if (filters.station) {
            data.station_id = filters.station;
        }
        $.ajax({
            type: 'POST',
            url: url,
            data: data,
            dataType: 'json',
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', $('[name="csrfmiddlewaretoken"]').val());
                $('#station-field').hide();
                $('#station-field-loading').show();
            }
        }).done(function(data) {
            if (data.length == 1 && data[0].error) {
                $('#station-selection').html(`<option id="no-station"
                                                          value="" selected>
                                                    No station available
                                                  </option>`).prop('disabled', true);
                $('#station-selection').selectpicker('refresh');
            } else if (data.stations.length > 0) {
                var stations_options = '';
                if (filters.station) {
                    if (data.stations.findIndex(st => st.id == filters.station) > -1) {
                        var station = data.stations.find(st => st.id == filters.station);
                        stations_options = create_station_option(station);
                        $('#station-selection').html(stations_options);
                        $('#station-selection').selectpicker('val', filters.station);
                        $('#station-selection').selectpicker('refresh');
                    } else {
                        $('#station-selection').html(`<option id="no-station"
                                                                  value="" selected>
                                                            Selected station not available
                                                          </option>`).prop('disabled', true);
                        $('#station-selection').selectpicker('refresh');
                    }
                } else {
                    $.each(data.stations, function (i, station) {
                        stations_options += create_station_option(station);
                    });
                    $('#station-selection').html(stations_options).prop('disabled', false);
                    $('#station-selection').selectpicker('refresh');
                    $('#station-selection').selectpicker('selectAll');
                }
            } else {
                $('#station-selection').html(`<option id="no-station"
                                                          value="" selected>
                                                    No station available
                                                  </option>`).prop('disabled', true);
                $('#station-selection').selectpicker('refresh');
            }
            if (callback) {
                callback();
            }
            $('#station-field-loading').hide();
            $('#station-field').show();
        });
    }

    function create_transmitter_option(satellite, transmitter){
        return `
            <option data-satellite="` + satellite + `"
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
                                      <div class="progress-bar progress-bar-warning transmitter-unknown"
                                        data-toggle="tooltip" data-placement="bottom"
                                        title="` + transmitter.unknown_rate + '% (' + transmitter.unknown_count + `) Unknown"
                                        style="width:` + transmitter.unknown_rate + `%"></div>
                                      <div class="progress-bar progress-bar-danger transmitter-bad"
                                        data-toggle="tooltip" data-placement="bottom"
                                        title="` + transmitter.bad_rate + '% (' + transmitter.bad_count + `) Bad"
                                        style="width:` + transmitter.bad_rate + `%"></div>
                                      <div class="progress-bar progress-bar-info transmitter-future"
                                        data-toggle="tooltip" data-placement="bottom"
                                        title="` + transmitter.future_rate + '% (' + transmitter.future_count + `) Future"
                                        style="width:` + transmitter.future_rate + `%"></div>
                                    </div>
                                  </div>'>
            </option>
        `;
    }

    function select_proper_transmitters(filters){
        var url = '/transmitters/';
        var data = {'satellite': filters.satellite};
        if (filters.station) {
            data.station_id = filters.station;
        }

        $.ajax({
            type: 'POST',
            url: url,
            data: data,
            dataType: 'json',
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', $('[name="csrfmiddlewaretoken"]').val());
                $('#transmitter-field').hide();
                $('#transmitter-field-loading').show();
                $('#station-field').hide();
                $('#station-field-loading').show();
            }
        }).done(function(data) {
            if (data.length == 1 && data[0].error) {
                $('#transmitter-selection').html(`<option id="no-transmitter"
                                                          value="" selected>
                                                    No transmitter available
                                                  </option>`).prop('disabled', true);
                $('#transmitter-selection').selectpicker('refresh');
            } else if (data.transmitters.length > 0) {
                var transmitters_options = '';
                if (filters.transmitter){
                    var is_transmitter_available = (data.transmitters.findIndex(tr => tr.uuid == filters.transmitter) > -1);
                    if(is_transmitter_available) {
                        var transmitter = data.transmitters.find(tr => tr.uuid == filters.transmitter);
                        transmitters_options = create_transmitter_option(filters.satellite, transmitter);
                        $('#transmitter-selection').html(transmitters_options);
                        $('#transmitter-selection').selectpicker('val', filters.transmitter);
                        var hidden_input='<input type="hidden" name="transmitter" value="'+ filters.transmitter + '">';
                        $('#transmitter-selection').after(hidden_input);
                        filters.transmitter = transmitter.uuid;
                    } else {
                        $('#transmitter-selection').html(`<option id="no-transmitter" value="" selected>
                                                            No transmitter available
                                                          </option>`).prop('disabled', true);
                        delete filters.transmitter;
                    }
                    $('#transmitter-selection').selectpicker('refresh');
                } else {
                    var max_good_count = 0;
                    var max_good_val = '';
                    $.each(data.transmitters, function (i, transmitter) {
                        if (max_good_count <= transmitter.good_count) {
                            max_good_count = transmitter.good_count;
                            max_good_val = transmitter.uuid;
                        }
                        transmitters_options += create_transmitter_option(filters.satellite, transmitter);
                    });
                    $('#transmitter-selection').html(transmitters_options).prop('disabled', false);
                    $('#transmitter-selection').selectpicker('refresh');
                    $('#transmitter-selection').selectpicker('val', max_good_val);
                    filters.transmitter = max_good_val;
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
            $('#transmitter-field-loading').hide();
            $('#transmitter-field').show();
        });
    }

    var suggested_data = [];
    var elevation_slider = new Slider('#scheduling-elevation-filter', { id: 'scheduling-elevation-filter', min: 0, max: 90, step: 1, range: true, value: [0, 90] });

    function update_schedule_button_status(){
        if($('#timeline rect').not('.unselected-obs').length != 0){
            $('#schedule-observation').prop('disabled', false);
        } else {
            $('#schedule-observation').prop('disabled', true);
        }
    }

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
        update_schedule_button_status();
    }

    elevation_slider.on('slideStop', function() {
        filter_observations();
        update_schedule_button_status();
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
        update_schedule_button_status();
    });

    $('#select-none-observations').on('click', function(){
        $.each(suggested_data, function(i, station){
            $.each(station.times, function(j, observation){
                observation.selected = false;
                $('#' + observation.id).toggleClass('unselected-obs', true);
            });
            station.selectedAll = false;
        });
        update_schedule_button_status();
    });

    $('#modal-schedule-observation').on('click', function() {
        $(this).prop('disabled', true);
        $('#schedule-observation').prop('disabled', true);
        $('#calculate-observation').prop('disabled', true);
    });

    $('#schedule-observation').on('click', function() {
        $('#windows-data').empty();
        var obs_counter = 0;
        var station_counter = 0;
        var warn_min_obs = parseInt(this.dataset.warnMinObs);
        var transmitter_uuid = $('#transmitter-selection').find(':selected').val();
        $.each(suggested_data, function(i, station){
            let obs_counted = obs_counter;
            $.each(station.times, function(j, observation){
                if(observation.selected){
                    var start = moment.utc(observation.starting_time).format('YYYY-MM-DD HH:mm:ss.SSS');
                    var end = moment.utc(observation.ending_time).format('YYYY-MM-DD HH:mm:ss.SSS');
                    $('#windows-data').append('<input type="hidden" name="obs-' + obs_counter + '-start" value="' + start + '">');
                    $('#windows-data').append('<input type="hidden" name="obs-' + obs_counter + '-end" value="' + end + '">');
                    $('#windows-data').append('<input type="hidden" name="obs-' + obs_counter + '-ground_station" value="' + station.id + '">');
                    $('#windows-data').append('<input type="hidden" name="obs-' + obs_counter + '-transmitter_uuid" value="' + transmitter_uuid + '">');
                    obs_counter += 1;
                }
            });
            if(obs_counted < obs_counter){
                station_counter += 1;
            }
        });
        $('#windows-data').append('<input type="hidden" name="obs-TOTAL_FORMS" value="' + obs_counter + '">');
        $('#windows-data').append('<input type="hidden" name="obs-INITIAL_FORMS" value="0">');
        if(obs_counter > warn_min_obs){
            $('#confirm-modal .counted-obs').text(obs_counter);
            $('#confirm-modal .counted-stations').text(station_counter);
            $('#confirm-modal').modal('show');
        } else if (obs_counter != 0){
            $(this).prop('disabled', true);
            $('#calculate-observation').prop('disabled', true);
            $('#form-obs').submit();
        }
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

    function initiliaze_calculation(show_results){
        if(show_results){
            $('.calculation-result').show();
        } else {
            $('.calculation-result').hide();
        }
        $('#obs-selection-tools').hide();
        $('#timeline').empty();
        $('#hover-obs').hide();
        $('#windows-data').empty();
        $('#schedule-observation').prop('disabled', true);
        $('#calculate-observation').prop('disabled', false);
    }

    $('#satellite-selection').on('changed.bs.select', function() {
        var satellite = $(this).find(':selected').data('norad');
        var station = $('#form-obs').data('obs-filter-station');
        select_proper_transmitters({
            satellite: satellite,
            station: station
        });
        initiliaze_calculation(false);
    });

    $('#transmitter-selection').on('changed.bs.select', function() {
        var transmitter = $(this).find(':selected').val();
        var station = $('#form-obs').data('obs-filter-station');
        select_proper_stations({
            transmitter: transmitter,
            station: station
        }, function(){
            if (obs_filter && obs_filter_dates && obs_filter_station && obs_filter_satellite){
                $('#obs-selection-tools').hide();
                $('#truncate-overlapped').click();
                calculate_observation();
            }
        });
        initiliaze_calculation(false);
    });

    function sort_stations(a, b){
        if( a.status > b.status){
            return -1;
        } else {
            return a.id - b.id;
        }
    }

    function calculate_observation(){
        initiliaze_calculation(true);
        var url = '/prediction_windows/';
        var data = {};
        // Add 5min for giving time to user schedule and avoid frequent start time errors.
        // More on issue #686: https://gitlab.com/librespacefoundation/satnogs/satnogs-network/issues/686
        if (!obs_filter_dates){
            data.start = moment($('#datetimepicker-start input').val()).add(5,'minute').format('YYYY-MM-DD HH:mm');
        } else {
            data.start = $('#datetimepicker-start input').val();
        }
        data.end = $('#datetimepicker-end input').val();
        data.transmitter = $('#transmitter-selection').find(':selected').val();
        data.satellite = $('#satellite-selection').val();
        data.stations = $('#station-selection').val();
        if (data.satellite.length == 0) {
            $('#windows-data').html('<span class="text-danger">You should select a Satellite first.</span>');
            return;
        } else if (data.transmitter.length == 0) {
            $('#windows-data').html('<span class="text-danger">You should select a Transmitter first.</span>');
            return;
        } else if (data.stations.length == 0 || (data.stations.length == 1 && data.stations[0] == '')) {
            $('#windows-data').html('<span class="text-danger">You should select a Station first.</span>');
            return;
        } else if (data.start.length == 0) {
            $('#windows-data').html('<span class="text-danger">You should select a Start Time first.</span>');
            return;
        } else if (data.end.length == 0) {
            $('#windows-data').html('<span class="text-danger">You should select an End Time first.</span>');
            return;
        }
        var is_custom_horizon = $('#horizon-status input[type=radio]').filter(':checked').val() == 'custom';
        if(is_custom_horizon) {
            data.min_horizon = $('#min-horizon').val();
        }
        var trancate_overlapped = $('#overlapped input[type=radio]').filter(':checked').val() == 'truncate-overlapped';
        if(trancate_overlapped) {
            data.overlapped = 1;
        }

        $.ajax({
            type: 'POST',
            url: url,
            data: data,
            dataType: 'json',
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', $('[name="csrfmiddlewaretoken"]').val());
                $('#loading').show();
            }
        }).done(function(results) {
            $('#loading').hide();
            if (results.length == 1 && results[0].error) {
                var error_msg = results[0].error;
                $('#windows-data').html('<span class="text-danger">' + error_msg + '</span>');
            } else {
                suggested_data = [];
                var dc = 0; // Data counter
                $('#windows-data').empty();
                results.sort(sort_stations);
                $.each(results, function(i, k){
                    var label = k.id + ' - ' + k.name;
                    var times = [];
                    var selectedAll = true;
                    $.each(k.window, function(m, n){
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
                            overlapped: n.overlapped,
                            id: k.id + '_' + times.length
                        });

                        dc = dc + 1;
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
                    timeline_init(data.start, data.end, suggested_data);
                } else {
                    var empty_msg = 'No Ground Station available for this observation window';
                    $('#windows-data').html('<span class="text-danger">' + empty_msg + '</span>');
                }
            }
        });
    }

    function timeline_init(start, end, payload){
        var start_timeline = moment.utc(start).valueOf();
        var end_timeline = moment.utc(end).valueOf();
        var period = end_timeline - start_timeline;
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
            .beginning(start_timeline)
            .ending(end_timeline)
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
                    div.find('#start').text(moment.utc(d.starting_time).format('YYYY-MM-DD HH:mm:ss'));
                    div.find('#end').text(moment.utc(d.ending_time).format('YYYY-MM-DD HH:mm:ss'));
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
                if ($('rect').length == 1 && obs_filter_station) {
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
                update_schedule_button_status();
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
                if(obs.overlapped){
                    $('#' + obs.id).css({'stroke': 'red'});
                }
            });
        });
        update_schedule_button_status();
        if ($('rect').length > 1) {
            $('#obs-selection-tools').show();
        }
    }

    $('#calculate-observation').click( function(){
        calculate_observation();
    });

    if (obs_filter && obs_filter_satellite) {
        select_proper_transmitters({
            satellite: obs_filter_satellite,
            transmitter: obs_filter_transmitter,
            station: obs_filter_station
        });
    } else {
        // Focus on satellite field
        $('#satellite-selection').selectpicker('refresh');
        $('#satellite-selection').selectpicker('toggle');
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
