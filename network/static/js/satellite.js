$(document).ready(function() {
    'use strict';

    $('#SatelliteModal').on('show.bs.modal', function (event) {
        var satlink = $(event.relatedTarget);
        var modal = $(this);

        $.ajax({
            url: '/satellites/' + satlink.data('id') + '/'
        })
            .done(function( data ) {
                modal.find('.satellite-title').text(data.name);
                modal.find('.satellite-names').text(data.names);
                modal.find('#SatelliteModalTitle').text(data.name);
                modal.find('.satellite-id').text(satlink.data('id'));
                modal.find('#db-link').attr('href', 'https://db.satnogs.org/satellite/' + satlink.data('id'));
                modal.find('#new-obs-link').attr('href', '/observations/new/?norad=' + satlink.data('id'));
                modal.find('#old-obs-link').attr('href', '/observations/?norad=' + satlink.data('id'));
                modal.find('#good-sat-obs').attr('href', '/observations/?future=0&good=1&bad=0&unvetted=0&failed=0&norad=' + satlink.data('id'));
                modal.find('#unknown-sat-obs').attr('href', '/observations/?future=0&good=0&bad=0&unvetted=1&failed=0&norad=' + satlink.data('id'));
                modal.find('#bad-sat-obs').attr('href', '/observations/?future=0&good=0&bad=1&unvetted=0&failed=0&norad=' + satlink.data('id'));
                modal.find('.satellite-success-rate').text(data.success_rate + '%');
                modal.find('.satellite-total-obs').text(data.data_count);
                modal.find('.satellite-good').text(data.good_count);
                modal.find('.satellite-unknown').text(data.unknown_count);
                modal.find('.satellite-bad').text(data.bad_count);
                modal.find('#transmitters').empty();
                $.each(data.transmitters, function(i, transmitter){
                    var transmitter_status = '-danger';
                    if(transmitter.alive){
                        transmitter_status = '-success';
                    }
                    var good_percentage = 0;
                    var unknown_percentage = 0;
                    var bad_percentage = 0;
                    if(transmitter.data_count > 0){
                        good_percentage = Math.round((transmitter.good_count / transmitter.data_count) * 100);
                        unknown_percentage = Math.round((transmitter.unknown_count / transmitter.data_count) * 100);
                        bad_percentage = Math.round((transmitter.bad_count / transmitter.data_count) * 100);
                    }
                    modal.find('#transmitters').append(`
                        <div class="col-md-12 transmitter">
                          <div class="panel panel` + transmitter_status + `">
                            <div class="panel-heading">
                              <span class="transmitter-desc">` + transmitter.description + `</span>
                            </div>
                            <div class="panel-body">
                              <div class="front-line">
                                <span class="label label-default">Observations</span>
                                <span class="front-data-big">
                                  <span class="transmitter-total-obs">` + transmitter.data_count + `</span>
                                  <div class="progress pull-right">
                                    <div class="progress-bar progress-bar-success transmitter-good"
                                                data-toggle="tooltip" data-placement="bottom"
                                                title="` + good_percentage  + '% (' + transmitter.good_count + `) Good"
                                                style="width:` + good_percentage + `%"></div>
                                    <div class="progress-bar progress-bar-warning transmitter-unknown"
                                                data-toggle="tooltip" data-placement="bottom"
                                                title="` + unknown_percentage  + '% (' + transmitter.unknown_count + `) Unknown"
                                                style="width:` + unknown_percentage + `%"></div>
                                    <div class="progress-bar progress-bar-danger transmitter-bad"
                                                data-toggle="tooltip" data-placement="bottom"
                                                title="` + bad_percentage  + '% (' + transmitter.bad_count + `) Bad"
                                                style="width:` + bad_percentage + `%"></div>
                                  </div>
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>`
                    );
                });
                if (data.image) {
                    modal.find('.satellite-img-full').attr('src', data.image);
                } else {
                    modal.find('.satellite-img-full').attr('src', '/static/img/sat.png');
                }

            });
    });
});
