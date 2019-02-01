function updateUTCTime(){
    var now     = new Date();
    var minutes = now.getUTCMinutes();
    var hours   = now.getUTCHours();

    if (minutes < 10){
        minutes = '0' + minutes;
    }

    if (hours < 10){
        hours = '0' + hours;
    }

    var t_str = hours + ':' + minutes + ' UTC';
    document.getElementById('current_utc').innerHTML = t_str;
}
setInterval(updateUTCTime, 1000);
