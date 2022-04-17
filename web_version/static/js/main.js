setSampleFileType = () => {

    var file_type_options = document.getElementsByName("file_type");
    for(var i=0; i<file_type_options.length; i++){
        if(!file_type_options[i].checked) continue;

        if(file_type_options[i].value == 'annot'){
            $('#sample_file_path').attr('accept', '.txt');
        }
        else {
            $('#sample_file_path').attr('accept', '.edf');
        }
    }
}

enableLoadButton = () => {
    if(document.getElementById("sample_file_path").files.length > 0) {
        document.getElementById("sample_file_path_proxy").value = document.getElementById("sample_file_path").files[0].name;
        document.getElementById('load_btn').className = replaceClass(document.getElementById('load_btn').className, 'disabled', '');
    }
    else {
        document.getElementById("sample_file_path_proxy").value = "No file chosen";
        document.getElementById('load_btn').className = addClass(document.getElementById('load_btn').className, 'disabled');
    }
}

loadData = () => {

    for(var id in arr=['configure_btn', 'execute_btn', 'download_btn']){
        let ele = document.getElementById(arr[id]);
        let regexp = new RegExp("\\b" + 'disabled' + "\\b");
        if(ele.className.search(regexp) == -1) ele.className += ' disabled';
    }

    for(var id in arr=['apply_filter_btn', 'apply_filter_label']){
        document.getElementById(arr[id]).disabled = true;
    }
    
    let myform = document.getElementById("input_form");
    let fd = new FormData(myform);

    if(fd.get('sample_file_path').name == ''){
        return showStatusMessage('No input file selected.', type='error');
    }
    if(fd.get('epoch_size') == ''){
        return showStatusMessage('No epoch size selected.', type='error');
    }

    document.getElementById('status_area').innerHTML = '';
    showStatus('Uploading data ... (this may take a while)');

    $.ajax({
        xhr : function () {
            var xhr = new window.XMLHttpRequest();
            xhr.upload.addEventListener('progress', function(evt) {
                if (evt.lengthComputable) {
                    var progress_val = evt.loaded / evt.total;
                    progress_val = parseInt(progress_val * 100);
                    $('#upload_progressbar').attr('class', replaceClass($('#upload_progressbar').attr('class'), 'invisible', ''));
                    $('#input_file_upload_progess_bar').width(progress_val+'%');
                    $('#input_file_upload_progess_bar').html(progress_val+'%');
                }
            }, false);

            return xhr;
        },
        url: `/scvis/load/${job_id}`,
        data: fd,
        cache: false,
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (result) {
            $('#upload_progressbar').attr('class', $('#upload_progressbar').attr('class') + ' invisible');
            var status = result[0];
            var msg = result[1];
            showStatus(msg);
            if(status == 'Failed') return;
            for(var id in arr=['configure_btn', 'execute_btn']){
                document.getElementById(arr[id]).className = replaceClass(document.getElementById(arr[id]).className, 'disabled', '');
            }
        
            for(var id in arr=['apply_filter_btn', 'apply_filter_label']){
                document.getElementById(arr[id]).disabled = false;
            }
        }
      });
};

gotoConfigPage = () => {
    window.open(`/scvis/config/${job_id}`);
}

execute = () => {

    showStatus('Executing...');
    document.getElementById('vis_image').src = `${assets_folder}/loading.jpg`;
    document.getElementById('sc_st_table_content').innerHTML = '';

    let myform = document.getElementById("exec_form");
    let fd = new FormData(myform);
    
    $.ajax({
        url: `/scvis/execute/${job_id}`,
        data: fd,
        cache: false,
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (result) {
            var status = result[0];
            var msg = result[1];

            if(status == 'Failed'){
                showStatus(msg);
                document.getElementById('vis_image').src = `${assets_folder}/failed.jpg`;
                return
            }

            showStatus('Output files generated')
            
            let src_viz = `${data_folder}/${msg}.jpg?dummy=${Date.now()}`
            let src_sc_data = `${data_folder}/${msg}_sc.txt`
            let src_st_data = `${data_folder}/${msg}_st.txt`

            document.getElementById('vis_image').src = src_viz;

            tabulateData = data => {
                let data_tab = [];
                data.split('\n').forEach((row, index) => {
                    data_tab.push(row.split('\t'));
                })
                return data_tab
            }
        
            getCombinedTable = (data_tab1, data_tab2) => {
        
                makeHTMLRow = (last_epoch, i, data_comb) => {
                    let html_row = '';
                    if(i != last_epoch)
                        html_row = `<td>${last_epoch}-${i}</td>`;
                    else
                        html_row = `<td>${last_epoch}</td>`;
                    data_comb.forEach((col) => {
                        html_row += `<td>${col}</td>`
                    })
                    return html_row;
                }
        
                isEqArr = (array1, array2) => {
                    return (array1.length == array2.length) && array1.every(function(element, index) {
                                                                        return element === array2[index]; 
                    });
                }
        
                var html = '';
                for(var i=0; i < data_tab1.length; i++)
                {
                    if(i==0 || !isEqArr(data_comb, [...data_tab1[i], ...data_tab2[i]])){
                        if(i > 0){
                            html += ('<tr>' + makeHTMLRow(last_epoch, i, data_comb) + '</tr>');
                        }
                        data_comb = [...data_tab1[i], ...data_tab2[i]];
                        last_epoch = i+1
                    }
                    if(i == (data_tab1.length-1)){
                        html += ('<tr>' + makeHTMLRow(last_epoch, i+1, data_comb) + '</tr>');
                    }
                }
        
                return html;
            }
        
            $.get(src_sc_data, function(data) {
                let data_tab1 = tabulateData(data);
                $.get(src_st_data, function(data) {   
                    let data_tab2 = tabulateData(data);
                    document.getElementById('sc_st_table_content').innerHTML = getCombinedTable(data_tab1, data_tab2)
                }, 'text');
            }, 'text');

            document.getElementById('download_btn').className = replaceClass(document.getElementById('download_btn').className, 'disabled', '' );
        }
    });
};

