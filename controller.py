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
class DesktopUIController(Controller):

    channels_all = None
    annotations_all = None
    state_changed = True
    
    # --------------------------------------------------------------------------
    def loadSleepData(self, view):

        file_type = self.validate(view.file_type_entry.get(), 'file_type')
        input_file_path = self.validate(view.sample_path_entry.get(), 'input_file_path')
        epoch_size = self.validate(view.epoch_size_entry.get(), 'epoch_size') 
        output_folder_path = self.validate(view.output_path_entry.get(), 'output_folder_path')

        if (file_type is None) or (input_file_path is None) or (epoch_size is None) or (output_folder_path is None): return

        print(input_file_path, file_type, epoch_size, output_folder_path)

        try:
            self.scv_obj = scv.loadSleepData(input_file_path, output_folder_path, file_type, epoch_size)
            if file_type == 'edf':
                if self.scv_obj.eeg_data is None: self.scv_obj.loadEEG()
                self.annotations_all = np.sort(np.unique(self.scv_obj.eeg_data._annotations.description))
                self.channels_all = self.scv_obj.eeg_data.info['ch_names']
                if len(self.channels_all) == 0: print('No channels found !!!')
                scv.Config.CHANNELS_SELECTED = scv.Config.CHANNELS_SELECTED[np.in1d(scv.Config.CHANNELS_SELECTED, self.channels_all)]
        except:
            return False

        print('Loaded sleep data successfully ...')

        return True

    # --------------------------------------------------------------------------
    def execute(self, view):

        self.removeOutputFiles()
        self.scv_obj.clearSleepData()
        self.scv_obj.apply_filter = view.apply_filter.get()
        try:
            scv.extractSleepStages(self.scv_obj)
        except scv.SpecialError as error:
            print(error.msg)

    # --------------------------------------------------------------------------
    def setStateChange(self):
        self.state_changed=True

    # --------------------------------------------------------------------------
    def getConfig(self):
        return scv.Config

    # --------------------------------------------------------------------------
    def saveSettings(self, view):

        channels_selected = np.array([ch_name for ch_name, var in view.channel_values.items() if var.get() == True])

        for st_stage_ind, stage in enumerate(scv.Config.SLEEP_STAGES_ALL):
            no_st_selection = True
            for annot in view.annot_checkbuttons_right[st_stage_ind]:
                if view.annot_checkbuttons_right[st_stage_ind][annot]:
                    no_st_selection = False
                    scv.Config.sleep_stage_event_to_id_mapping[annot.lower()] = stage

            if no_st_selection: return (False, f"No annotation selected for {scv.Config.SLEEP_STAGE_ALL_NAMES[st_stage_ind]}")

        notch_freq = self.validate(view.notch_freq_entry.get(), 'frequency', input_name='Notch Frequency')
        bandpass_min_freq = self.validate(view.bandpass_min_freq_entry.get(), 'frequency', input_name='Bandpass Maximum Frequency')
        bandpass_max_freq = self.validate(view.bandpass_max_freq_entry.get(), 'frequency', input_name='Bandpass Minimum Frequency')
        amplitude_max = self.validate(view.amplitude_max_entry.get(), 'amplitude', input_name='Maximum Amplitude')
        flat_signal_duration = self.validate(view.flat_signal_duration_entry.get(), 'time', input_name='Flat Signal Duration')
        freq_std_min = self.validate(view.freq_std_min_flat_entry.get(), 'frequency', input_name='Minimum frequency standard deviation in flat signal duration')
        freq_std_max = self.validate(view.freq_std_min_epoch_entry.get(), 'frequency', input_name='Minimum frequency standard deviation in an epoch')
        bad_annots = [view.bad_annots_list.get(i) for i in view.bad_annots_list.curselection()]

        if len(channels_selected) == 0:
            return (False, "No channels selected")

        if (notch_freq is None) or (bandpass_min_freq is None) or (bandpass_max_freq is None) or (amplitude_max is None) or \
            (flat_signal_duration is None) or (freq_std_min is None) or (freq_std_max is None):
            return (False, "Invalid input")

        if bandpass_max_freq < bandpass_min_freq:
            return (False, "Bandpass maximum frequency cannot be less than minimum frequency")

        scv.Config.FILTERS['notch'] = notch_freq
        scv.Config.FILTERS['bandpass'] = [bandpass_min_freq, bandpass_max_freq]
        scv.Config.FILTERS['amplitude_max'] = amplitude_max
        scv.Config.FILTERS['flat_signal'] = [flat_signal_duration, freq_std_min, freq_std_max]
        scv.Config.FILTERS['bad_annots'] = bad_annots
        scv.Config.CHANNELS_SELECTED = channels_selected

        #print(scv.Config.sleep_stage_event_to_id_mapping)

        self.setStateChange()

        return (True, "Saved Settings")

