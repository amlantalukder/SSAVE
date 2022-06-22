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
        enableElement(document.getElementById('load_btn'));
    }
    else {
        document.getElementById("sample_file_path_proxy").value = "No file chosen";
        disableElement(document.getElementById('load_btn'));
    }
}

loadData = () => {

    for(var id in arr=['configure_btn', 'execute_btn', 'download_btn']){
        disableElement(document.getElementById(arr[id]));
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
        url: `/ssave/load/${job_id}`,
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
            var file_type = result[2];
            if(file_type == 'edf'){
                for(var id in arr=['configure_btn', 'execute_btn']){
                    enableElement(document.getElementById(arr[id]));
                }

                for(var id in arr=['apply_filter_btn', 'apply_filter_label']){
                    document.getElementById(arr[id]).disabled = false;
                }

                document.getElementById('apply_filter_btn').checked = false;
            }
            else
                enableElement(document.getElementById('execute_btn'));
        }
      });
};

gotoConfigPage = () => {
    window.open(`/ssave/config/${job_id}`);
}

showExecutionResults = (result) => {

    var status = result['status'];
    var msg = result['msg'];

    if(status == 'Failed'){
        showStatus(msg);
        document.getElementById('vis_image').src = `${assets_folder}/failed.jpg`;
        return
    }

    if(result['num_filtered_epochs'])
        showStatus(`${result['num_filtered_epochs']} epochs are filtered out`);

    showStatus('Output files generated')
    
    let src_viz = `${data_folder}/${msg}.jpg?dummy=${Date.now()}`
    let src_sc_data = `${data_folder}/${msg}_sc.txt?dummy=${Date.now()}`
    let src_st_data = `${data_folder}/${msg}_st.txt?dummy=${Date.now()}`

    document.getElementById('vis_image').src = src_viz;
    if(document.getElementById('vis_image_1')) document.getElementById('vis_image_1').src = src_viz;

    tabulateData = data => {
        let data_tab = [];
        data.split('\n').forEach((row, index) => {
            data_tab.push(row.split('\t').slice(1));
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

    enableElement(document.getElementById('download_btn'));

    if(result['cut_options'] && result['cut_options'].length > 0){

        let cut_options = result['cut_options'];
        let cut_options_selected = result['cut_options_selected'];

        $.get(src_sc_data, function(data) {
            let data_tab = tabulateData(data);
            let html = '';
            for(let i=0; i < cut_options.length; i++){
                let checked = '';
                if (cut_options_selected.find(x => x == cut_options[i]) != undefined)
                    checked = 'checked';
                let epoch = parseInt(cut_options[i]);
                let sc_index = data_tab[epoch][0]
                let start, end;
                for(start=epoch; start >= 0 && sc_index == data_tab[start][0]; start--);
                for(end=epoch; end < data_tab.length && sc_index == data_tab[end][0]; end++);
                html += `<tr><td>${start+2}-${end}</td><td>${sc_index}</td><td>${cut_options[i]}</td><td>\
                    <input class="form-check-input" type="checkbox" name="nremp_cut_options_chk" value="${epoch}" ${checked}>\
                    </td></tr>`
            }
            document.getElementById('nremp_cut_options_table_content').innerHTML = html;
        }, 'text');
        let msg = 'We have found cut options for long NREM cycle. Please \
            <a class="link-primary" href="#" onclick="activateTab(\'nremp_cut_options\');">click here</a>\
                to show the options.'
        document.getElementById('nremp_cut_option_msg').innerHTML = 
            `<div class="alert alert-info alert-dismissible fade show text-center" style="font-size:0.8rem">\
                ${msg}\
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>\
            </div>`;

        showElement(document.getElementById('nremp_cut_options_tab'));
    }
    else {
        activateTab('visualization');
        document.getElementById('nremp_cut_option_msg').innerHTML = '';
        document.getElementById('nremp_cut_options_table_content').innerHTML = '';
        hideElement(document.getElementById('nremp_cut_options_tab'));
    }
} 

execute = () => {

    showStatus('Executing...');
    document.getElementById('vis_image').src = `${assets_folder}/loading.jpg`;
    if(document.getElementById('vis_image_1')) document.getElementById('vis_image_1').src = `${assets_folder}/loading.jpg`;
    document.getElementById('sc_st_table_content').innerHTML = '';

    let myform = document.getElementById("exec_form");
    let fd = new FormData(myform);

    let save_cut_options = document.getElementsByName('nremp_cut_options_chk');
    if(save_cut_options){
        for(let i=0; i < save_cut_options.length; i++){
            if(save_cut_options[i].checked)
                fd.append('nremp_cut_options_selected', save_cut_options[i].value);
        }
    }
    
    $.ajax({
        url: `/ssave/execute/${job_id}`,
        data: fd,
        cache: false,
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (result) {
            showExecutionResults(result);
        }
    });
};

downloadOutputs = () => {

    showStatus('Preparing files to download...');
    
    $.ajax({
        url: `/ssave/download/${job_id}`,
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
            return showStatusMessage(`No events selected for ${sleep_stage}.`, type='error');
        }
        for(var i in annots){
            fd.append(sleep_stage, annots[i])
        }
    }

    document.getElementById('status_area').innerHTML = '';
    showStatus('Saving settings...');
    
    $.ajax({
        url: `/ssave/savesettings/${job_id}`,
        data: fd,
        cache: false,
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (result) {
            var status = result[0];
            var msg = result[1];
            showStatus(msg);
            var remain_here_modal = new bootstrap.Modal(document.getElementById('remain_here_modal'), {
                keyboard: false
            });

            remain_here_modal.show()
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

moveAnnotsToRightPanel = () => {

    var sleep_stage_selected = document.getElementById('settings_form').st_type.value;

    var checkboxes_selected = $('input[name="annot_checkbuttons_left"]:checked');
    for(var i=0; i<checkboxes_selected.length; i++){
        let annot = checkboxes_selected[i].value;
        annots_right_settings[sleep_stage_selected].push(annot)
    }

    loadSleepStageSettings();
}

moveAnnotsToLeftPanel = () => {

    var sleep_stage_selected = document.getElementById('settings_form').st_type.value;

    var checkboxes_selected = $(`input[name="annot_checkbuttons_right_${sleep_stage_selected}"]:checked`);
    for(var i=0; i<checkboxes_selected.length; i++){
        let annot = checkboxes_selected[i].value;
        annots_right_settings[sleep_stage_selected].splice(annots_right_settings[sleep_stage_selected].findIndex(val => val === annot), 1)
    }

    loadSleepStageSettings();
}

loadRightPanel = () => {

    var sleep_stage_selected = document.getElementById('settings_form').st_type.value;
    annots_right_settings[sleep_stage_selected].sort();
    document.getElementById('annotations_selected').innerHTML = '';

    for(const [sleep_stage, annots] of Object.entries(annots_right_settings)) {
        var html = '';
        var annots_selected = '';
        for(var i in annots){
            annot = annots[i];
            let disabled = '';
            if(sleep_stage != sleep_stage_selected)
                disabled = 'disabled';
            html += 
            `<div class="row"> \
                <div class="col-1"> \
                    <input style="height:50%;width:80%;margin-top:0.32em" type="checkbox" name="annot_checkbuttons_right_${sleep_stage}" value="${annot}" ${disabled}> \
                </div> \
                <div class="col"> \
                    <label class="form-check-label" for="annot_checkbuttons_right_${sleep_stage}">${annot}</label> \
                </div> \
            </div>`
            if (annots_selected == '')
                annots_selected = annot
            else
                annots_selected += (', ' + annot)
        }
        
        document.getElementById(sleep_stage).innerHTML = html;
    }
}

loadSleepStageSettings = () => {

    hasKeyword = (x) => {
        for(var i in keywords)
            if(x.toLowerCase().search(keywords[i]) >= 0) return true
        return false
    }

    var keywords = ['sleep stage', 'wake stage', 'stage wake', 'w stage', 'stage w', 'wake', 
                    'n1 stage', 'stage n1', 'nrem 1', 'n1', 'stage1', 'stage 1', 'n 1', 
                    'n2 stage', 'stage n2', 'nrem 2', 'n2', 'stage2', 'stage 2', 'n 2', 
                    'n3 stage', 'stage n3', 'nrem 3', 'n3', 'stage3', 'stage 3', 'n 3',
                    'rem', 'r stage', 'stage r'];
        
    var html_relevant = '', html_nonrelevant = '';

    annots_all_settings.sort();
    
    for(var i in annots_all_settings) {
        annot = annots_all_settings[i];
        
        if(Object.values(annots_right_settings).find(annots => {
            for(var i in annots)
                if(annots[i] == annot) return true
            return false
        }) != undefined) continue;

        var html = `<div class="row"> \
                        <div class="col-1"> \
                            <input class="form-check-input" type="checkbox" name="annot_checkbuttons_left" value="${annot}"> \
                        </div> \
                        <div class="col"> \
                            <label class="form-check-label" for="${annot}">${annot}</label> \
                        </div> \
                    </div>`

        if(hasKeyword(annot))
            html_relevant += html;
        else
            html_nonrelevant += html;
    }
    if(html_relevant == '')
        html_relevant = '<label class="pb-1">No relevant sleep stage available for selection</label>';
    else
        html_relevant = '<label class="pb-1">Relevant sleep stage events</label>' + html_relevant;
    
    if(html_nonrelevant != '')
        html_nonrelevant = '<label class="pb-1">Other events</label>' + html_nonrelevant;

    document.getElementById('annotations_relevant').innerHTML = html_relevant;
    document.getElementById('annotations_nonrelevant').innerHTML = html_nonrelevant;

    loadRightPanel()

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

showElement = (ele) => {
    ele.className = replaceClass(ele.className, 'd-none', '');
}

hideElement = (ele) => {
    ele.className = addClass(ele.className, 'd-none');
}

enableElement = (ele) => {
    ele.className = replaceClass(ele.className, 'disabled', '');
}

disableElement = (ele) => {
    ele.className = addClass(ele.className, 'disabled');
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

activateTab = (tab) => {
    $('.nav-tabs a[href="#' + tab + '"]').tab('show');
}