downloadOutputs = () => {

    showStatus('Preparing files to download...');
    
    $.ajax({
        url: `/scvis/download/${job_id}`,
        cache: false,
        processData: false,
        contentType: false,
        type: 'GET',
        success: function (result) {
            var status = result[0];
            var msg = result[1];
            if(status == 'Failed') {
                showStatus(msg);
                return;
            } 
            const link = document.createElement("a");
            link.download = 'output_files.zip';
            link.href = `${data_folder}/${msg}`;
            document.body.appendChild(link)
            link.click();
            document.body.removeChild(link)
        }
    });
}

saveSettings = () => {

    let myform = document.getElementById("settings_form");
    let fd = new FormData(myform);

    if(fd.getAll('channel_values').length == 0){
        $('a[href="#select_channels"]').tab('show');
        return showStatusMessage('No channels selected.', type='error');
    }

    for(const [sleep_stage, annots] of Object.entries(annots_right_settings)) {
        if(annots.length == 0){
            $('a[href="#select_sleep_stages"]').tab('show');
            return showStatusMessage(`No annotations selected for ${sleep_stage}.`, type='error');
        }
        for(var i in annots){
            fd.append(sleep_stage, annots[i])
        }
    }

    document.getElementById('status_area').innerHTML = '';
    showStatus('Saving settings...');
    
    $.ajax({
        url: `/scvis/savesettings/${job_id}`,
        data: fd,
        cache: false,
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (result) {
            var status = result[0];
            var msg = result[1];
            showStatus(msg);
        }
    });
};

selectAllChannels = (value) => {

    var channel_values = document.getElementsByName('channel_values');

    for (var i=0; i < channel_values.length; i++) {
        channel_values[i].checked = value;
    }
    select_all_or_none_btn = document.getElementById('select_all_or_none');
    if (value == true) {
        select_all_or_none_btn.innerHTML = 'Select None';
    }
    else {
        select_all_or_none_btn.innerHTML = 'Select All';
    }
        
    select_all_or_none_btn.onclick = () => {selectAllChannels(!value)};
}

showSleepStageAnnots = (value, event) => {

    for(var i=0; i < event.srcElement.options.length; i++){
        if(event.srcElement.options[i].value == value){
            document.getElementById(value).className = document.getElementById(value).className.replace( /(?:^|\s)d-none(?!\S)/g , '' );
        }
        else{
            document.getElementById(event.srcElement.options[i].value).className += " d-none";
        }
    }
}

moveAnnotsToRightPanel = () => {

    sleep_stage_selected = document.getElementById('sleep_stages').value;

    var checkboxes_selected = $('input[name="annot_checkbuttons_left"]:checked');
    for(var i=0; i<checkboxes_selected.length; i++){
        let annot = checkboxes_selected[i].value;
        annots_left_settings.splice(annots_left_settings.findIndex(val => val === annot), 1)
        annots_right_settings[sleep_stage_selected].push(annot)
    }

    annots_left_settings.sort();
    annots_right_settings[sleep_stage_selected].sort();
    loadSleepStageSettings();
}