# --------------------------------------------------------------------------
class WebUIController(Controller):

    channels_all = None
    annotations_all = None
    state_changed = True
    scv_obj = None

    FOLDER_INPUT = os.path.join(os.path.dirname(__file__), 'static/assets/temp/input_files')
    FOLDER_OUTPUT = os.path.join(os.path.dirname(__file__), 'static/assets/temp/output_files')

    def __init__(self, app):
        self.app = app
    
    # --------------------------------------------------------------------------
    def loadSleepData(self, view):

        try:
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
    
        if self.scv_obj.apply_filter != (view.form.get('apply_filter') == 'on'):
            self.scv_obj.apply_filter = (view.form.get('apply_filter') == 'on')
            self.app.logger.info(f'Apply filter: {self.scv_obj.apply_filter}')
            self.state_changed = True
        try:
            self.app.logger.info(f'State changed: {self.state_changed}')
            if self.state_changed:
                self.app.logger.info(f'Config.CHANNELS_SELECTED: {scv.Config.CHANNELS_SELECTED}')
                self.app.logger.info(f'Config.sleep_stage_event_to_id_mapping: {scv.Config.sleep_stage_event_to_id_mapping}')
                self.app.logger.info(f'Config.FILTERS: {scv.Config.FILTERS}')
                self.removeOutputFiles()
                self.scv_obj.clearSleepData()
                scv.extractSleepStages(self.scv_obj)
                self.state_changed = False
        except Exception as error:
            return ('Failed', f"Execution failed, {str(error)}")

        return ('Success', "Execution complete")

    # --------------------------------------------------------------------------
    def download(self):

        try:
            import shutil
            
            if os.path.exists(self.FOLDER_OUTPUT + '.zip'): os.remove(self.FOLDER_OUTPUT + '.zip')
            shutil.make_archive(self.FOLDER_OUTPUT, 'zip', self.FOLDER_OUTPUT)
        except Exception as error:
            return ('Failed', f"Internal error occurred, {str(error)}")

        return ('Success', 'Download link prepared')

# --------------------------------------------------------------------------
class CLIController(Controller):

    # --------------------------------------------------------------------------
    def loadSleepData(self, view):

        input_file_path = self.validate(input('Enter Sample Path: '), 'input_file_path')
        while input_file_path is None:
            input_file_path = self.validate(input('Enter Sample Path: '), 'input_file_path')

        file_type = input('Select File Type: 1. EDF format 2. Annotation epochs: ') 
        while file_type not in ['1', '2']: 
            file_type = input('Select File Type: 1. EDF format 2. Annotation epochs: ') 
        file_type = 'edf' if file_type == '1' else 'annot'
        
        epoch_size =  self.validate(input('Enter Epoch Size: '), 'epoch_size')

        output_folder_path =  self.validate(input('Enter Output Folder Path: '), 'output_folder_path')
        while output_folder_path is None:
            output_folder_path =  self.validate(input('Enter Output Folder Path: '), 'output_folder_path')

        apply_filter =  input('Apply Filter: 1. Yes 2. No: ')
        while apply_filter not in ['1', '2']:
            apply_filter = input('Apply Filter: 1. Yes 2. No: ') 
        apply_filter = True if apply_filter == '1' else False

        if (file_type is None) or (input_file_path is None) or (epoch_size is None) or (output_folder_path is None): return

        print(input_file_path, file_type, epoch_size, output_folder_path)

        try:
            self.scv_obj = scv.loadSleepData(input_file_path, output_folder_path, file_type, epoch_size)
            self.scv_obj.apply_filter = apply_filter
            if file_type == 'edf':
                if self.scv_obj.eeg_data is None: self.scv_obj.loadEEG()
                self.annotations_all = np.sort(np.unique(self.scv_obj.eeg_data._annotations.description))
                self.channels_all = self.scv_obj.eeg_data.info['ch_names']
                if len(self.channels_all) == 0: print('No channels found !!!')
                scv.Config.CHANNELS_SELECTED = scv.Config.CHANNELS_SELECTED[np.in1d(scv.Config.CHANNELS_SELECTED, self.channels_all)]
        except:
            return False

        print('Loaded sleep data successfully ...')

        return True

    # --------------------------------------------------------------------------
    def execute(self, view):

        self.removeOutputFiles()
        self.scv_obj.clearSleepData()
        try:
            scv.extractSleepStages(self.scv_obj)
        except scv.SpecialError as error:
            print(error.msg)