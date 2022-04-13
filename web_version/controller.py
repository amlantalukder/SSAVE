import os, sys, re
import numpy as np
import pdb

import visualize_sleep as scv

# --------------------------------------------------------------------------
class Controller():
    
    # --------------------------------------------------------------------------
    def removeOutputFiles(self):

        img_path = os.path.join(self.scv_obj.folder_cache, f'{self.scv_obj.sample_name}.jpg')
        sc_path = os.path.join(self.scv_obj.folder_cache, f'{self.scv_obj.sample_name}_sc.txt')
        st_path = os.path.join(self.scv_obj.folder_cache, f'{self.scv_obj.sample_name}_st.txt')
        eeg_path = os.path.join(self.scv_obj.folder_cache, f'{self.scv_obj.sample_name}_eeg.npy')
        spec_path = os.path.join(self.scv_obj.folder_cache, f'{self.scv_obj.sample_name}_spec_2.npy')

        if os.path.exists(img_path): os.remove(img_path)
        if os.path.exists(sc_path): os.remove(sc_path)
        if os.path.exists(st_path): os.remove(st_path)
        if os.path.exists(eeg_path): os.remove(eeg_path)
        if os.path.exists(spec_path): os.remove(spec_path)

    # --------------------------------------------------------------------------
    def validate(self, value, _type, input_name=''):

        if _type == 'file_type':
            if value in ['edf', 'annot']: return value
            print("Error!! sample type not selected")
        elif _type == 'epoch_size': return float(value)
        elif _type == 'input_file_path':
            if os.path.exists(value) and os.path.isfile(value) and os.path.splitext(value)[1].lower() in ['.edf', '.txt']: return os.path.abspath(value)
            print("Error!! invalid sample path selected")
        elif _type == 'output_folder_path':
            if os.path.exists(value) and os.path.isdir(value): return os.path.abspath(value)
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
        self.FOLDER_INPUT = os.path.join(os.path.dirname(__file__), f'static/assets/temp/input_files_{self.job_id}')
        self.FOLDER_OUTPUT = os.path.join(os.path.dirname(__file__), f'static/assets/temp/output_files_{self.job_id}')
        print(self)

    # --------------------------------------------------------------------------
    def loadSleepData(self, view):

        try:
            print(id(self), id(self.app))
            file_type = self.validate(view.form.get('file_type'), 'file_type')
            f = view.files.get('sample_file_path')
            if not os.path.exists(self.FOLDER_INPUT): os.makedirs(self.FOLDER_INPUT)
            input_file_path = os.path.join(self.FOLDER_INPUT, f.filename)
            f.save(input_file_path)
            input_file_path = self.validate(input_file_path, 'input_file_path')
            epoch_size = self.validate(view.form.get('epoch_size'), 'epoch_size')

            if (file_type is None) or (input_file_path is None) or (epoch_size is None): raise Exception

            self.scv_obj = scv.loadSleepData(input_file_path, self.FOLDER_OUTPUT, file_type, epoch_size)
            if file_type == 'edf':
                if self.scv_obj.eeg_data is None: self.scv_obj.loadEEG()
                self.annotations_all = np.sort(np.unique(self.scv_obj.eeg_data._annotations.description))
                self.channels_all = self.scv_obj.eeg_data.info['ch_names']
                if len(self.channels_all) == 0: print('No channels found !!!')
                scv.Config.CHANNELS_SELECTED = scv.Config.CHANNELS_SELECTED[np.in1d(scv.Config.CHANNELS_SELECTED, self.channels_all)]

            self.state_changed = True
        except Exception as error:
            return ('Error', f"Data loading failed, {str(error)}")

        return ('Success', "Loaded sleep data successfully")

    # --------------------------------------------------------------------------
    def getConfig(self):
        return scv.Config

    # --------------------------------------------------------------------------
    def saveSettings(self, view):
        try:
            channels_selected = np.array(view.form.getlist('channel_values'))

            new_st_mapping = {}
            for st_ind, stage in enumerate(scv.Config.SLEEP_STAGE_ALL_NAMES):
                if len(view.form.getlist(stage)) == 0: return (False, f"No annotation selected for {stage}")
                for annot in view.form.getlist(stage):
                    new_st_mapping[annot.lower()] = scv.Config.SLEEP_STAGES_ALL[st_ind]

            notch_freq = self.validate(view.form.get('notch_freq_entry'), 'frequency', input_name='Notch Frequency')
            bandpass_min_freq = self.validate(view.form.get('bandpass_min_freq_entry'), 'frequency', input_name='Bandpass Maximum Frequency')
            bandpass_max_freq = self.validate(view.form.get('bandpass_max_freq_entry'), 'frequency', input_name='Bandpass Minimum Frequency')
            amplitude_max = self.validate(view.form.get('amplitude_max_entry'), 'amplitude', input_name='Maximum Amplitude')
            flat_signal_duration = self.validate(view.form.get('flat_signal_duration_entry'), 'time', input_name='Flat Signal Duration')
            freq_std_min = self.validate(view.form.get('freq_std_min_flat_entry'), 'frequency', input_name='Minimum frequency standard deviation in flat signal duration')
            freq_std_max = self.validate(view.form.get('freq_std_min_epoch_entry'), 'frequency', input_name='Minimum frequency standard deviation in an epoch')
            bad_annots = view.form.getlist('bad_annots_list')

            if len(channels_selected) == 0:
                return (False, "No channels selected")

            if (notch_freq is None) or (bandpass_min_freq is None) or (bandpass_max_freq is None) or (amplitude_max is None) or \
                (flat_signal_duration is None) or (freq_std_min is None) or (freq_std_max is None):
                return (False, "Invalid input")

            if bandpass_max_freq < bandpass_min_freq:
                return (False, "Bandpass maximum frequency cannot be less than minimum frequency")
        
            scv.Config.CHANNELS_SELECTED = channels_selected
            scv.Config.sleep_stage_event_to_id_mapping = new_st_mapping
            scv.Config.FILTERS['notch'] = notch_freq
            scv.Config.FILTERS['bandpass'] = [bandpass_min_freq, bandpass_max_freq]
            scv.Config.FILTERS['amplitude_max'] = amplitude_max
            scv.Config.FILTERS['flat_signal'] = [flat_signal_duration, freq_std_min, freq_std_max]
            scv.Config.FILTERS['bad_annots'] = bad_annots

            self.state_changed = True

        except Exception as error:
            return ('Failed', f"Settings could not be saved, {str(error)}")

        return ('Success', "Saved Settings")

    # --------------------------------------------------------------------------
    def execute(self, view):
        print(id(self), id(self.app))
        try:
            assert self.scv_obj != None, "Sleep data not loaded properly, please try uploading the data again"

            if self.scv_obj.apply_filter != (view.form.get('apply_filter') == 'on'):
                self.scv_obj.apply_filter = (view.form.get('apply_filter') == 'on')
                self.app.logger.info(f'Apply filter: {self.scv_obj.apply_filter}')
                self.state_changed = True

            self.app.logger.info(f'State changed: {self.state_changed}')
            if self.state_changed:
                self.app.logger.info(f'Config.CHANNELS_SELECTED: {scv.Config.CHANNELS_SELECTED}')
                self.app.logger.info(f'Config.sleep_stage_event_to_id_mapping: {scv.Config.sleep_stage_event_to_id_mapping}')
                self.app.logger.info(f'Config.FILTERS: {scv.Config.FILTERS}')
                self.app.logger.info('Removing old output files')
                self.removeOutputFiles()
                self.scv_obj.clearSleepData()
                scv.extractSleepStages(self.scv_obj)
                self.state_changed = False
        except Exception as error:
            return ('Failed', f"Execution failed, {str(error)}")

        return ('Success', os.path.join(os.path.basename(self.FOLDER_OUTPUT), self.scv_obj.sample_name))

    # --------------------------------------------------------------------------
    def download(self):

        try:
            import shutil
            
            if os.path.exists(self.FOLDER_OUTPUT + '.zip'): os.remove(self.FOLDER_OUTPUT + '.zip')
            shutil.make_archive(self.FOLDER_OUTPUT, 'zip', self.FOLDER_OUTPUT)
        except Exception as error:
            return ('Failed', f"Internal error occurred, {str(error)}")

        return ('Success', os.path.basename(self.FOLDER_OUTPUT + '.zip'))