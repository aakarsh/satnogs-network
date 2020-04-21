/* Returns band names of the given frequency range based on
    https://www.itu.int/rec/R-REC-V.431-8-201508-I/en recommendation from ITU */
/* exported bands_from_range */
function bands_from_range(min_frequency, max_frequency, return_array){

    if(max_frequency > min_frequency){
        var frequency_bands = [
            ['ULF', 300, 3000],
            ['VLF', 3000, 30000],
            ['LF', 30000, 300000],
            ['MF', 300000, 3000000],
            ['HF', 3000000, 30000000],
            ['VHF', 30000000, 300000000],
            ['UHF', 300000000, 1000000000],
            ['L', 1000000000, 2000000000],
            ['S', 2000000000, 4000000000],
            ['C', 4000000000, 8000000000],
            ['X', 8000000000, 12000000000],
            ['Ku', 12000000000, 18000000000],
            ['K', 18000000000, 27000000000],
            ['Ka', 27000000000, 40000000000],
        ];

        var bands = [];
        var found_min = false;
        for(let frequency_band of frequency_bands){
            let name = frequency_band[0];
            let min_freq = frequency_band[1];
            let max_freq = frequency_band[2];
            if(!found_min){
                if(min_freq <= min_frequency && min_frequency<= max_freq){
                    bands.push(name);
                    if(min_freq <= max_frequency && max_frequency <= max_freq){
                        if(return_array){
                            return bands;
                        } else {
                            return bands.join(', ');
                        }
                    }
                    found_min = true;
                    continue;
                }
                continue;
            }
            bands.push(name);
            if(min_freq < max_frequency && max_frequency <= max_freq){
                if(return_array){
                    return bands;
                } else {
                    return bands.join(', ');
                }
            }
        }
    }

    if(return_array){
        return [];
    } else {
        return '';
    }
}

/* exported human_frequency */
//Returns human readable, Hz formatted frequency
function human_frequency(frequency){
    var to_format = parseFloat(frequency);
    var formatted = '-';
    if(isNaN(to_format)){
        return formatted;
    }

    if(to_format >= 1000000000000){
        formatted = (to_format / 1000000000000).toFixed(3);
        formatted = formatted + ' THz';
    } else if(to_format >= 1000000000){
        formatted = (to_format / 1000000000).toFixed(3);
        formatted = formatted + ' GHz';
    } else if(to_format >= 1000000){
        formatted = (to_format / 1000000).toFixed(3);
        formatted = formatted + ' MHz';
    } else if(to_format >= 1000){
        formatted = (to_format / 1000).toFixed(3);
        formatted = formatted + ' KHz';
    } else{
        formatted = (to_format).toFixed(3);
        formatted = formatted + ' Hz';
    }
    return formatted;
}


