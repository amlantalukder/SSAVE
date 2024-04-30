from functools import cmp_to_key
import os
import shutil
import numpy as np
import pdb

import visualize_sleep as scv

# --------------------------------------------------------------------------


class Controller():

    # --------------------------------------------------------------------------
    def removeOutputFiles(self, scv_obj):

        img_path = os.path.join(scv_obj.folder_cache, f'{scv_obj.sample_name}.jpg')
        sc_path = os.path.join(scv_obj.folder_cache, f'{scv_obj.sample_name}_sc.txt')
        st_path = os.path.join(scv_obj.folder_cache, f'{scv_obj.sample_name}_st.txt')
        eeg_path = os.path.join(scv_obj.folder_cache, f'{scv_obj.sample_name}_eeg.npy')
        spec_path = os.path.join(scv_obj.folder_cache, f'{scv_obj.sample_name}_spec_2.npy')

        if os.path.exists(img_path):
            os.remove(img_path)
        if os.path.exists(sc_path):
            os.remove(sc_path)
        if os.path.exists(st_path):
            os.remove(st_path)
        if os.path.exists(eeg_path):
            os.remove(eeg_path)
        if os.path.exists(spec_path):
            os.remove(spec_path)

    # --------------------------------------------------------------------------
    def validate(self, value, _type, input_name=''):

        if _type == 'file_type':
            if value in ['edf', 'annot']:
                return value
            print("Error!! sample type not selected")
        elif _type == 'epoch_size':
            return float(value)
        elif _type == 'input_file_path':
            if os.path.exists(value) and os.path.isfile(value) and os.path.splitext(value)[1].lower() in ['.edf', '.txt']:
                return os.path.abspath(value)
            print("Error!! invalid sample path selected")
        elif _type == 'output_folder_path':
            if os.path.exists(value) and os.path.isdir(value):
                return os.path.abspath(value)
            print("Error!! invalid output path selected")
        elif _type in ['frequency', 'amplitude', 'time']:
            try:
                return float(value)
            except:
                print("Error!! invalid value for {input_name}")

# --------------------------------------------------------------------------


