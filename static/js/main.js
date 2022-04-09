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

loadData = () => {
    
    let myform = document.getElementById("input_form");
    let fd = new FormData(myform);

    if(fd.get('sample_file_path').name == ''){
        return showStatusMessage('No input file selected.', type='error');
    }
    if(fd.get('epoch_size') == ''){
        return showStatusMessage('No epoch size selected.', type='error');
    }

    document.getElementById('status_area').innerHTML = '';
    showStatus('Loading...');
    
    $.ajax({
        url: "/scvis/load",
        data: fd,
        cache: false,
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (result) {
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

execute = () => {

    showStatus('Executing...');
    document.getElementById('vis_image').src = `${assets_folder}/loading.jpg`;
    document.getElementById('sc_table_content').innerHTML = '';
    document.getElementById('st_table_content').innerHTML = '';

    let myform = document.getElementById("input_form");
    let fd = new FormData(myform);
    
    $.ajax({
        url: "/scvis/execute",
        data: fd,
        cache: false,
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (result) {
            var status = result[0];
            var msg = result[1];
            showStatus(msg);

            if(status == 'Failed'){
                document.getElementById('vis_image').src = `${assets_folder}/failed.jpg`;
                return
            } 

            src_viz = `${assets_folder}/temp/output_files/22-0320_F_1.6_1_splt_di.jpg?dummy=${Date.now()}`
            src_sc_data = `${assets_folder}/temp/output_files/22-0320_F_1.6_1_splt_di_sc.txt`
            src_st_data = `${assets_folder}/temp/output_files/22-0320_F_1.6_1_splt_di_st.txt`

            document.getElementById('vis_image').src = src_viz;

            tabulateData = data => {
                html = ''
                data.split('\n').forEach((row, index) => {
                    html_row = ''
                    row.split('\t').forEach((col) => {
                        html_row += `<td>${col}</td>`
                    })
                    html += `<tr><td>${index+1}</td>${html_row}</tr>`
                })
                return html
            }

            $.get(src_sc_data, function(data) {   
                document.getElementById('sc_table_content').innerHTML = tabulateData(data);
             }, 'text');

             $.get(src_st_data, function(data) {   
                document.getElementById('st_table_content').innerHTML = tabulateData(data);
             }, 'text');

            document.getElementById('download_btn').className = replaceClass(document.getElementById('download_btn').className, 'disabled', '' );
        }
    });
};

downloadOutputs = () => {

    showStatus('Preparing files to download...');
    
    $.ajax({
        url: "/scvis/download",
        cache: false,
        processData: false,
        contentType: false,
        type: 'GET',
        success: function (result) {
            var status = result[0];
            var msg = result[1];
            if(status == 'Failed') return;
            showStatus(msg)
            const link = document.createElement("a");
            link.download = 'output_files.zip';
            link.href = `${assets_folder}/temp/output_files.zip`;
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
        url: "/scvis/savesettings",
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
            <div class="col-2"> \
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
        for(var i in annots){
            annot = annots[i];
            html += 
            `<div class="row"> \
                <div class="col-2"> \
                    <input class="form-check-input" type="checkbox" name="annot_checkbuttons_right" value="${annot}"> \
                </div> \
                <div class="col"> \
                    <label class="form-check-label" for="${annot}">${annot}</label> \
                </div> \
            </div>`
        }
        class_name = 'row';
        if(sleep_stage != sleep_stage_selected)
            class_name += ' d-none';
        document.getElementById('annotations_selected').innerHTML += `<div id="${sleep_stage}" class="${class_name}">\
                                                                    <div class="col">${html}</div>\
                                                                   </div>`;
    }                     
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
    return class_str.replace(class_to_replace, class_to_replace_with);
}