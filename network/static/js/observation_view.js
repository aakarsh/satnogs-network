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
        wavesurfer.on('error', hideProgress);

        wavesurfer.on('loading', function(percent) {
            showProgress(percent);
            $(loading).show();
        });

        $this.parents('.observation-data').find('.playpause').click( function(){
            wavesurfer.playPause();
        });

        $('a[href="#tab-audio"]').on('shown.bs.tab', function () {
            wavesurfer.load(data_audio_url);
            $('a[href="#tab-audio"]').off('shown.bs.tab');
        });

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

    function change_vetting_labels(status, status_display, user, datetime){
        $('#vetting-status').find('button').each(function(){
            if(this.dataset.status == status){
                $(this).addClass('hidden');
            } else {
                $(this).removeClass('hidden');
            }
        });
        var label_classes = 'label-unknown label-good label-bad label-failed';
        $('#vetting-status-label').removeClass(label_classes).addClass('label-' + status);
        $('#vetting-status-label').text(status_display);
        var title = 'Vetted ' + status + ' on ' + datetime + ' by ' + user;
        if(status == 'unknown'){
            title = 'This observation needs vetting';
        }
        $('#vetting-status-label').prop('title', title).tooltip('fixTitle');
    }

    //Vetting request
    function vet_observation(id, vet_status){
        var data = {};
        data.status = vet_status;
        var url = '/observation_vet/' + id + '/';
        $.ajax({
            type: 'POST',
            url: url,
            data: data,
            dataType: 'json',
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', $('[name="csrfmiddlewaretoken"]').val());
                $('#vetting-status').hide();
                $('#vetting-spinner').show();
            }
        }).done(function(results) {
            if (Object.prototype.hasOwnProperty.call(results, 'error')) {
                var error_msg = results.error;
                show_alert('danger',error_msg);
            } else {
                show_alert('success', 'Observation is vetted succesfully as ' + results.vetted_status);
                change_vetting_labels(results.vetted_status, results.vetted_status_display, results.vetted_user, results.vetted_datetime);
            }
            $('#vetting-spinner').hide();
            $('#vetting-status').show();
            return;
        }).fail(function() {
            var error_msg = 'Something went wrong, please try again';
            show_alert('danger', error_msg);
            $('#vetting-spinner').hide();
            $('#vetting-status').show();
            return;
        });
    }

    $('#vetting-status button').click( function(){
        var vet_status = $(this).data('status');
        var id = $(this).data('id');
        $(this).blur();
        vet_observation(id, vet_status);
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
            var link_unknown = $('#unknown-data');
            link_unknown[0].click();
        } else if (event.which == 71) {
            var link_good = $('#good-data');
            link_good[0].click();
        } else if (event.which == 66) {
            var link_bad = $('#bad-data');
            link_bad[0].click();
        } else if (event.which == 70) {
            var link_failed = $('#failed-data');
            link_failed[0].click();
        }
    });
});