moveAnnotsToLeftPanel = () => {

    sleep_stage_selected = document.getElementById('sleep_stages').value;

    var checkboxes_selected = $('input[name="annot_checkbuttons_right"]:checked');
    for(var i=0; i<checkboxes_selected.length; i++){
        let annot = checkboxes_selected[i].value;
        annots_left_settings.push(annot)
        annots_right_settings[sleep_stage_selected].splice(annots_right_settings[sleep_stage_selected].findIndex(val => val === annot), 1)
    }

    annots_left_settings.sort();
    annots_right_settings[sleep_stage_selected].sort();
    loadSleepStageSettings();
}

loadSleepStageSettings = () => {

    var html = '';
    
    for(var i in annots_left_settings) {
        annot = annots_left_settings[i];
        html += 
        `<div class="row"> \
            <div class="col-1"> \
                <input class="form-check-input" type="checkbox" name="annot_checkbuttons_left" value="${annot}"> \
            </div> \
            <div class="col"> \
                <label class="form-check-label" for="${annot}">${annot}</label> \
            </div> \
        </div>`
    }

    document.getElementById('annotations').innerHTML = html;

    sleep_stage_selected = document.getElementById('sleep_stages').value;
    document.getElementById('annotations_selected').innerHTML = '';

    for(const [sleep_stage, annots] of Object.entries(annots_right_settings)) {
        var html = '';
        var annots_selected = '';
        for(var i in annots){
            annot = annots[i];
            html += 
            `<div class="row"> \
                <div class="col-1"> \
                    <input class="form-check-input" type="checkbox" name="annot_checkbuttons_right" value="${annot}"> \
                </div> \
                <div class="col"> \
                    <label class="form-check-label" for="${annot}">${annot}</label> \
                </div> \
            </div>`
            if (annots_selected == '')
                annots_selected = annot
            else
                annots_selected += (', ' + annot)
        }
        class_name = 'row';
        if(sleep_stage != sleep_stage_selected)
            class_name += ' d-none';
        document.getElementById('annotations_selected').innerHTML += `<div id="${sleep_stage}" class="${class_name}">\
                                                                    <div class="col">${html}</div>\
                                                                   </div>`;

        document.getElementById(`st_annot_td_${sleep_stage}`).innerHTML = annots_selected;
    }

}

loadSettings = () => {

    var html = '';
    var checked_all = true;
    for(var i in channel_settings){
        let channel_row = channel_settings[i];
        let html_cols = '';
        for(var j in channel_row){
            let ch_name = channel_row[j][0];
            let checked = channel_row[j][1];
            if(!checked) checked_all = false;
            html_cols += 
            `<div class="col-6 col-md-3 col-xl-2 border border-light">\
                <input class="form-check-input" type="checkbox" name="channel_values" value="${ch_name}" ${checked}>\
                <label class="form-check-label ms-2" for="${ch_name}">${ch_name}</label>\
            </div>`
        }
        html += `<div class="row">${html_cols}</div>`
    }
    var select_all_or_none_btn = document.getElementById('select_all_or_none');
    if(!checked_all) {
        select_all_or_none_btn.innerHTML = 'Select All';
    }
    else {
        select_all_or_none_btn.innerHTML = 'Select None';
    }
    select_all_or_none_btn.onclick = () => {selectAllChannels(!checked_all)};
    document.getElementById('channels').innerHTML = html;

    loadSleepStageSettings()                     
}

showStatusMessage = (msg, type='info') => {

    if (type == 'success') {
        html = 
        `<div class="alert alert-success alert-dismissible fade show">\
        <strong>Success!</strong> ${msg}\
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>\
        </div>`;
    }
    else if (type == 'error') {
        html = 
        `<div class="alert alert-danger alert-dismissible fade show">\
        <strong>Error!</strong> ${msg}\
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>\
        </div>`;
    }
    else if (type == 'warning') {
        html = 
        `<div class="alert alert-warning alert-dismissible fade show">\
        <strong>Warning!</strong> ${msg}\
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>\
        </div>`;
    }
    else if (type == 'info') {
        html = 
        `<div class="alert alert-info alert-dismissible fade show">\
        <strong>Info!</strong> ${msg}\
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>\
        </div>`;
    }

    document.getElementById('status_area').innerHTML = html;
}

showStatus = msg => {
    status_area = document.getElementById('status_textarea'); 
    status_area.innerHTML += `${msg}\n`;
    status_area.focus();
    status_area.scrollTop = status_area.scrollHeight;
}

replaceClass = (class_str, class_to_replace, class_to_replace_with) => {
    let regexp = new RegExp("\\b" + class_to_replace + "\\b");
    return class_str.replace(regexp, class_to_replace_with);
}

addClass = (class_str, class_to_add) => {
    let regexp = new RegExp("\\b" + class_to_add + "\\b");
    if(class_str.search(regexp) == -1) class_str += ' ' + class_to_add;
    return class_str
}