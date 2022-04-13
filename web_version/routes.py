import uuid, pdb
from web_version.controller import WebUIController
from flask import render_template, redirect, request, jsonify, url_for
from web_version import app

print(id(app))
controller_pool = {}

@app.route('/', methods=['GET'])
def home():
    app.logger.info('Home page loaded.')
    job_id = uuid.uuid4().hex
    return render_template('index.html', job_id=job_id)

@app.route('/config/<job_id>', methods=['GET'])
def config(job_id):
    print(job_id)
    if job_id not in controller_pool:
        return redirect(url_for('home'))
    controller = controller_pool[job_id]
    
    channel_settings = getChannelSettings(controller)
    annots_left_settings, annots_right_settings, sleep_stages = getSleepStageSettings(controller)
    filter_settings, bad_annot_settings = getFilterSettings(controller)
    app.logger.info('Configurations loaded.')
    return render_template('config.html', channel_settings=channel_settings, 
                                            annots_left_settings=annots_left_settings,
                                            annots_right_settings=annots_right_settings,
                                            sleep_stages=sleep_stages,
                                            filter_settings=filter_settings,
                                            bad_annot_settings=bad_annot_settings)

@app.route('/load/<job_id>', methods = ['POST'])
def loadData(job_id):
    print(job_id)
    global controller_pool
    controller = WebUIController(app, job_id)
    app.logger.info(f'Data load request: {request}')
    response = controller.loadSleepData(request)
    controller_pool[job_id] = controller
    app.logger.info(f'Data load response: {response}')
    return jsonify(response)

@app.route('/execute/<job_id>', methods = ['POST'])
def execute(job_id):
    print(job_id)
    if job_id not in controller_pool: 
        return redirect(url_for('home'))
    controller = controller_pool[job_id]

    app.logger.info(f'Execution request: {request}')
    response = controller.execute(request)
    app.logger.info(f'Execution response: {response}')
    return jsonify(response)

@app.route('/savesettings/<job_id>', methods = ['POST'])
def saveSettings(job_id):
    print(job_id)
    if job_id not in controller_pool: 
        return redirect(url_for('home'))
    controller = controller_pool[job_id]

    app.logger.info(f'Save settings request: {request}')
    response = controller.saveSettings(request)
    app.logger.info(f'Save settings response: {response}')
    return jsonify(response)

@app.route('/download/<job_id>', methods = ['GET'])
def download(job_id):
    print(job_id)
    if job_id not in controller_pool: 
        return redirect(url_for('home'))
    controller = controller_pool[job_id]

    app.logger.info(f'Download request')
    response = controller.download()
    app.logger.info(f'Download response: {response}')
    return jsonify(response)

def getChannelSettings(controller):

    config = controller.getConfig()
    row, num_cols = 0, 12
    channels_of_interest = set(list(config.CHANNELS_SELECTED))
    channel_cols, channel_settings = [], []
    for i in range(len(controller.channels_all)):
        
        ch_name = controller.channels_all[i]
        
        if i // num_cols != row:
            if i > 0: channel_settings.append(channel_cols)
            channel_cols = []
            row = i // num_cols

        channel_cols.append((ch_name, "checked" if ch_name in channels_of_interest else ""))

        if i == len(controller.channels_all)-1:
            channel_settings.append(channel_cols)

    return channel_settings

def getSleepStageSettings(controller):

    config = controller.getConfig()

    annots_left_settings = []
    for i in range(len(controller.annotations_all)):
        annot_name = controller.annotations_all[i]
        if annot_name.lower() not in config.sleep_stage_event_to_id_mapping:
            annots_left_settings.append(annot_name)

    annots_right_settings = {sleep_stage:[] for sleep_stage in config.SLEEP_STAGE_ALL_NAMES}

    for annot_name in controller.annotations_all:
        if annot_name.lower() in config.sleep_stage_event_to_id_mapping:
            for st_stage_ind in range(len(config.SLEEP_STAGE_ALL_NAMES)):
                if config.sleep_stage_event_to_id_mapping[annot_name.lower()] == config.SLEEP_STAGES_ALL[st_stage_ind]:
                    annots_right_settings[config.SLEEP_STAGE_ALL_NAMES[st_stage_ind]].append(annot_name)

    return annots_left_settings, annots_right_settings, config.SLEEP_STAGE_ALL_NAMES

def getFilterSettings(controller):

    config = controller.getConfig()

    filter_settings = {key:value for key, value in config.FILTERS.items() if key in ['notch', 'bandpass', 'amplitude_max', 'flat_signal']}

    bad_annots = set(config.FILTERS['bad_annots'])
    bad_annot_settings = []
    for annot in controller.annotations_all:
        if annot in bad_annots:
            bad_annot_settings.append([annot, 'checked'])
        else:
            bad_annot_settings.append([annot, ''])
        
    return filter_settings, bad_annot_settings