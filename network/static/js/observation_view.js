/* global WaveSurfer calcPolarPlotSVG */

$(document).ready(function() {
    'use strict';

    // Format time for the player
    function formatTime(timeSeconds) {
        var minute = Math.floor(timeSeconds / 60);
        var tmp = Math.round(timeSeconds - (minute * 60));
        var second = (tmp < 10 ? '0' : '') + tmp;
        var seconds_rounded = Math.round(timeSeconds);
        return String(minute + ':' + second + ' / ' + seconds_rounded + ' s');
    }

    // Set width for not selected tabs
    var panelWidth = $('.tab-content').first().width();
    $('.tab-pane').css('width', panelWidth);

    function load_audio_tab() {
        // Waveform loading
        $('.wave').each(function(){
            var $this = $(this);
            var wid = $this.data('id');
            var data_audio_url = $this.data('audio');
            var container_el = '#data-' + wid;
            $(container_el).css('opacity', '0');
            var loading = '#loading-' + wid;
            var $playbackTime = $('#playback-time-' + wid);
            var progressDiv = $('#progress-bar-' + wid);
            var progressBar = $('.progress-bar', progressDiv);
 
            var showProgress = function (percent) {
                if (percent == 100) {
                    $(loading).text('Analyzing data...');
                }
                progressDiv.css('display', 'block');
                progressBar.css('width', percent + '%');
                progressBar.text(percent + '%');
            };
 
            var hideProgress = function () {
                progressDiv.css('display', 'none');
            };

            var onError = function () {
                hideProgress();
                $('#tab-audio').replaceWith('<div class="notice">Something went wrong, try again later.</div><div class="notice">If the problem persists, please contact an administrator.</div>');
            };
 
            var wavesurfer = WaveSurfer.create({
                container: container_el,
                waveColor: '#bf7fbf',
                progressColor: 'purple',
                plugins: [
                    WaveSurfer.spectrogram.create({
                        wavesurfer: wavesurfer,
                        container: '#wave-spectrogram',
                        fftSamples: 256,
                        windowFunc: 'hann'
                    })
                ]
            });
 
            wavesurfer.on('destroy', hideProgress);
            wavesurfer.on('error', onError);
 
            wavesurfer.on('loading', function(percent) {
                showProgress(percent);
                $(loading).show();
            });
 
            $this.parents('.observation-data').find('.playpause').click( function(){
                wavesurfer.playPause();
            });
 
            wavesurfer.load(data_audio_url);

            wavesurfer.on('ready', function() {
                hideProgress();
 
                //$playbackTime.text(formatTime(wavesurfer.getCurrentTime()));
                $playbackTime.text(formatTime(wavesurfer.getCurrentTime()));
 
                wavesurfer.on('audioprocess', function(evt) {
                    $playbackTime.text(formatTime(evt));
                });
                wavesurfer.on('seek', function(evt) {
                    $playbackTime.text(formatTime(wavesurfer.getDuration() * evt));
                });
                $(loading).hide();
                $(container_el).css('opacity', '1');
            });
        });
    }

    $('a[href="#tab-audio"]').on('shown.bs.tab', function () {
        load_audio_tab();
        $('a[href="#tab-audio"]').off('shown.bs.tab');
    });
 
    // Handle Observation tabs
    var uri = new URL(location.href);
    var tab = uri.hash;
    $('.observation-tabs li a[href="' + tab + '"]').tab('show');

    // Delete confirmation
    var message = 'Do you really want to delete this Observation?';
    var actions = $('#obs-delete');
    if (actions.length) {
        actions[0].addEventListener('click', function(e) {
            if (! confirm(message)) {
                e.preventDefault();
            }
        });
    }
    //Vetting help functions
    function show_alert(type, msg){
        $('#alert-messages').html(
            `<div class="col-md-12">
               <div class="alert alert-` + type + `" role="alert">
                 <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                   <span class="glyphicon glyphicon-remove"></span>
                 </button>` + msg +`
               </div>
             </div>`);
    }

    function change_vetting_labels(user, datetime, waterfall_status_label, waterfall_status_display,
        status, status_label, status_display){
        $('#waterfall-status').find('button').each(function(){
            if(this.dataset.status == waterfall_status_label){
                $(this).addClass('hidden');
            } else {
                $(this).removeClass('hidden');
            }
        });

        var waterfall_label_classes = 'label-unknown label-with-signal label-without-signal';
        $('#waterfall-status-label').removeClass(waterfall_label_classes).addClass('label-' + waterfall_status_label);
        $('#waterfall-status-label').text(waterfall_status_display);
        var waterfall_status_title = 'Vetted ' + waterfall_status_display + ' on ' + datetime + ' by ' + user;
        if(waterfall_status_label == 'unknown'){
            waterfall_status_title = 'Waterfall needs vetting';
        }
        $('#waterfall-status-label').prop('title', waterfall_status_title).tooltip('fixTitle');

        var rating_label_classes = 'label-unknown label-future label-good label-bad label-failed';
        $('#rating-status span').removeClass(rating_label_classes).addClass('label-' + status_label);
        $('#rating-status span').text(status_display);
        var status_title = status;
        $('#rating-status span').prop('title', status_title).tooltip('fixTitle');
    }

    //Vetting request
    function vet_waterfall(id, vet_status){
        var data = {};
        data.status = vet_status;
        var url = '/waterfall_vet/' + id + '/';
        $.ajax({
            type: 'POST',
            url: url,
            data: data,
            dataType: 'json',
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', $('[name="csrfmiddlewaretoken"]').val());
                $('#waterfall-status-label').hide();
                $('#waterfall-status-form').hide();
                $('#rating-status').hide();
                $('#vetting-spinner').show();
                $('#rating-spinner').show();
            }
        }).done(function(results) {
            if (Object.prototype.hasOwnProperty.call(results, 'error')) {
                var error_msg = results.error;
                show_alert('danger',error_msg);
            } else {
                show_alert('success', 'Waterfall is vetted succesfully as ' + results.waterfall_status);
                change_vetting_labels(results.waterfall_status_user, results.waterfall_status_datetime,
                    results.waterfall_status_label, results.waterfall_status_display,
                    results.status, results.status_label,
                    results.status_display);
            }
            $('#vetting-spinner').hide();
            $('#rating-spinner').hide();
            $('#waterfall-status-label').show();
            $('#waterfall-status-form').show();
            $('#rating-status').show();
            return;
        }).fail(function() {
            var error_msg = 'Something went wrong, please try again';
            show_alert('danger', error_msg);
            $('#vetting-spinner').hide();
            $('#rating-spinner').hide();
            $('#waterfall-status-label').show();
            $('#waterfall-status-form').show();
            $('#rating-status').show();
            return;
        });
    }

    $('#waterfall-status button').click( function(){
        var vet_status = $(this).data('status');
        var id = $(this).data('id');
        $(this).blur();
        vet_waterfall(id, vet_status);
    });

    //JSON pretty renderer
    var metadata = $('#json-renderer').data('json');
    $('#json-renderer').jsonViewer(metadata, {collapsed: true, withLinks: false});

    // Draw orbit in polar plot
    var tleLine1 = $('svg#polar').data('tle1');
    var tleLine2 = $('svg#polar').data('tle2');

    var timeframe = {
        start: new Date($('svg#polar').data('timeframe-start')),
        end: new Date($('svg#polar').data('timeframe-end'))
    };

    var groundstation = {
        lon: $('svg#polar').data('groundstation-lon'),
        lat: $('svg#polar').data('groundstation-lat'),
        alt: $('svg#polar').data('groundstation-alt')
    };

    const polarPlotSVG = calcPolarPlotSVG(timeframe,
        groundstation,
        tleLine1,
        tleLine2);

    $('svg#polar').append(polarPlotSVG);

    // Function to convert hex data in each data blob to ASCII, while storing
    // the original blob in a jquery .data, for later reversal back to hex
    // (see next function)
    $('#asciibutton').click(function(){
        $('.hex').each(function(){
            $(this).data('hex', $(this).text());
            var hex = $(this).text().replace(/ /g,'').replace(/\r?\n|\r/g, '');
            var str = '';
            for (var i = 0; i < hex.length; i += 2) {
                str += String.fromCharCode(parseInt(hex.substr(i, 2), 16));
            }
            $(this).html(str);
        });
        $('#asciibutton').toggleClass('btn-default');
        $('#asciibutton').toggleClass('btn-primary');
        $('#hexbutton').toggleClass('btn-default');
        $('#hexbutton').toggleClass('btn-primary');
        $('#asciibutton').attr('disabled', 'disabled');
        $('#hexbutton').removeAttr('disabled');
    });

    // retrieve saved hex data and replace the decoded blob with the original
    // hex text
    $('#hexbutton').click(function(){
        $('.hex').each(function(){
            $(this).html($(this).data('hex'));
        });
        $('#asciibutton').toggleClass('btn-default');
        $('#asciibutton').toggleClass('btn-primary');
        $('#hexbutton').toggleClass('btn-default');
        $('#hexbutton').toggleClass('btn-primary');
        $('#hexbutton').attr('disabled', 'disabled');
        $('#asciibutton').removeAttr('disabled');
    });

    // Hotkeys bindings
    $(document).bind('keyup', function(event){
        if (event.which == 88) {
            var link_delete = $('#obs-delete');
            link_delete[0].click();
        } else if (event.which == 68) {
            var link_discuss = $('#obs-discuss');
            link_discuss[0].click();
        } else if (event.which == 85) {
            var link_unknown = $('#unknown-status');
            link_unknown[0].click();
        } else if (event.which == 71) {
            var link_good = $('#with-signal-status');
            link_good[0].click();
        } else if (event.which == 66) {
            var link_bad = $('#without-signal-status');
            link_bad[0].click();
        }
    });
});
