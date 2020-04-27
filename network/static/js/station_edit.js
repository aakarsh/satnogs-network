/*global human_frequency, bands_from_range*/
/*eslint no-control-regex: 0*/
$(document).ready(function() {
    'use strict';

    $('#antennas-loading').toggle();
    $('.selectpicker').selectpicker();

    // Parse and initialize station data and remove html elements that holding them
    var station_element = $('#station-data-to-parse');
    var station_data = station_element.data();
    const max_frequency_ranges = station_data.max_frequency_ranges_per_antenna;
    const max_antennas = station_data.max_antennas_per_station;
    const maximum_frequency = station_data.max_frequency_for_range;
    const minimum_frequency = station_data.min_frequency_for_range;
    const vhf_max = station_data.vhf_max_frequency;
    const vhf_min = station_data.vhf_min_frequency;
    const uhf_max = station_data.uhf_max_frequency;
    const uhf_min = station_data.uhf_min_frequency;
    const s_max = station_data.s_max_frequency;
    const s_min = station_data.s_min_frequency;
    const l_max = station_data.l_max_frequency;
    const l_min = station_data.l_min_frequency;
    station_element.remove();

    // Parse and initialize antenna data and remove html elements that holidng them
    var current_antenna = {};
    var current_order = -1;
    var antenna_element = $('#antennas-data-to-parse');
    var antennas = [];

    function get_band_range(frequency_data){
        let range = {
            'min': frequency_data.min,
            'human_min': human_frequency(frequency_data.min),
            'max': frequency_data.max,
            'human_max': human_frequency(frequency_data.max),
            'bands': bands_from_range(frequency_data.min, frequency_data.max),
            'initial': Object.prototype.hasOwnProperty.call(frequency_data, 'id'),
            'deleted': Object.prototype.hasOwnProperty.call(frequency_data, 'deleted')
        };
        if(range.initial){
            range.id = frequency_data.id;
        }
        return range;
    }

    antenna_element.children().each(function(){
        var antenna_data = $(this).data();
        var frequency_ranges = [];
        $(this).children().each(function(){
            var frequency_data = $(this).data();
            frequency_ranges.push(
                get_band_range(frequency_data)
            );
        });
        let antenna = {
            'type_name': antenna_data.typeName,
            'type_id': antenna_data.typeId,
            'initial': Object.prototype.hasOwnProperty.call(antenna_data, 'id'),
            'deleted': Object.prototype.hasOwnProperty.call(antenna_data, 'deleted'),
            'frequency_ranges': frequency_ranges
        };
        if(antenna.initial){
            antenna.id = antenna_data.id;
        }
        antennas.push(antenna);
    });
    antenna_element.remove();

    // Functions to create and update antenna wells
    function create_antenna_well(antenna, order){
        var frequency_ranges_elements ='';
        for(let range of antenna.frequency_ranges){
            if(!range.deleted){
                frequency_ranges_elements += '<div>'+ range.human_min + ' - ' + range.human_max + ' (' + range.bands + ')</div>';
            }
        }
        var add_frequency_ranges_button = '<button type="button" data-action="edit" data-order="' + order + `" class="btn btn-xs btn-primary" data-toggle="modal" data-target="#modal">
                                             <span class="glyphicon glyphicon-plus" aria-hidden="true"></span>
                                             Click here to add frequency ranges
                                           </button>`;
        frequency_ranges_elements = frequency_ranges_elements || add_frequency_ranges_button;
        return '<div class="well" id="' + order + `">
                  <div class='row'>
                    <div class='col-md-6'>
                      <div class='antenna-label'>Type:</div>
                      ` + antenna.type_name + `
                    </div>
                    <div class='col-md-6'>
                      <button type="button" data-action="edit" data-order="` + order + `" class="btn btn-primary pull-right" data-toggle="modal" data-target="#modal">
                        <span class="glyphicon glyphicon-edit" aria-hidden="true"></span>
                        Edit
                      </button>
                    </div>
                  </div>
                  <div class='row'>
                    <div class='col-md-12'>
                      <div class="antenna-label">Frequency Ranges:</div>
                      <div class="frequency-ranges">` + frequency_ranges_elements + `</div>
                    </div>
                  </div>
                </div>`;
    }

    function update_antennas_wells(){
        $('#antennas-loading').show();
        $('#antennas-panel-body').hide();
        $('#antennas-panel-body .well').remove();
        let antennas_wells = '';
        let deleted = 0;
        antennas.forEach(function(antenna, order){
            if(!antenna.deleted){
                antennas_wells += create_antenna_well(antenna, order);
            } else {
                deleted++;
            }
        });
        $('#new-antenna').toggle(
            (antennas.length - deleted) < max_antennas
        );
        $('#antennas-panel-body').prepend(antennas_wells);
        $('#antennas-loading').hide();
        $('#antennas-panel-body').show();
    }

    // Create initial antenna bootstrap wells if antennas exist
    update_antennas_wells();

    // Form fields validations
    function update_text_input_and_validation(text_input, text, valid){
        text_input.val(text);
        text_input.parents('.frequency-range-fields').toggleClass('has-success', valid);
        text_input.parents('.frequency-range-fields').toggleClass('has-error', !valid);

    }

    function check_validity_of_frequencies(){
        $('button[data-action=save]').prop('disabled', false);
        let valid = true;

        for(let order in current_antenna.frequency_ranges){
            let valid_range = true;
            let range = current_antenna.frequency_ranges[order];

            if(range.deleted){
                continue;
            }

            let min = parseInt(range.min);
            let max = parseInt(range.max);
            let text_input = $('#' + order + '-range-text');

            if(isNaN(min) || isNaN(max)){
                valid_range = false;
                update_text_input_and_validation(text_input, 'Invalid minimum or maximum value', false);
                continue;
            } else if(max < min){
                valid_range = false;
                update_text_input_and_validation(text_input, 'Maximum value is greater than minimum value', false);
                continue;
            } else if(min < minimum_frequency || max > maximum_frequency){
                valid_range = false;
                update_text_input_and_validation(text_input, 'Minimum or maximum value is out of range', false);
                continue;
            }

            for(let index in current_antenna.frequency_ranges){
                let index_range = current_antenna.frequency_ranges[index];
                let index_min = parseInt(index_range.min);
                let index_max = parseInt(index_range.max);
                if(index_range.deleted || index === order || isNaN(index_min) || isNaN(index_max)){
                    continue;
                }
                if(index_min < min && index_max > max) {
                    valid_range = false;
                    update_text_input_and_validation(text_input, 'Range is subset of another range', false);
                    break;
                } else if(index_min > min && index_max < max) {
                    valid_range = false;
                    update_text_input_and_validation(text_input, 'Range is superset of another range', false);
                    break;
                } else if(!(index_min > max || index_max < min)){
                    valid_range = false;
                    update_text_input_and_validation(text_input, 'Range conflicts with another range', false);
                    break;
                }
            }

            if(valid_range){
                range.human_min = human_frequency(range.min);
                range.human_max = human_frequency(range.max);
                range.bands = bands_from_range(range.min, range.max);
                update_text_input_and_validation(text_input, range.human_min + '-' + range.human_max + '(' + range.bands + ')', true);
            } else {
                valid = false;
            }
        }

        if(!valid) {
            $('button[data-action=save]').prop('disabled', true);
        }
    }

    function check_validity_of_input(element){
        let input = $(element);
        if(element.id === 'station-name' || element.id === 'description'){
            /* Limit letters of description and name to ISO/IEC 8859-1 (latin1)
               https://en.wikipedia.org/wiki/ISO/IEC_8859-1 */
            let constraint = new RegExp('[^\n\r\t\x20-\x7E\xA0-\xFF]', 'gi');
            if(element.id === 'station-name'){
                constraint = new RegExp('[^\x20-\x7E\xA0-\xFF]', 'gi');
            }
            if(constraint.test(input.val())){
                element.setCustomValidity('Please use characters that belong to ISO-8859-1 (https://en.wikipedia.org/wiki/ISO/IEC_8859-1)');
            } else {
                element.setCustomValidity('');
            }
        }
        let valid = element.checkValidity();
        $('#submit').prop('disabled', !$('form')[0].checkValidity());
        input.parent().toggleClass('has-success', valid);
        input.parent().toggleClass('has-error', !valid);
    }

    $('input').each(function(){
        if(!$(this).hasClass('frequency')){
            check_validity_of_input(this);
        }
    });

    // Events related to validation
    $('body').on('input', function(e){
        let input = $(e.target);
        let value = input.val();
        let order = input.data('order');
        let field = input.data('field');
        if(input.hasClass('frequency')){
            current_antenna.frequency_ranges[order][field] = value;
            check_validity_of_frequencies();
        } else {
            check_validity_of_input(e.target);
        }
    });

    // Functions to initialize modal
    function band_ranges(band){
        switch(band){
        case 'VHF':
            return get_band_range({'min': vhf_min, 'max': vhf_max});
        case 'UHF':
            return get_band_range({'min': uhf_min, 'max': uhf_max});
        case 'L':
            return get_band_range({'min': l_min, 'max': l_max});
        case 'S':
            return get_band_range({'min': s_min, 'max': s_max});
        default:
            return get_band_range({'min': minimum_frequency, 'max': maximum_frequency});
        }
    }

    function create_frequency_range_well(range, order){
        return `<div class="well">
                  <div class="form-group">
                    <div data-order="` + order + `" class='row frequency-range-fields'>
                      <div class='col-md-10'>
                        <div class='row'>
                          <div class='col-md-6'>
                            <label for="` + order + `-min" class="control-label">Minimum</label>
                            <input data-order="` + order + '" data-field="min" value="' + range.min + '" id="' + order + '-min" type="number" min="' + minimum_frequency + '" max="' + maximum_frequency + `" class="form-control frequency" placeholder="Minimum Frequency">
                          </div>
                          <div class='col-md-6'>
                            <label for="` + order + `-max" class="control-label">Maximum</label>
                            <input data-order="` + order + '" data-field="max" value="' + range.max + '" id="' + order + '-max" type="number" min="' + minimum_frequency + '" max="' + maximum_frequency + `" class="form-control frequency " placeholder="Maximum Frequency">
                          </div>
                        </div>
                        <div class='row'>
                          <div class='col-md-12'>
                            <input id="` + order + '-range-text" readonly="" type="text" value="' + range.human_min + ' - ' + range.human_max + ' (' + range.bands + `)" class="form-control text-center">
                          </div>
                        </div>
                      </div>
                      <div class='col-md-2 text-right'>
                        <button class="btn btn-danger remove-range" type="button" data-order="` + order + `" aria-label="Remove frequency range">
                          <span class="glyphicon glyphicon-remove"></span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>`;
    }

    function update_frequency_ranges_wells(){
        $('#frequency-ranges-loading').show();
        $('#frequency-ranges').hide();
        $('#frequency-ranges .well').remove();
        let frequency_ranges_wells = '';
        let deleted = 0;
        current_antenna.frequency_ranges.forEach(function(frequency_range, order){
            if(!frequency_range.deleted){
                frequency_ranges_wells += create_frequency_range_well(frequency_range, order);
            } else {
                deleted++;
            }
        });
        $('#new-ranges').toggle(
            (current_antenna.frequency_ranges.length - deleted) < max_frequency_ranges
        );
        if((current_antenna.frequency_ranges.length - deleted) == 0){
            frequency_ranges_wells = 'Add a frequency range by choosing one of the default ranges or a custom one bellow<hr>';
        }
        $('#frequency-ranges').html(frequency_ranges_wells);
        check_validity_of_frequencies();
        $('#frequency-ranges-loading').hide();
        $('#frequency-ranges').show();
    }

    // Events related to modal
    $('#antenna-type').on('changed.bs.select', function (e, clickedIndex, isSelected) {
        if(isSelected !== null){
            let value = e.target.value;
            current_antenna.type_name = $('option[value=' + value + ']').data('content');
            current_antenna.type_id = value;
        }
    });

    $('#frequency-ranges').on('click', '.remove-range',function(e){
        let order = $(e.currentTarget).data('order');
        if(current_antenna.frequency_ranges[order].initial){
            current_antenna.frequency_ranges[order].deleted = true;
        } else {
            current_antenna.frequency_ranges.splice(order, 1);
        }
        update_frequency_ranges_wells();
    });

    $('.new-range').on('click', function(){
        let range = band_ranges($(this).data('range'));
        current_antenna.frequency_ranges.push(range);
        update_frequency_ranges_wells();
    });

    $('#modal').on('show.bs.modal', function (e) {
        $('#submit').prop('disabled', true); // Disable submit button
        let action = $(e.relatedTarget).data('action');
        if(action == 'edit'){
            let order = $(e.relatedTarget).data('order');
            $('#modal-title').text('Edit Antenna');
            current_antenna = $.extend(true, {}, antennas[order]);
            current_order = order;
            $('#antenna-type').selectpicker('val', antennas[order].type_id);
            $('#delete-antenna').show();

        } else if(action == 'new'){
            $('#modal-title').text('New Antenna');
            let value = $('#antenna-type').children(':first').val();
            current_antenna = {'type_name': $('option[value=' + value + ']').data('content'), 'type_id': value, 'initial': false, 'deleted': false, 'frequency_ranges': []};
            current_order = -1;
            $('#antenna-type').selectpicker('val', value);
            $('#delete-antenna').hide();
        }
        update_frequency_ranges_wells();
    });

    $('#modal').on('click', '.modal-action', function (e) {
        let action = $(e.currentTarget).data('action');
        let order = current_order;
        if(action == 'save'){
            let to_save_antenna = $.extend(true, {}, current_antenna);
            to_save_antenna.frequency_ranges.forEach(function(range){
                range.human_min = human_frequency(range.min);
                range.human_max = human_frequency(range.max);
                range.bands = bands_from_range(range.min, range.max);
            });
            if(current_order >= 0){
                antennas[order] = to_save_antenna;
            } else {
                antennas.push(to_save_antenna);
            }
        } else if(action == 'delete'){
            if(antennas[order].initial){
                antennas[order].deleted = true;
            } else {
                antennas.splice(order, 1);
            }
        }
        update_antennas_wells();
        $(e.delegateTarget).modal('hide');
    });

    $('#modal').on('hidden.bs.modal', function () {
        let value = $('#antenna-type').first().val();
        current_antenna = {'type_name': $('option[value=' + value + ']').data('content'), 'type_id': value, 'initial': false, 'deleted': false, 'frequency_ranges': []};
        $('#antenna-type').selectpicker('val', value);
        $('#frequency-ranges').html('Add a frequency range by choosing one of the default ranges or a custom one bellow<hr>');
        $('#frequency-ranges').show();
        $('#delete-antenna').hide();
        $('#submit').prop('disabled', false); // Enable submit button
    });

    // Initialize Station form elements
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

    var image_exists = Object.prototype.hasOwnProperty.call($('#station-image').data(), 'existing');
    var send_remove_file = false;
    if(image_exists){
        $('#station-image').fileinput({
            showRemove: true,
            showUpload: false,
            initialPreview: $('#station-image').data('existing'),
            initialPreviewAsData: true,
            allowedFileTypes: ['image'],
            autoOrientImage: false,
            fileActionSettings: {
                showDownload: false,
                showRemove: false,
                showZoom: true,
                showDrag: false,
            }
        });
    } else {
        $('#station-image').fileinput({
            showRemove: true,
            showUpload: false,
            allowedFileTypes: ['image'],
            autoOrientImage: false,
            fileActionSettings: {
                showDownload: false,
                showRemove: false,
                showZoom: true,
                showDrag: false,
            }
        });
    }
    $('#station-image').on('change', function() {
        send_remove_file = false;
    });

    $('#station-image').on('fileclear', function() {
        send_remove_file = image_exists;
    });

    // Submit or Cancel form
    $('#cancel').on('click', function(){
        if(this.textContent == 'Back to Dashboard'){
            location.href = location.origin + '/users/redirect/';
        } else {
            location.href = location.href.replace('edit/','');
        }
    });

    $('form').on('submit', function(){
        $('#antenna-type').remove();
        let antennas_total = 0;
        let antennas_initial = 0;
        let form = $('form');
        // Prepare station form
        if(send_remove_file){
            form.append('<input type="checkbox" name="image-clear" style="display: none" checked>');
        }
        // Prepare antennas forms
        antennas.forEach(function(antenna, order){
            antennas_total++;
            let antenna_prefix = 'ant-' + order;
            if(antenna.deleted){
                form.append('<input type="checkbox" name="' + antenna_prefix + '-DELETE" style="display: none" checked>');
            }
            if(antenna.initial){
                antennas_initial++;
                form.append('<input type="hidden" name="' + antenna_prefix + '-id" value="' + antenna.id + '">');
            }
            form.append('<input type="hidden" name="' + antenna_prefix + '-antenna_type" value="' + antenna.type_id + '">');

            //Prepare frequency ranges forms
            let frequency_ranges_total = 0;
            let frequency_ranges_initial = 0;
            antenna.frequency_ranges.forEach(function(range, range_order){
                frequency_ranges_total++;
                let range_prefix = antenna_prefix + '-fr-' + range_order;
                if(range.deleted){
                    form.append('<input type="checkbox" name="' + range_prefix + '-DELETE" style="display: none" checked>');
                }
                if(range.initial){
                    frequency_ranges_initial++;
                    form.append('<input type="hidden" name="' + range_prefix + '-id" value="' + range.id + '">');
                }
                form.append('<input type="hidden" name="' + range_prefix + '-min_frequency" value="' + range.min + '">');
                form.append('<input type="hidden" name="' + range_prefix + '-max_frequency" value="' + range.max + '">');
            });
            form.append('<input type="hidden" name="' + antenna_prefix + '-fr-TOTAL_FORMS" value="' + frequency_ranges_total + '">');
            form.append('<input type="hidden" name="' + antenna_prefix + '-fr-INITIAL_FORMS" value="' + frequency_ranges_initial + '">');
            form.append('<input type="hidden" name="' + antenna_prefix + '-fr-MAX_NUM_FORMS" value="' + max_frequency_ranges + '">');
        });
        form.append('<input type="hidden" name="ant-TOTAL_FORMS" value="' + antennas_total + '">');
        form.append('<input type="hidden" name="ant-INITIAL_FORMS" value="' + antennas_initial + '">');
        form.append('<input type="hidden" name="ant-MAX_NUM_FORMS" value="' + max_antennas + '">');
    });

});
