import numpy as np
import mne, os, sys, pdb
from scipy.signal import detrend
from matplotlib.patches import Rectangle
from datetime import timedelta, datetime
from utils import Config, plt, loadFileNames, createDir, showPercBar, readFileInTable, writeDataTableAsText
import tkinter as tk

class SpecialError(Exception):
    def __init__(self, msg):
        self.msg = msg

# -------------------------------------------
class SleepInfo:

    sample_name = None
    edf_file_path = None
    annot_file_path = None
    eeg_data = None
    annotations = None
    sampling_freq = None
    ch_names = None
    eeg_data_epoch_wise = None
    sleep_stages_epoch_wise = None
    sleep_cycles = None
    spectogram = None
    epoch_size = 30
    enable_cache = False
    use_cache = True
    #folder_cache = f'{Config.FOLDER_PROCESSED_DATA}/sleep_data_epoch_wise_shifted'
    #folder_cache = '/ddn/gs1/group/li3/DataFromLLI/SleepData_UNC/UNC_data/sleep_cycles_with_spectograms/all_samples/shifted'
    folder_cache = 'temp'
    shift_len = 0
    apply_filter = False
    bad_epoch_indices = []

    # --------------------------------------------------------------------------
    # Initialize object with sample name and epoch size (optional)
    # --------------------------------------------------------------------------
    def __init__(self, sample_name, edf_file_path=None, annot_file_path=None, input_file_type=None, use_cache = True):
        self.sample_name = sample_name
        self.edf_file_path = edf_file_path
        self.annot_file_path = annot_file_path
        self.input_file_type = input_file_type
        self.use_cache = use_cache

    # --------------------------------------------------------------------------
    # Print customized message
    # --------------------------------------------------------------------------
    def printDec(self, msg):

        horizontal_border = '_' * 50
        vertical_border = '|'

        l = len(horizontal_border)

        print(horizontal_border)
        print(' ' * l)
        msg_part = msg.strip()
        while len(msg_part) >= l - 4:
            print(vertical_border + ' ' + msg_part[:l - 4] + ' ' + vertical_border)
            msg_part = msg_part[l - 4:].strip()
        print(vertical_border + ' ' + msg_part + ' ' * (l - 3 - len(msg_part)) + vertical_border)
        print(horizontal_border)
        print("")

    # --------------------------------------------------------------------------
    # Read eeg signal data
    # --------------------------------------------------------------------------
    def loadEEG(self):

        printDec('Loading eeg data')

        # --------------------------------------------------------------------------
        # Read eeg signal data
        # --------------------------------------------------------------------------
        #self.edf_file_path = 'test_edf.edf'
        #self.edf_file_path = f'{self.folder_cache}/{self.sample_name}_al.edf'
        self.eeg_data = mne.io.read_raw_edf(self.edf_file_path, verbose=False)
        
        self.sampling_freq = float(self.eeg_data.info['sfreq'])

        self.ch_names = list(Config.CHANNELS_SELECTED[np.in1d(Config.CHANNELS_SELECTED, self.eeg_data.info['ch_names'])])
        print(f'Selected channels: {", ".join(self.ch_names)}')

        self.eeg_data_raw = self.eeg_data.get_data(picks=self.ch_names)
        
        '''
        self.eeg_data_raw *= 1e6
        self.eeg_data_raw = np.array([
            self.eeg_data_raw[ch_names.index('F3')] - self.eeg_data_raw[ch_names.index('M2')],
            self.eeg_data_raw[ch_names.index('F4')] - self.eeg_data_raw[ch_names.index('M1')],
            self.eeg_data_raw[ch_names.index('C3')] - self.eeg_data_raw[ch_names.index('M2')],
            self.eeg_data_raw[ch_names.index('C4')] - self.eeg_data_raw[ch_names.index('M1')],
            self.eeg_data_raw[ch_names.index('O1')] - self.eeg_data_raw[ch_names.index('M2')],
            self.eeg_data_raw[ch_names.index('O2')] - self.eeg_data_raw[ch_names.index('M1')],
        ])
        '''

    # --------------------------------------------------------------------------
    # Apply a series of filters on EEG data
    # --------------------------------------------------------------------------
    def applyFilterOnEEG(self):

        print(Config.FILTERS)

        if self.sampling_freq/2 > Config.FILTERS['notch']:
            self.eeg_data_epoch_wise = mne.filter.notch_filter(self.eeg_data_epoch_wise, self.sampling_freq, Config.FILTERS['notch'], fir_design="firwin", verbose=False)

        fmin = Config.FILTERS['bandpass'][0]
        fmax = Config.FILTERS['bandpass'][1]
        if fmax >= self.sampling_freq/2: fmax = None
        self.eeg_data_epoch_wise = mne.filter.filter_data(self.eeg_data_epoch_wise, self.sampling_freq, fmin, fmax, fir_design="firwin", verbose=False)

        bad_epochs = self.bad_epoch_indices

        nan2d = np.any(np.isnan(self.eeg_data_epoch_wise), axis=2)
        nan1d = np.where(np.any(nan2d, axis=1))[0]
        bad_epochs = np.r_[bad_epochs, nan1d]

        amplitude_large2d = np.any(np.abs(self.eeg_data_epoch_wise) > Config.FILTERS['amplitude_max'], axis=2)  #(#epoch, 6)
        amplitude_large1d = np.where(np.any(amplitude_large2d, axis=1))[0] #(#epoch,)
        bad_epochs = np.r_[bad_epochs, amplitude_large1d]

        # if there is any flat signal with flat_length
        flat_duration, std_thres, std_thres2 = Config.FILTERS['flat_signal']
        flat_length = int(round(flat_duration*self.sampling_freq))
            
        a, b, c = self.eeg_data_epoch_wise.shape
        short_segs = self.eeg_data_epoch_wise.reshape(a, b, c//flat_length, flat_length)
        flat2d = np.any(detrend(short_segs, axis=3).std(axis=3) <= std_thres, axis=2)
        flat2d = np.logical_or(flat2d, np.std(self.eeg_data_epoch_wise, axis=2) <= std_thres2)
        flat1d = np.where(np.any(flat2d, axis=1))[0]
        bad_epochs = np.r_[bad_epochs, flat1d]
        
        bad_epochs = np.unique(bad_epochs).astype(int)
        indices = np.delete(np.arange(self.eeg_data_epoch_wise.shape[0]), bad_epochs)
        
        if len(indices) == 0: raise SpecialError("All epochs are filtered out !!! Nothing to show...")
        
        self.eeg_data_epoch_wise = self.eeg_data_epoch_wise[indices]
        self.sleep_stages_epoch_wise = self.sleep_stages_epoch_wise[indices]

        print(f'{len(bad_epochs)} epochs were filtered out')

    # --------------------------------------------------------------------------
    # Extract epoch wise data from the event info of the eeg data
    # --------------------------------------------------------------------------
    def extractEpochsFromAnnots(self):

        if self.eeg_data is None: self.loadEEG()

        eeg_data_path = f'{self.folder_cache}/{self.sample_name}_eeg.npy'
        sleep_stage_path = f'{self.folder_cache}/{self.sample_name}_st.txt'

        self.annotations = self.eeg_data._annotations
        whole_annotations = np.concatenate([self.annotations.onset[:, None].astype(object), self.annotations.duration[:, None].astype(object), self.annotations.description[:, None].astype(object)], axis=1)#, dtype=object)

        # --------------------------------------------------------------------------
        # Set window size
        # --------------------------------------------------------------------------
        window_size = int(self.epoch_size * self.sampling_freq)

        # --------------------------------------------------------------------------
        # Extract epoch wise annotations and signal data
        # --------------------------------------------------------------------------
        bad_epochs, sleep_epoch_indices = set(), []
        bad_annots = set(Config.FILTERS['bad_annots'])
        self.sleep_stages_epoch_wise, self.eeg_data_epoch_wise = [], []
        for t, d, desc in whole_annotations:
    
            epoch_id = int(t//self.epoch_size)
            n_epochs = int(d//self.epoch_size)

            # Check if this is a sleep stage annotation
            if desc.lower() not in Config.sleep_stage_event_to_id_mapping:
                if desc in bad_annots: bad_epochs |= {i for i in range(epoch_id, epoch_id + n_epochs + 1)}
                continue
            label = Config.sleep_stage_event_to_id_mapping[desc.lower()]
            
            for j in range(n_epochs):
                sleep_epoch_indices.append(epoch_id + j)
                self.sleep_stages_epoch_wise.append(label)
                index_raw = int((epoch_id + j) * window_size)
                self.eeg_data_epoch_wise.append(self.eeg_data_raw[:, index_raw : index_raw + window_size])

        self.sleep_stages_epoch_wise, self.eeg_data_epoch_wise = np.array(self.sleep_stages_epoch_wise), np.array(self.eeg_data_epoch_wise)

        # --------------------------------------------------------------------------
        # Extract epochs with bad annotations
        # --------------------------------------------------------------------------
        self.bad_epoch_indices = [i for i, epoch in enumerate(sleep_epoch_indices) if epoch in bad_epochs]
        if self.apply_filter: self.applyFilterOnEEG()

        # --------------------------------------------------------------------------
        # Save annotations and signal data
        # --------------------------------------------------------------------------
        writeDataTableAsText(self.sleep_stages_epoch_wise[:, None], sleep_stage_path)
        if self.enable_cache:
            np.save(eeg_data_path, self.eeg_data_epoch_wise)

    # --------------------------------------------------------------------------
    # Load epoch wise data from the annotation path provided
    # --------------------------------------------------------------------------
    def extractEpochsFromTextAnnots(self):
        self.sleep_stages_epoch_wise = [item[0] for item in readFileInTable(self.annot_file_path)]

        # --------------------------------------------------------------------------
        # Save annotations
        # --------------------------------------------------------------------------
        sleep_stage_path = f'{self.folder_cache}/{self.sample_name}_st.txt'
        writeDataTableAsText(np.array(self.sleep_stages_epoch_wise)[:, None], sleep_stage_path)

    # --------------------------------------------------------------------------
    # Extract epoch wise data
    # --------------------------------------------------------------------------
    def extractEpochs(self):

        eeg_data_path = f'{self.folder_cache}/{self.sample_name}_eeg.npy'
        sleep_stage_path = f'{self.folder_cache}/{self.sample_name}_st.txt'
  
        if self.use_cache and (os.path.exists(eeg_data_path) and os.path.exists(sleep_stage_path)):
            self.eeg_data_epoch_wise = np.load(eeg_data_path)
            self.sleep_stages_epoch_wise = [item[0] for item in readFileInTable(sleep_stage_path)]
            return

        printDec('Extracting epoch wise data')

        if not (self.annot_file_path is None):
            self.extractEpochsFromTextAnnots()
        else:
            self.extractEpochsFromAnnots()

    # --------------------------------------------------------------------------
    # Extract spectogram data
    # --------------------------------------------------------------------------
    def extractSpectogram(self, fmin=0, fmax=30, nw=2):

        if not (self.spectogram is None or self.spec_freq is None): return

        spectogram_path = f'{self.folder_cache}/{self.sample_name}_spec_{nw}.npz'
        if self.use_cache and os.path.exists(spectogram_path):
            data = np.load(spectogram_path)
            self.spectogram, self.spec_freq = data['spec'], data['spec_freq']
            return

        if self.eeg_data_epoch_wise is None: self.extractEpochs()
        if self.sampling_freq is None: self.loadEEG()

        printDec('Extracting spectogram')
        
        #nw = 2 #Sun uses 10. The smaller the better the resolution.
        bw = nw*2./self.epoch_size
  
        self.spectogram, self.spec_freq = mne.time_frequency.psd_array_multitaper(self.eeg_data_epoch_wise, self.sampling_freq, \
            fmin=fmin, fmax=fmax, adaptive=False, low_bias=True, n_jobs=1, verbose='ERROR', bandwidth=bw, normalization='full')
        self.spectogram = self.spectogram.transpose(0,2,1)

        if self.enable_cache: np.savez(spectogram_path, spec = self.spectogram, spec_freq = self.spec_freq)

    # --------------------------------------------------------------------------
    # Find cut options of long NREMP cycles
    # --------------------------------------------------------------------------
    def getCutOptions(self):

        # --------------------------------------------------------------------------
        def getGroupWiseCounts(arr):
            group, count = [], 0
            for i in range(len(arr)):
                count += 1
                if i == len(arr)-1 or arr[i] != arr[i+1]:
                    group.append((arr[i], count))
                    count = 0
            return group

        # --------------------------------------------------------------------------
        def getCutOptionsPerCycle(sleep_stage_durations, total_duration_non_w):
            cut_options = []
            index = 0
            duration_non_w = 0
            for stage, duration in sleep_stage_durations:
                if stage != Config.WAKE_STAGE: duration_non_w += duration
                if ((stage == Config.WAKE_STAGE and duration >= 2) or (stage == Config.N1_STAGE and duration >= 7)) and \
                    ((stage == Config.WAKE_STAGE and duration_non_w > 10 and (total_duration_non_w - duration_non_w) > 10) or \
                        (stage == Config.N1_STAGE and (duration_non_w - duration) > 10 and (total_duration_non_w - duration_non_w) > 10)):
                    cut_options.append(index)
                index += duration
            return cut_options

        # --------------------------------------------------------------------------
        # f. If a sleep cycle (usually NC) is longer than 120 minutes (240 epoch), 
        #   break it into two NC cycles, using either awake (>= 1 minute* or 2 epochs) or N1 (> 3 minutes* or 6 epochs)
        # g. In the middle of a sleep cycle, if wake is < 3 minutes* (6 epochs), do not break the cycle.
        # --------------------------------------------------------------------------
        sleep_cycle_durations = getGroupWiseCounts(self.sleep_cycles)

        start_epoch = 0
        cut_options_all = []
        
        for i, ([sc_id, sc], duration) in enumerate(sleep_cycle_durations):
            if sc == 'NREMP' and duration > 240:

                end_epoch = start_epoch + duration
                
                sleep_stages_epoch_wise = self.sleep_stages_epoch_wise[start_epoch:end_epoch]
                sleep_stage_durations = getGroupWiseCounts(sleep_stages_epoch_wise)
                duration_w = sum([d for stage, d in sleep_stage_durations if stage == Config.WAKE_STAGE])
                duration_without_w = duration - duration_w
    
                if duration > 240 and duration_w >= 6:

                    cut_options = np.array(getCutOptionsPerCycle(sleep_stage_durations, duration_without_w)) + start_epoch
                    if len(cut_options): print(f'NREMP (cycle {sc_id}) can be cut at {cut_options[:]}')

                    cut_options_all += list(cut_options)

            start_epoch += duration

        return cut_options_all

    # --------------------------------------------------------------------------
    # Extract sleep cycles
    # --------------------------------------------------------------------------
    def extractSleepCycles(self):

        if not (self.sleep_cycles is None): return

        sleep_cycles_path = f'{self.folder_cache}/{self.sample_name}_sc.txt'
        if self.use_cache and os.path.exists(sleep_cycles_path):
            self.sleep_cycles = readFileInTable(sleep_cycles_path)
            return

        printDec('Extracting sleep cycles')

        # ----------------------------------------------------
        # Remove non sleep stages
        # ----------------------------------------------------
        sleep_stages_epoch_wise = [stage for stage in self.sleep_stages_epoch_wise if stage in Config.SLEEP_STAGE_ANNOTS]
            
        # ----------------------------------------------------
        # Get the consecutive NREM and REM sleep epoch counts
        # ----------------------------------------------------
        consecutive_epochs = []
        count_sc, current_cycle = 0, None
        for i in range(len(sleep_stages_epoch_wise)):
            count_sc += 1
            if current_cycle is None: current_cycle = 'REMP' if sleep_stages_epoch_wise[i] == Config.REM_STAGE else 'NREMP'
            if (i == len(sleep_stages_epoch_wise)-1) or (sleep_stages_epoch_wise[i] != sleep_stages_epoch_wise[i+1]):            
                if (i < len(sleep_stages_epoch_wise)-1):
                    if current_cycle == "NREMP" and sleep_stages_epoch_wise[i+1] == Config.REM_STAGE:
                        consecutive_epochs.append((current_cycle, count_sc))
                        count_sc, current_cycle = 0, 'REMP'
                    elif current_cycle == "REMP" and (sleep_stages_epoch_wise[i+1] != Config.REM_STAGE and sleep_stages_epoch_wise[i+1] != Config.WAKE_STAGE):
                        consecutive_epochs.append((current_cycle, count_sc))
                        count_sc, current_cycle = 0, 'NREMP'
                else:
                    consecutive_epochs.append(('REMP' if (current_cycle == 'REMP') else 'NREMP', count_sc))
                    count_sc = 0
    
        # ----------------------------------------------------
        # Get sleep cycles following a set of rules
        # 1. The first REM of any size is counted as REMP. 
        #    Otherwise, (N)REMP is followed by more than 5 min (10 epochs) of (N)REM (Ex: 20-2386_F_48.6_1_di)
        # 2. NREMP will always start with a NREM stage (N1, N2 or N3). (Ex: 19-0599_M_5.4_1_di)
        # 3. For the first NREMP, the initial "W" stages are skipped
        # 4. For the last (N)REMP, the trailing "W" stages are skipped 
        # ----------------------------------------------------

        sleep_cycles = []
        is_first_rem = True
        sc_index = 1
        i = 0
        while i < len(consecutive_epochs):
            
            stage_sc, count = consecutive_epochs[i]

            if stage_sc == 'REMP' and (is_first_rem or count >= 10):
                is_first_rem = False
                sc = 'REMP'
            else:
                sc = 'NREMP'
                
            count_sc = 0
            while i < len(consecutive_epochs):
                stage_sc, count = consecutive_epochs[i]
                count_sc += count
        
                if i >= len(consecutive_epochs)-1 or \
                (consecutive_epochs[i+1][0] != sc and \
                    (consecutive_epochs[i+1][1] > 10 or \
                        (consecutive_epochs[i+1][0] == 'REMP' and is_first_rem))):
                    i += 1
                    break
                i += 1

            sleep_cycles += [[sc_index, sc]]*count_sc
            sc_index += 1
        
        assert len(sleep_stages_epoch_wise) == len(sleep_cycles), "Sleep Cycle length does not match with hypnogram !!!"

        # Remove initial wake stages
        for i in range(len(sleep_stages_epoch_wise)):
            if sleep_stages_epoch_wise[i] != Config.WAKE_STAGE: break
            sleep_cycles[i] = ['NA', 'NA']
        
        # Remove final wake stages
        for i in range(len(sleep_stages_epoch_wise)-1, -1, -1):
            if sleep_stages_epoch_wise[i] != Config.WAKE_STAGE: break
            sleep_cycles[i] = ['NA', 'NA']

        # ----------------------------------------------------
        # Add "NA" for non sleep stages to keep up with the 
        # number of epochs  
        # ----------------------------------------------------
        self.sleep_cycles = []
        j = 0
        for i in range(len(self.sleep_stages_epoch_wise)):
            if self.sleep_stages_epoch_wise[i] in Config.SLEEP_STAGE_ANNOTS:
                self.sleep_cycles.append(sleep_cycles[j])
                j += 1
            else:
                self.sleep_cycles.append(['NA', 'NA'])
        
        writeDataTableAsText(self.sleep_cycles, sleep_cycles_path)

    # --------------------------------------------------------------------------
    # Generate visualization plots
    # --------------------------------------------------------------------------
    def generatePlot(self, sleep_stage_levels, sleep_stage_colors=None, title='', fig_path=None):
        """Generates Plot
        """

        printDec('Generating plot')

        if sleep_stage_colors is None: sleep_stage_colors = {stage:'k' for stage in sleep_stage_levels}

        y_ticklabels, y_ticks = list(sleep_stage_levels.keys()), list(sleep_stage_levels.values())

        fig = plt.figure(figsize=(12, 9), dpi=Config.PLOT_DPI)

        if not (self.spectogram is None):
            gs = fig.add_gridspec(2, 1, height_ratios=[2,2])
            ax_ss = fig.add_subplot(gs[0])
        else:
            gs = fig.add_gridspec(1, 1)
            ax_ss = fig.add_subplot(gs[0])

        x, y = [], []

        if self.shift_len > 0:  title += f' (shifted {self.shift_len} epochs)'
        
        for i in range(len(self.sleep_stages_epoch_wise)):
            x.append(i)
            y.append(sleep_stage_levels[self.sleep_stages_epoch_wise[i]])
        
            if (i == len(self.sleep_stages_epoch_wise)-1) or \
                (sleep_stage_levels[self.sleep_stages_epoch_wise[i]] != sleep_stage_levels[self.sleep_stages_epoch_wise[i+1]]):

                if (i < len(self.sleep_stages_epoch_wise)-1):
                    x.append(i+1)
                    y.append(sleep_stage_levels[self.sleep_stages_epoch_wise[i+1]])

                ax_ss.plot(x, y, color=sleep_stage_colors[self.sleep_stages_epoch_wise[i]], marker='o')
                x, y = [], []
    
        if not (self.sleep_cycles is None):
            
            max_level = max(list(sleep_stage_levels.values()))
            sc_labels = sorted(set([stage_sc for _, stage_sc in self.sleep_cycles if stage_sc != 'NA']))
            sc_levels = {sc_label:max_level + 1 + i for i, sc_label in enumerate(sc_labels)}
            y_ticklabels += sc_labels
            y_ticks += sorted(sc_levels.values())

            x_sc = []
            index_overlay_anchor = None

            for i in range(len(self.sleep_cycles)):
                cycle, stage_sc = self.sleep_cycles[i]

                if index_overlay_anchor is None: index_overlay_anchor = i

                if stage_sc != 'NA': 
                    x_sc.append(i)
                    if (i == len(self.sleep_stages_epoch_wise)-1) or (self.sleep_stages_epoch_wise[i] != self.sleep_stages_epoch_wise[i+1]):
                        if (i < len(self.sleep_stages_epoch_wise)-1) and stage_sc == self.sleep_cycles[i+1][1]: x_sc.append(i+1)
                        ax_ss.plot(x_sc, [sc_levels[stage_sc]]*len(x_sc), color=sleep_stage_colors[self.sleep_stages_epoch_wise[i]], marker='o', markersize=3)
                        x_sc = []

                if (i == len(self.sleep_cycles)-1) or (stage_sc != self.sleep_cycles[i+1][1]):
                    if stage_sc != 'NA':
                        if stage_sc == 'NREMP':
                            overlay = Rectangle((index_overlay_anchor, 0), i-index_overlay_anchor, max_level, fill=True, color='darkgrey', alpha=0.5)
                        else:
                            overlay = Rectangle((index_overlay_anchor, 0), i-index_overlay_anchor, max_level, fill=True, color='darkgrey', alpha=0.3)    
                        plt.gca().add_patch(overlay)
                    index_overlay_anchor = i

            if 'NREMP' in sc_levels: ax_ss.vlines(self.getCutOptions(), 0, sc_levels['NREMP'], linestyles='dashed', colors='black')

        ax_ss.tick_params(axis='x', labelsize=Config.PLOT_TICKLABEL_FONT_SIZE)
        ax_ss.set_yticks(y_ticks)
        ax_ss.set_yticklabels(y_ticklabels, fontsize=Config.PLOT_TICKLABEL_FONT_SIZE)
        #ax_ss.set_xlabel('Epochs', fontsize=Config.PLOT_LABEL_FONT_SIZE)
        ax_ss.set_ylim(min(y_ticks)-0.5, max(y_ticks)+0.5)
        ax_ss.set_ylabel('Sleep Stages', fontsize=Config.PLOT_LABEL_FONT_SIZE)
        ax_ss.grid(True)
        
        if not (self.spectogram is None):
            ax_spec = fig.add_subplot(gs[1], sharex=ax_ss)
            tt = np.arange(self.spectogram.shape[0])
            self.spectogram[np.where(self.spectogram==0)] = np.nan
            specs_db = 10*np.log10(self.spectogram)
            specs_db = specs_db.mean(axis=-1)  # average across channels
            qmin, qmax = np.nanpercentile(specs_db, (5, 95))
            im = ax_spec.imshow(
                    specs_db.T, aspect='auto', origin='lower', cmap='jet',
                    vmin=qmin, vmax=qmax,
                    extent=(tt.min(), tt.max(), self.spec_freq.min(), self.spec_freq.max()))
            ax_spec.tick_params(axis='both', labelsize=Config.PLOT_TICKLABEL_FONT_SIZE)
            ax_spec.set_ylabel('Frequency (Hz)', fontsize=Config.PLOT_LABEL_FONT_SIZE)
            ax_spec.set_xlabel('Epochs', fontsize=Config.PLOT_LABEL_FONT_SIZE)
            cax = fig.add_axes([0.91, 0.18, 0.02, 0.2])
            fig.colorbar(im, cax=cax, orientation='vertical')

        fig.suptitle(title, fontsize=Config.PLOT_TITLE_FONT_SIZE)
        #fig.tight_layout()
        if not fig_path: plt.show()
        else:
            createDir(fig_path, is_file_path=True)
            plt.savefig(fig_path)
            plt.close()

    # --------------------------------------------------------------------------
    def clearSleepData(self):

        self.eeg_data = None        
        self.sleep_cycles = None
        self.spectogram = None
        self.spec_freq = None
        
    # --------------------------------------------------------------------------
    def visualize(self, show_sc=False, show_spec=False):

        sleep_stage_colors = {Config.WAKE_STAGE:'limegreen', Config.REM_STAGE:'gold', Config.N1_STAGE:'deepskyblue', \
            Config.N2_STAGE:'royalblue', Config.N3_STAGE:'darkblue'}#, Config.U_STAGE:'black'}#, 'O':'red', 'NA':'orange'}

        self.extractEpochs()
        if show_spec: self.extractSpectogram(nw=2)
        if show_sc: self.extractSleepCycles()

        fig_path = f'{self.folder_cache}/{self.sample_name}.jpg'
        #fig_path = f'{Config.FOLDER_PROCESSED_DATA}/temp2/{self.sample_name}.jpg'

        self.generatePlot(Config.SLEEP_STAGE_ANNOTS_ALL, sleep_stage_colors=sleep_stage_colors, title=self.sample_name, fig_path=fig_path)

# --------------------------------------------------------------------------
def printDec(msg):
    print(msg)
    return

    horizontal_border = '_' * 50
    vertical_border = '|'

    l = len(horizontal_border)

    print(horizontal_border)
    print(' ' * l)
    msg_part = msg.strip()
    while len(msg_part) >= l - 4:
        print(vertical_border + ' ' + msg_part[:l - 4] + ' ' + vertical_border)
        msg_part = msg_part[l - 4:].strip()
    print(vertical_border + ' ' + msg_part + ' ' * (l - 3 - len(msg_part)) + vertical_border)
    print(horizontal_border)
    print("")

# --------------------------------------------------------------------------
def loadSleepData(input_file_path, output_folder_path, input_file_type="edf", epoch_size=30, apply_filter=False):

    edf_file_path, annot_file_path = None, None

    if input_file_type == 'edf':
        file_name = os.path.basename(input_file_path)
        edf_file_path = input_file_path
    elif input_file_type == 'annot':
        file_name = os.path.basename(input_file_path)
        annot_file_path = input_file_path
    else:
        print(f'No valid input provided !!!')
        return

    printDec('Processing ' + file_name)

    sample_name, _ = os.path.splitext(file_name)

    # --------------------------------------------------------------------------
    # Read eeg signal data and annotation files
    # --------------------------------------------------------------------------
 
    sleep_obj = SleepInfo(sample_name=sample_name, edf_file_path=edf_file_path, annot_file_path=annot_file_path, input_file_type=input_file_type, use_cache=False)
    sleep_obj.epoch_size = epoch_size
    sleep_obj.folder_cache = output_folder_path

    return sleep_obj

# --------------------------------------------------------------------------
def extractSleepStages(sleep_obj):

    if sleep_obj.input_file_type == 'edf': 
        sleep_obj.visualize(show_sc=True, show_spec=True)
    elif sleep_obj.input_file_type == 'annot':
        sleep_obj.visualize(show_sc=True, show_spec=False)
    else:
        print('Invalid input file type !!!')

# --------------------------------------------------------------------------
if __name__ == '__main__':
    edf_file_path = f"temp/19-0328_F_42.3_1_di_al.edf"
    annot_file_path = f"temp/19-0328_F_42.3_1_di_al.txt"
    try:
        extractSleepStages(loadSleepData(edf_file_path, annot_file_path))
    except SpecialError as error:
        print(error.msg)
    