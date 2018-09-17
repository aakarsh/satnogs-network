/* global WaveSurfer URI calcPolarPlotSVG */

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
        var wavesurfer = Object.create(WaveSurfer);
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

        wavesurfer.init({
            container: container_el,
            waveColor: '#bf7fbf',
            progressColor: 'purple'
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
            var spectrogram = Object.create(WaveSurfer.Spectrogram);
            spectrogram.init({
                wavesurfer: wavesurfer,
                container: '#wave-spectrogram',
                fftSamples: 256,
                windowFunc: 'hann'
            });

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
    var uri = new URI(location.href);
    var tab = uri.hash();
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

    //JSON pretty renderer
    var metadata = $('#json-renderer').data('json');
    $('#json-renderer').jsonViewer(metadata, {collapsed: true});

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

    // Hotkeys bindings
    $(document).bind('keyup', function(event){
        if (event.which == 88) {
            var link_delete = $('#obs-delete');
            link_delete[0].click();
        } else if (event.which == 68) {
            var link_discuss = $('#obs-discuss');
            link_discuss[0].click();
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
