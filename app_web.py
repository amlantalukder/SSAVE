import sys, os, logging, pdb
from controller import WebUIController
from flask import Flask, render_template, make_response, redirect, request, jsonify, url_for

log_path = os.path.join(os.path.dirname(__file__), 'scvis.log')
logging.basicConfig(filename=log_path, level=logging.INFO)

class PrefixMiddleware(object):

    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):

        if environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            start_response('404', [('Content-Type', 'text/plain')])
            return ["This url does not belong to the app.".encode()]

app = Flask(__name__)
app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix='/scvis')
controller = WebUIController(app)

@app.route('/', methods=['GET'])
def home():
    app.logger.info('Home page loaded.')
    return render_template('index.html')

@app.route('/config', methods=['GET'])
def config():
    config = controller.getConfig()
    channel_settings = getChannelSettings(config)
    annots_left_settings, annots_right_settings, sleep_stages = getSleepStageSettings(config)
    filter_settings, bad_annot_settings = getFilterSettings(config)
    app.logger.info('Configurations loaded.')
    return render_template('config.html', channel_settings=channel_settings, 
                                            annots_left_settings=annots_left_settings,
                                            annots_right_settings=annots_right_settings,
                                            sleep_stages=sleep_stages,
                                            filter_settings=filter_settings,
                                            bad_annot_settings=bad_annot_settings)

@app.route('/load', methods = ['POST'])
def loadData():
    app.logger.info(f'Data load request: {request}')
    response = controller.loadSleepData(request)
    app.logger.info(f'Data load response: {response}')
    return jsonify(response)

@app.route('/execute', methods = ['POST'])
def execute():
    app.logger.info(f'Execution request: {request}')
    response = controller.execute(request)
    app.logger.info(f'Execution response: {response}')
    return jsonify(response)

@app.route('/savesettings', methods = ['POST'])
def saveSettings():
    app.logger.info(f'Save settings request: {request}')
    response = controller.saveSettings(request)
    app.logger.info(f'Save settings response: {response}')
    return jsonify(response)

@app.route('/download', methods = ['GET'])
def download():
    app.logger.info(f'Download request')
    response = controller.download()
    app.logger.info(f'Download response: {response}')
    return jsonify(response)

def getChannelSettings(config):

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

def getSleepStageSettings(config):

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

def getFilterSettings(config):

    filter_settings = {key:value for key, value in config.FILTERS.items() if key in ['notch', 'bandpass', 'amplitude_max', 'flat_signal']}

    bad_annots = set(config.FILTERS['bad_annots'])
    bad_annot_settings = []
    for annot in controller.annotations_all:
        if annot in bad_annots:
            bad_annot_settings.append([annot, 'checked'])
        else:
            bad_annot_settings.append([annot, ''])
        
    return filter_settings, bad_annot_settings

if __name__ == '__main__':

    ip_address, port = '127.0.0.1', 5002
    
    app.logger.info(sys.argv)
    
    if len(sys.argv) > 1:
        ip_address = sys.argv[1]
    elif len(sys.argv) > 2:
        ip_address, port = sys.argv[1:3]    
    
    app.run(host=ip_address, port=port, debug=True)