class WebUIController(Controller):

    channels_all = None
    annotations_all = None
    state_changed = True
    scv_obj = None

    def __init__(self, app, job_id):
        self.app = app
        self.job_id = job_id
        self.FOLDER_INPUT = os.path.join(os.path.dirname(__file__), f'static/assets/temp/{self.job_id}/input_files')
        self.FOLDER_OUTPUT = os.path.join(os.path.dirname(__file__), f'static/assets/temp/{self.job_id}/output_files')
        self.FOLDER_EXAMPLES = os.path.join(os.path.dirname(__file__), f'static/assets/examples')
        self.FOLDER_OTHER_DATA = os.path.join(os.path.dirname(__file__), f'static/assets/temp/{self.job_id}/other_data_files')
        print(self)

    # --------------------------------------------------------------------------
    def loadSleepData(self, view):

        try:
            file_type = self.validate(view.form.get('file_type'), 'file_type')

            if view.form.get('example') is None:
                f = view.files.get('sample_file_path')
                if not os.path.exists(self.FOLDER_INPUT):
                    os.makedirs(self.FOLDER_INPUT)
                input_file_path = os.path.join(self.FOLDER_INPUT, f.filename)
                f.save(input_file_path)
            else:
                file_name, input_file_name = view.form.get('example').split(',')
                example_file_path = os.path.join(self.FOLDER_EXAMPLES, file_name)
                if not os.path.exists(self.FOLDER_INPUT):
                    os.makedirs(self.FOLDER_INPUT)
                input_file_path = os.path.join(self.FOLDER_INPUT, input_file_name)
                shutil.copyfile(example_file_path, input_file_path)

            input_file_path = self.validate(input_file_path, 'input_file_path')
            if (input_file_path is None) or (file_type is None):
                raise Exception

            self.app.logger.info(f'Input EEG file: {input_file_path}')

            scv_obj = scv.loadSleepData(input_file_path, self.FOLDER_OUTPUT, file_type, app_logger=self.app.logger)

            other_data = {'sample_name': scv_obj.sample_name, 'input_file_path': input_file_path,
                          'file_type': file_type, 'apply_filter': False, 'annotations_all': [],
                          'channels_all': [], 'CHANNELS_SELECTED': [],
                          'sleep_stage_event_to_id_mapping': scv.Config.sleep_stage_event_to_id_mapping,
                          'FILTERS': scv.Config.FILTERS, 'EPOCH_SIZE': scv.Config.EPOCH_SIZE, 'status_changed': True}

            if file_type == 'edf':

                if scv_obj.eeg_data is None:
                    scv_obj.loadEEG()

                other_data['annotations_all'] = np.sort(np.unique(scv_obj.eeg_data._annotations.description))
                other_data['channels_all'] = scv_obj.eeg_data.info['ch_names']

                if len(other_data['channels_all']) == 0:
                    print('No channels found !!!')

                other_data['CHANNELS_SELECTED'] = scv.Config.CHANNELS_SELECTED[np.in1d(scv.Config.CHANNELS_SELECTED, other_data['channels_all'])]

            if not os.path.exists(self.FOLDER_OTHER_DATA):
                os.makedirs(self.FOLDER_OTHER_DATA)
            np.save(f'{self.FOLDER_OTHER_DATA}/other_data.npy', other_data)

        except Exception as error:
            return ('Failed', f"Data loading failed, {str(error)}")

        return ('Success', "Loaded sleep data successfully", file_type)

    # --------------------------------------------------------------------------
    def saveSettings(self, view):

        try:

            channels_selected = np.array(view.form.getlist('channel_values'))

            new_st_mapping = {}
            for st_ind, stage in enumerate(scv.Config.SLEEP_STAGE_ALL_NAMES):
                if len(view.form.getlist(stage)) == 0:
                    return (False, f"No annotation selected for {stage}")
                for annot in view.form.getlist(stage):
                    new_st_mapping[annot.lower()] = scv.Config.SLEEP_STAGES_ALL[st_ind]

            notch_freq = self.validate(view.form.get('notch_freq_entry'), 'frequency', input_name='Notch Frequency')
            bandpass_min_freq = self.validate(view.form.get('bandpass_min_freq_entry'), 'frequency', input_name='Bandpass Maximum Frequency')
            bandpass_max_freq = self.validate(view.form.get('bandpass_max_freq_entry'), 'frequency', input_name='Bandpass Minimum Frequency')
            amplitude_max = self.validate(view.form.get('amplitude_max_entry'), 'amplitude', input_name='Maximum Amplitude')
            flat_signal_duration = self.validate(view.form.get('flat_signal_duration_entry'), 'time', input_name='Flat Signal Duration')
            bad_annots = view.form.getlist('bad_annots_list')

            epoch_size = self.validate(view.form.get('epoch_size'), 'epoch_size')

            if len(channels_selected) == 0:
                return (False, "No channels selected")

            if (notch_freq is None) or (bandpass_min_freq is None) or (bandpass_max_freq is None) or (amplitude_max is None) or (flat_signal_duration is None):
                return (False, "Invalid input")

            if bandpass_max_freq < bandpass_min_freq:
                return (False, "Bandpass maximum frequency cannot be less than minimum frequency")

            other_data = np.load(f'{self.FOLDER_OTHER_DATA}/other_data.npy', allow_pickle=True).item()

            other_data['CHANNELS_SELECTED'] = channels_selected
            other_data['sleep_stage_event_to_id_mapping'] = new_st_mapping
            other_data['FILTERS']['notch'] = notch_freq
            other_data['FILTERS']['bandpass'] = [bandpass_min_freq, bandpass_max_freq]
            other_data['FILTERS']['amplitude_max'] = amplitude_max
            other_data['FILTERS']['flat_signal'] = flat_signal_duration
            other_data['FILTERS']['bad_annots'] = bad_annots
            other_data['EPOCH_SIZE'] = epoch_size

            other_data['state_changed'] = True

            np.save(f'{self.FOLDER_OTHER_DATA}/other_data.npy', other_data)

        except Exception as error:
            return ('Failed', f"Settings could not be saved, {str(error)}")

        return ('Success', "Saved Settings")

    # --------------------------------------------------------------------------
    def execute(self, view):

        num_filtered_epochs = 0

        try:

            other_data = np.load(f'{self.FOLDER_OTHER_DATA}/other_data.npy', allow_pickle=True).item()

            if other_data['apply_filter'] != (view.form.get('apply_filter') == 'on'):
                other_data['apply_filter'] = (view.form.get('apply_filter') == 'on')
                self.app.logger.info(f'Apply filter: {other_data["apply_filter"]}')
                other_data['state_changed'] = True

            if ('cut_options_selected' not in other_data) or (other_data['cut_options_selected'] != view.form.getlist('nremp_cut_options_selected')):
                other_data['cut_options_selected'] = view.form.getlist('nremp_cut_options_selected')
                self.app.logger.info(f'Cut options selected: {other_data["cut_options_selected"]}')
                other_data['state_changed'] = True

            self.app.logger.info(f'State changed: {self.state_changed}')
            if other_data['state_changed']:
                scv_obj = scv.loadSleepData(other_data['input_file_path'], self.FOLDER_OUTPUT, other_data['file_type'])
                scv_obj.cut_options_selected = list(np.array(other_data['cut_options_selected'], dtype=np.int64))

                if other_data['file_type'] == 'edf':
                    scv.Config.CHANNELS_SELECTED = other_data['CHANNELS_SELECTED']
                    scv.Config.sleep_stage_event_to_id_mapping = other_data['sleep_stage_event_to_id_mapping']
                    scv.Config.FILTERS = other_data['FILTERS']
                    scv.Config.EPOCH_SIZE = other_data['EPOCH_SIZE']

                    self.app.logger.info(f'Config.CHANNELS_SELECTED: {scv.Config.CHANNELS_SELECTED}')
                    self.app.logger.info(f'Config.sleep_stage_event_to_id_mapping: {scv.Config.sleep_stage_event_to_id_mapping}')
                    self.app.logger.info(f'Config.FILTERS: {scv.Config.FILTERS}')

                self.app.logger.info('Removing old output files')
                self.removeOutputFiles(scv_obj)
                scv_obj.clearSleepData()
                scv.extractSleepStages(scv_obj, other_data['apply_filter'])
                num_filtered_epochs = scv_obj.num_filtered_epochs
                other_data['cut_options'] = scv_obj.cut_options
                other_data['state_changed'] = False

                np.save(f'{self.FOLDER_OTHER_DATA}/other_data.npy', other_data)

        except Exception as error:
            return ('Failed', f"Execution failed, {str(error)}")

        return ('Success', os.path.join(os.path.basename(self.FOLDER_OUTPUT), other_data['sample_name']),
                other_data['cut_options'], other_data['cut_options_selected'], num_filtered_epochs)

    # --------------------------------------------------------------------------
    def getConfig(self):
    
        try:
            other_data = np.load(f'{self.FOLDER_OTHER_DATA}/other_data.npy', allow_pickle=True).item()

            channel_settings = self.getChannelSettings(other_data)
            annots_left_settings, annots_right_settings, sleep_stages = self.getSleepStageSettings(other_data)
            filter_settings, bad_annot_settings = self.getFilterSettings(other_data)
            epoch_size = other_data['EPOCH_SIZE']

        except Exception as error:
            return ('Failed', f"Configuration could not be acquired, {str(error)}", None)

        return ('Success', "Configuration loaded successfully", (channel_settings,
                                                                 annots_left_settings, annots_right_settings, sleep_stages,
                                                                 filter_settings, bad_annot_settings,
                                                                 epoch_size))

    # --------------------------------------------------------------------------
    def getChannelSettings(self, other_data):

        row, num_cols = 0, 12
        channels_of_interest = set(list(other_data['CHANNELS_SELECTED']))

        channel_cols, channel_settings = [], []
        for i in range(len(other_data['channels_all'])):

            ch_name = other_data['channels_all'][i]

            if i // num_cols != row:
                if i > 0:
                    channel_settings.append(channel_cols)
                channel_cols = []
                row = i // num_cols

            channel_cols.append((ch_name, "checked" if ch_name in channels_of_interest else ""))

            if i == len(other_data['channels_all'])-1:
                channel_settings.append(channel_cols)

        return channel_settings

    # --------------------------------------------------------------------------
    def getSleepStageSettings(self, other_data):

        annots_right_settings = {sleep_stage: [] for sleep_stage in scv.Config.SLEEP_STAGE_ALL_NAMES}

        for annot_name in other_data['annotations_all']:
            if annot_name.lower() in other_data['sleep_stage_event_to_id_mapping']:
                for st_stage_ind in range(len(scv.Config.SLEEP_STAGE_ALL_NAMES)):
                    if other_data['sleep_stage_event_to_id_mapping'][annot_name.lower()] == scv.Config.SLEEP_STAGES_ALL[st_stage_ind]:
                        annots_right_settings[scv.Config.SLEEP_STAGE_ALL_NAMES[st_stage_ind]].append(annot_name)

        return list(other_data['annotations_all']), annots_right_settings, scv.Config.SLEEP_STAGE_ALL_NAMES

    # --------------------------------------------------------------------------
    def getFilterSettings(self, other_data):

        filter_settings = {key: value for key, value in other_data['FILTERS'].items() if key in ['notch', 'bandpass', 'amplitude_max', 'flat_signal']}

        bad_annot_keywords = {'bathroom', 'restroom', 'breakout box', 'snoring', 'cough', 'snoring', 'snore', 'movement'}

        def hasKeyword(x):
            for kw in bad_annot_keywords:
                if x.lower().find(kw) >= 0:
                    return True
            return False

        def compare(x, y):
            if hasKeyword(x) and not hasKeyword(y):
                return -1
            if not hasKeyword(x) and hasKeyword(y):
                return 1
            return x > y

        all_annots = sorted(other_data['annotations_all'], key=cmp_to_key(compare))
        bad_annots = set(other_data['FILTERS']['bad_annots'])
        bad_annot_settings = []
        for annot in all_annots:
            if annot in bad_annots:
                bad_annot_settings.append([annot, 'checked'])
            else:
                bad_annot_settings.append([annot, ''])

        return filter_settings, bad_annot_settings

    # --------------------------------------------------------------------------
    def download(self):

        try:
            import shutil

            if os.path.exists(self.FOLDER_OUTPUT + '.zip'):
                os.remove(self.FOLDER_OUTPUT + '.zip')
            shutil.make_archive(self.FOLDER_OUTPUT, 'zip', self.FOLDER_OUTPUT)
        except Exception as error:
            return ('Failed', f"Internal error occurred, {str(error)}")

        return ('Success', os.path.basename(self.FOLDER_OUTPUT + '.zip'))
