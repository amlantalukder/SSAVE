import uuid, pdb
from web_version.controller import WebUIController
from flask import render_template, redirect, request, jsonify, url_for
from web_version import app
import numpy as np

print(id(app))

@app.route('/', methods=['GET'])
def home():
    app.logger.info('Home page loaded.')
    
    job_id = uuid.uuid4().hex
    
    app.logger.info(f'Job id assigned, job id: {job_id}')
    
    return render_template('index.html', job_id=job_id)

@app.route('/config/<job_id>', methods=['GET'])
def config(job_id):

    app.logger.info(f'Configuration request: {request}, job id: {job_id}')
    
    controller = WebUIController(app, job_id)
    status, response, data = controller.getConfig()
    channel_settings, \
    annots_left_settings, annots_right_settings, sleep_stages, \
    filter_settings, bad_annot_settings, \
    epoch_size = data

    app.logger.info(f'Configuration response: {response}, job id: {job_id}')

    return render_template('config.html', job_id = job_id, \
                                            channel_settings=channel_settings, 
                                            annots_left_settings=annots_left_settings,
                                            annots_right_settings=annots_right_settings,
                                            sleep_stages=sleep_stages,
                                            filter_settings=filter_settings,
                                            bad_annot_settings=bad_annot_settings,
                                            epoch_size=epoch_size)

@app.route('/load/<job_id>', methods = ['POST'])
def loadData(job_id):

    app.logger.info(f'Data load request: {request}, job id: {job_id}')
    
    controller = WebUIController(app, job_id)
    response = controller.loadSleepData(request)
    
    app.logger.info(f'Data load response: {response}, job id: {job_id}')
    
    return jsonify(response)

@app.route('/execute/<job_id>', methods = ['POST'])
def execute(job_id):

    app.logger.info(f'Execution request: {request}, job id: {job_id}')
    
    controller = WebUIController(app, job_id)
    response = controller.execute(request)
    
    app.logger.info(f'Execution response: {response}, job id: {job_id}')
    
    status, msg, *cut_options_settings = response

    if cut_options_settings:
        cut_options, cut_options_selected = cut_options_settings
        cut_options = list(np.array(cut_options, dtype=str))
        cut_options_selected = list(np.array(cut_options_selected, dtype=str))

        return jsonify({'status':status, 'msg':msg, 'cut_options':cut_options, 'cut_options_selected':cut_options_selected})
    
    return jsonify({'status':status, 'msg':msg})

@app.route('/savesettings/<job_id>', methods = ['POST'])
def saveSettings(job_id):

    app.logger.info(f'Save settings request: {request}, job id: {job_id}')
    
    controller = WebUIController(app, job_id)
    response = controller.saveSettings(request)
    
    app.logger.info(f'Save settings response: {response}, job id: {job_id}')

    return jsonify(response)

@app.route('/download/<job_id>', methods = ['GET'])
def download(job_id):

    app.logger.info(f'Download request, job id: {job_id}')

    controller = WebUIController(app, job_id)
    response = controller.download()
    
    app.logger.info(f'Download response: {response}, job id: {job_id}')
    
    return jsonify(response)