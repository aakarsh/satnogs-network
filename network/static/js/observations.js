$(document).ready(function() {
    'use strict';

    $('.selectpicker').selectpicker();

    $('#observation-filter').submit(function () {
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

    // Filters submits
    $('.filter-section input[type=checkbox]').change(function() {
        $('#observation-filter').submit();
    });

    $('#satellite-selection').bind('keyup change', function() {
        $('#observation-filter').submit();
    });
    $('#observer-selection').bind('keyup change', function() {
        $('#observation-filter').submit();
    });
    $('#station-selection').bind('keyup change', function() {
        $('#observation-filter').submit();
    });

    // Check if filters should be displayed
    if (window.location.hash == '#collapseFilters') {
        $('#collapseFilters').hide();
    } else if ($('#collapseFilters').data('filtered') == 'True') {
        $('#collapseFilters').show();
    }

    // Open all observations in new tabs
    $('#open-all').click(function() {
        $('a.obs-link').each(function() {
            window.open($(this).attr('href'));
        });
    });
});
