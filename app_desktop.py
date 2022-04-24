import os, sys, re
import tkinter as tk
from tkinter import Tk, ttk, font, filedialog, scrolledtext, messagebox
import numpy as np
import pdb

from utils import readFileInTable
from PIL import ImageTk, Image
from controller import DesktopUIController, CLIController
    
# --------------------------------------------------------------------------
class TextRedirector(object):

    def __init__(self, view):
        self.view = view

    def write(self, msg):
        self.view.status_textarea.config(state=tk.NORMAL)
        self.view.status_textarea.insert(tk.END, msg)
        self.view.master.update()
        self.view.status_textarea.config(state=tk.DISABLED)

# --------------------------------------------------------------------------
class Dialog:

    def __init__(self, master: Tk, width, height):

        # Set window
        self.master = master
        self.width = width
        self.height = height
  
        # Set font
        self.font_name = 'Default'
        self.font_size = 15
        self.defaultFont = font.nametofont("TkDefaultFont")
        self.defaultFont.configure(family=self.font_name, size=self.font_size)

# --------------------------------------------------------------------------
class SettingsDialog(Dialog):

    controller = None

    # --------------------------------------------------------------------------
    def __init__(self, master, controller):
        
        master = tk.Toplevel(master)
        master.title('SCVIS - Settings')
        master.geometry("900x800+450+150")

        super().__init__(master, 900, 800)

        self.controller = controller

        self.setSettingsUI()
        self.setChannelSelectionPanel()
        self.setSleepStageSelectionPanel()
        self.setFilterSettingsPanel()
        self.setEpochSizePanel()

        master.mainloop()

    # --------------------------------------------------------------------------
    def setSettingsUI(self):

        tab_control = ttk.Notebook(self.master, width=self.width-20, height=self.height-120)
        tab_control.pack(fill=tk.X)

        self.ch_sel = tk.Frame(tab_control, borderwidth=1, relief='solid')
        self.st_sel = tk.Frame(tab_control, borderwidth=1, relief='solid')
        self.filter_sel = tk.Frame(tab_control, borderwidth=1, relief='solid')
        self.epoch_sel = tk.Frame(tab_control, borderwidth=1, relief='solid')

        tab_control.add(self.ch_sel, text='Select Channels')
        tab_control.add(self.st_sel, text='Select Sleep Stages')
        tab_control.add(self.filter_sel, text='Set Filters')
        tab_control.add(self.epoch_sel, text='Set Epoch Size')

        ttk.Button(self.master, text="Save", command=self.saveSettings).pack(pady=(0, 10))

    # --------------------------------------------------------------------------
    def setChannelSelectionPanel(self):

        if self.controller.channels_all is None: return

        self.select_all_channels_btn = ttk.Button(self.ch_sel, text='Select All', command=lambda : self.selectAllChannels(True))
        self.select_all_channels_btn.pack(pady=10)

        ch_panel = ttk.Frame(self.ch_sel, borderwidth=1, relief='solid')
        ch_panel.pack(expand=1, fill=tk.X, anchor="nw", padx=10, pady=10)

        config = self.controller.getConfig()

        num_cols = 6
        channels_of_interest = set(list(config.CHANNELS_SELECTED))
        self.channel_values = {}
        for i in range(len(self.controller.channels_all)):
            ch_name = self.controller.channels_all[i]
            self.channel_values[ch_name] = tk.BooleanVar()
            row = int(i/num_cols)
            col = int(i%num_cols)

            ch_panel_col = tk.Frame(ch_panel)
            ch_panel_col.grid(row=row, column=col)
            tk.Checkbutton(ch_panel_col, text=ch_name, variable=self.channel_values[ch_name], 
                            onvalue=True, offvalue=False, font=(self.font_name, self.font_size)).pack()
            
            if ch_name in channels_of_interest:
                self.channel_values[ch_name].set(value=True)

        ch_panel.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

    # --------------------------------------------------------------------------
    def setSleepStageSelectionPanel(self):

        annotation_panel = ttk.Frame(self.st_sel)
        annotation_panel.pack(side="left", fill=tk.Y, padx=10, pady=10, expand=True)
        ttk.Label(annotation_panel, text='Annotations').pack()
        container1 = ttk.Frame(annotation_panel, borderwidth=1, relief='solid')
        container1.pack(fill=tk.BOTH, expand=True)
        container2 = ttk.Frame(container1)
        container2.pack(side='top', fill='both', expand=True)
        canvas = tk.Canvas(container2)
        canvas.pack(side="left", fill="y")
        vscrollbar = ttk.Scrollbar(container2, orient="vertical", command=canvas.yview)
        vscrollbar.pack(side="right", fill="y", expand=True)
        hscrollbar = ttk.Scrollbar(container1, orient="horizontal", command=canvas.xview)
        hscrollbar.pack(side="bottom", fill="x")
        
        self.st_panel_left = ttk.Frame(canvas)
        self.st_panel_left.pack(fill=tk.BOTH)
        
        self.st_panel_left.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.st_panel_left, anchor="nw")
        canvas.configure(xscrollcommand=hscrollbar.set)
        canvas.configure(yscrollcommand=vscrollbar.set)

        move_btn_panel = ttk.Frame(self.st_sel, width=40)
        move_btn_panel.pack(side="left", fill=tk.Y, pady=10, expand=True)
        move_btn_panel.pack_propagate(0)
        move_left_btn_panel = ttk.Frame(move_btn_panel)
        move_left_btn_panel.pack(expand=True, fill=tk.Y)
        move_right_btn_panel = ttk.Frame(move_btn_panel)
        move_right_btn_panel.pack(expand=True, fill=tk.Y)
        tk.Button(move_left_btn_panel, text='<<', command=self.moveAnnotsToLeftPanel).pack(side='bottom')
        tk.Button(move_right_btn_panel, text='>>', command=self.moveAnnotsToRightPanel).pack(side='top')

        config = self.controller.getConfig()

        self.annot_values, self.annot_checkbuttons_left = {}, {}
        for i in range(len(self.controller.annotations_all)):
            annot_name = self.controller.annotations_all[i]
            self.annot_values[annot_name] = tk.BooleanVar()
            if annot_name.lower() not in config.sleep_stage_event_to_id_mapping:
                self.annot_checkbuttons_left[annot_name] = tk.Checkbutton(self.st_panel_left, text=annot_name, variable=self.annot_values[annot_name], onvalue=True, offvalue=False, font=(self.font_name, self.font_size-5))
                self.annot_checkbuttons_left[annot_name].grid(row=i, column=0, padx=5, pady=5, sticky='nw')
        
        annotation_panel1 = ttk.Frame(self.st_sel)
        annotation_panel1.pack(side="left", fill=tk.Y, padx=10, pady=10, expand=True)
        self.st_options = ttk.Combobox(annotation_panel1, values=config.SLEEP_STAGE_ALL_NAMES, state='readonly', font=(self.font_name, self.font_size))
        self.st_options.bind('<<ComboboxSelected>>', self.loadAnnotsRightPanel)
        self.st_options.pack()
        self.st_options.current(0)
        container11 = ttk.Frame(annotation_panel1, borderwidth=1, relief='solid')
        container11.pack(fill=tk.BOTH, expand=True)
        container21 = ttk.Frame(container11)
        container21.pack(side='top', fill='both', expand=True)
        canvas1 = tk.Canvas(container21)
        canvas1.pack(side="left", fill="y")
        vscrollbar1 = ttk.Scrollbar(container21, orient="vertical", command=canvas1.yview)
        vscrollbar1.pack(side="right", fill="y", expand=True)
        hscrollbar1 = ttk.Scrollbar(container11, orient="horizontal", command=canvas1.xview)
        hscrollbar1.pack(side="bottom", fill="x")
        
        self.st_panel_right = ttk.Frame(canvas1)
        self.st_panel_right.pack(fill=tk.BOTH)
        
        self.st_panel_right.bind(
            "<Configure>",
            lambda e: canvas1.configure(
                scrollregion=canvas1.bbox("all")
            )
        )

        canvas1.create_window((0, 0), window=self.st_panel_right, anchor="nw")
        canvas1.configure(xscrollcommand=hscrollbar1.set)
        canvas1.configure(yscrollcommand=vscrollbar1.set)

        self.annot_checkbuttons_right = [{} for _ in config.SLEEP_STAGE_ALL_NAMES]

        for annot_name in self.controller.annotations_all:
            if annot_name.lower() in config.sleep_stage_event_to_id_mapping:
                for st_stage_ind in range(len(config.SLEEP_STAGE_ALL_NAMES)):
                    if config.sleep_stage_event_to_id_mapping[annot_name.lower()] == config.SLEEP_STAGES_ALL[st_stage_ind]:
                        if self.st_options.current() == st_stage_ind:
                            self.annot_checkbuttons_right[st_stage_ind][annot_name] = tk.Checkbutton(self.st_panel_right, text=annot_name, variable=self.annot_values[annot_name], onvalue=True, offvalue=False, font=(self.font_name, self.font_size-5))
                            self.annot_checkbuttons_right[st_stage_ind][annot_name].grid(row=i, column=0, padx=5, pady=5, sticky='nw')
                        else:
                            self.annot_checkbuttons_right[st_stage_ind][annot_name] = 'TBD'

    # --------------------------------------------------------------------------
    def setFilterSettingsPanel(self):

        config = self.controller.getConfig()

        vcmd = (self.master.register(self.callback))

        notch_panel = ttk.Frame(self.filter_sel, borderwidth=1, relief='solid')
        notch_panel.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(notch_panel, text="Notch filter frequency (Hz):", width=63, anchor='e', font=(self.font_name, self.font_size-5)).grid(row=0, column=0, padx=10, sticky='nse')
        self.notch_freq_entry = ttk.Entry(notch_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.notch_freq_entry.insert(tk.END, config.FILTERS['notch'])
        self.notch_freq_entry.grid(row=0, column=1, padx=10)

        bandpass_panel = tk.LabelFrame(self.filter_sel, text='Bandpass filter options', borderwidth=1, relief='solid')
        bandpass_panel.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(bandpass_panel, text="Minimum frequency (Hz):", width=63, anchor='e', font=(self.font_name, self.font_size-5)).grid(row=0, column=0, padx=10, sticky='nse')
        self.bandpass_min_freq_entry = ttk.Entry(bandpass_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.bandpass_min_freq_entry.insert(tk.END, config.FILTERS['bandpass'][0])
        self.bandpass_min_freq_entry.grid(row=0, column=1, padx=10)

        ttk.Label(bandpass_panel, text="Maximum frequency (Hz):", width=63, anchor='e', font=(self.font_name, self.font_size-5)).grid(row=1, column=0, padx=10, sticky='nse')
        self.bandpass_max_freq_entry = ttk.Entry(bandpass_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.bandpass_max_freq_entry.insert(tk.END, config.FILTERS['bandpass'][1])
        self.bandpass_max_freq_entry.grid(row=1, column=1, padx=10)

        amplitude_max_panel = ttk.Frame(self.filter_sel, borderwidth=1, relief='solid')
        amplitude_max_panel.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(amplitude_max_panel, text="Maximum amplitude (micro Volt):", width=63, anchor='e', font=(self.font_name, self.font_size-5)).grid(row=0, column=0, padx=10, sticky='nse')
        self.amplitude_max_entry = ttk.Entry(amplitude_max_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.amplitude_max_entry.insert(tk.END, config.FILTERS['amplitude_max'])
        self.amplitude_max_entry.grid(row=0, column=1, padx=10)

        flat_signal_filter_panel = tk.LabelFrame(self.filter_sel, text='Flat signal filter options', borderwidth=1, relief='solid')
        flat_signal_filter_panel.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(flat_signal_filter_panel, text="Duration (seconds):", width=63, anchor='e', font=(self.font_name, self.font_size-5)).grid(row=0, column=0, padx=10, sticky='nse')
        self.flat_signal_duration_entry = ttk.Entry(flat_signal_filter_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.flat_signal_duration_entry.insert(tk.END, config.FILTERS['flat_signal'][0])
        self.flat_signal_duration_entry.grid(row=0, column=1, padx=10)

        ttk.Label(flat_signal_filter_panel, text="Minimum frequency standard deviation in flat signal duration:", width=63, anchor='e', font=(self.font_name, self.font_size-5)).grid(row=1, column=0, padx=10, sticky='nse')
        self.freq_std_min_flat_entry = ttk.Entry(flat_signal_filter_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.freq_std_min_flat_entry.insert(tk.END, config.FILTERS['flat_signal'][1])
        self.freq_std_min_flat_entry.grid(row=1, column=1, padx=10)

        ttk.Label(flat_signal_filter_panel, text="Minimum frequency standard deviation in an epoch:", width=63, anchor='e', font=(self.font_name, self.font_size-5)).grid(row=2, column=0, padx=10, sticky='nse')
        self.freq_std_min_epoch_entry = ttk.Entry(flat_signal_filter_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.freq_std_min_epoch_entry.insert(tk.END, config.FILTERS['flat_signal'][2])
        self.freq_std_min_epoch_entry.grid(row=2, column=1, padx=10)

        bad_annots_panel = tk.LabelFrame(self.filter_sel, text='Annotations to remove from consideration')
        bad_annots_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        container1 = ttk.Frame(bad_annots_panel)
        container1.pack(fill=tk.BOTH, expand=True)
        container2 = ttk.Frame(container1)
        container2.pack(side="top", fill=tk.BOTH, expand=True)
        self.bad_annots_list = tk.Listbox(container2, selectmode="multiple", font=(self.font_name, self.font_size-5))
        self.bad_annots_list.pack(side="left", fill=tk.BOTH, expand=True, padx=0, pady=0)
        vscrollbar1 = ttk.Scrollbar(container2, orient="vertical", command=self.bad_annots_list.yview)
        vscrollbar1.pack(side="right", fill="y")
        hscrollbar1 = ttk.Scrollbar(container1, orient="horizontal", command=self.bad_annots_list.xview)
        hscrollbar1.pack(side="bottom", fill="x")
        
        self.bad_annots_list.configure(xscrollcommand=hscrollbar1.set)
        self.bad_annots_list.configure(yscrollcommand=vscrollbar1.set)
        
        if self.controller.annotations_all is not None:
            bad_annots = set(config.FILTERS['bad_annots'])
            for i, annot in enumerate(self.controller.annotations_all):
                self.bad_annots_list.insert(tk.END, annot)
                if annot in bad_annots: self.bad_annots_list.set(i)

    # --------------------------------------------------------------------------
    def setEpochSizePanel(self):

        vcmd = (self.master.register(self.callback))

        config = self.controller.getConfig()

        epoch_size_panel = ttk.Frame(self.epoch_sel, borderwidth=1, relief='solid')
        epoch_size_panel.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(epoch_size_panel, text="Epoch Size (Seconds):", width=40, anchor='e', font=(self.font_name, self.font_size-2)).grid(row=0, column=0, padx=10, sticky='nse')
        self.epoch_size_entry = ttk.Entry(epoch_size_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.epoch_size_entry.insert(tk.END, config.EPOCH_SIZE)
        self.epoch_size_entry.grid(row=0, column=1, padx=10)

    # --------------------------------------------------------------------------
    def callback(self, value):
        regex = re.compile(r"[0-9]*(\.)?[0-9]*$")
        result = regex.match(value)
        return (value == ""
                    or (result is not None
                        and result.group(0) != ""))

     # --------------------------------------------------------------------------
    def loadAnnotsRightPanel(self, event=None):
        
        st_stage_ind = self.st_options.current()
        for child in self.st_panel_right.winfo_children():
            child.destroy()

        for i, annot_name in enumerate(sorted(list(self.annot_values.keys()))):
            if annot_name in self.annot_checkbuttons_right[st_stage_ind] and self.annot_checkbuttons_right[st_stage_ind][annot_name] is not None:
                self.annot_checkbuttons_right[st_stage_ind][annot_name] = tk.Checkbutton(self.st_panel_right, text=annot_name, variable=self.annot_values[annot_name], onvalue=True, offvalue=False, font=(self.font_name, self.font_size-5))
                self.annot_checkbuttons_right[st_stage_ind][annot_name].grid(row=i, column=0, padx=5, pady=5, sticky='nw')
                self.annot_values[annot_name].set(False)

    # --------------------------------------------------------------------------
    def moveAnnotsToLeftPanel(self):

        st_stage_ind = self.st_options.current()

        for annot_name in self.annot_values.keys():
            if self.annot_values[annot_name].get() == True:
                if annot_name in self.annot_checkbuttons_right[st_stage_ind] and self.annot_checkbuttons_right[st_stage_ind][annot_name] is not None:
                    self.annot_checkbuttons_right[st_stage_ind][annot_name].destroy()
                    self.annot_checkbuttons_right[st_stage_ind][annot_name] = None
                    self.annot_checkbuttons_left[annot_name] = tk.Checkbutton(self.st_panel_left, text=annot_name, variable=self.annot_values[annot_name], onvalue=True, offvalue=False, font=(self.font_name, self.font_size-5))
                    
        for i, annot_name in enumerate(sorted(list(self.annot_values.keys()))):
            if annot_name in self.annot_checkbuttons_left and self.annot_checkbuttons_left[annot_name] is not None:
                self.annot_checkbuttons_left[annot_name].grid(row=i, column=0, padx=5, pady=5, sticky='nw')
                self.annot_values[annot_name].set(False)

    # --------------------------------------------------------------------------
    def moveAnnotsToRightPanel(self):

        st_stage_ind = self.st_options.current()

        for annot_name in self.annot_values.keys():
            if self.annot_values[annot_name].get() == True:
                if annot_name in self.annot_checkbuttons_left and self.annot_checkbuttons_left[annot_name] is not None:
                    self.annot_checkbuttons_left[annot_name].destroy()
                    self.annot_checkbuttons_left[annot_name] = None
                    self.annot_checkbuttons_right[st_stage_ind][annot_name] = 'TBD'
                    
        self.loadAnnotsRightPanel()

    # --------------------------------------------------------------------------
    def selectAllChannels(self, select):
        for ch_name, var in self.channel_values.items():
            var.set(value=select)

        if select == True:
            self.select_all_channels_btn.configure(text='Select None')
            self.select_all_channels_btn.configure(command=lambda : self.selectAllChannels(False))
        else:
            self.select_all_channels_btn.configure(text='Select All')
            self.select_all_channels_btn.configure(command=lambda : self.selectAllChannels(True))

    # --------------------------------------------------------------------------
    def saveSettings(self):

        success, msg = self.controller.saveSettings(self)

        if not success:
            messagebox.showerror(title="Error!!!", message=msg)
            return

        self.master.destroy()
        print(msg)
    
# --------------------------------------------------------------------------
class MainDialog(Dialog):

    controller = None

    # --------------------------------------------------------------------------
    def __init__(self, controller) -> None:

        master = Tk()
        master.title('SCVIS - Sleep Cycle Visualization Tool')
        master.geometry("900x1000+450+50")

        super().__init__(master, 900, 1000)

        self.controller = controller

        self.setInputPanel()
        self.setOutputPanel()
        
        #sys.stdout = TextRedirector(self)
        #sys.stderr = TextRedirector(self)
        
        master.mainloop()

    # --------------------------------------------------------------------------
    def setInputPanel(self):

        # Set input panel
        input_panel = ttk.Frame(self.master, width=self.width-20, height=int(self.height*0.3), borderwidth=1, relief='groove')
        input_panel.pack(padx=10)
        input_panel.pack_propagate(0)

        sample_path_panel = ttk.Frame(input_panel)
        sample_path_panel.pack(fill=tk.X)

        group_panel2 = ttk.Frame(sample_path_panel, width=200, borderwidth=1, relief='groove')
        group_panel2.pack(side=tk.RIGHT, fill=tk.Y)
        group_panel2.pack_propagate(0)
        
        ttk.Button(group_panel2, text='Load', command=self.loadData).pack(expand=True)

        group_panel1 = ttk.Frame(sample_path_panel, borderwidth=1, relief='groove')
        group_panel1.pack(side=tk.TOP, fill=tk.BOTH)

        ttk.Label(group_panel1, text="Sample Path:", width=12, anchor='e').grid(row=0, column=0, padx=10, sticky='nse', pady=5)

        self.sample_path_entry = ttk.Entry(group_panel1, width=35, textvariable='file_path_sample', font=(self.font_name, self.font_size))
        self.sample_path_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Button(group_panel1, text='Browse', command=self.browseInputFile).grid(row=0, column=2, padx=10)

        group_panel = ttk.Frame(input_panel)
        group_panel.pack(fill=tk.X)

        settings_type_panel = ttk.Frame(group_panel, width=200, borderwidth=1, relief='groove')
        settings_type_panel.pack(side=tk.RIGHT, fill=tk.Y)
        settings_type_panel.pack_propagate(0)

        self.config_btn = ttk.Button(settings_type_panel, text='Configure', state=tk.DISABLED, command=self.openSettingsDialog)
        self.config_btn.pack(expand=1, pady=5)

        self.apply_filter = tk.BooleanVar()
        self.apply_filter_btn = ttk.Checkbutton(settings_type_panel, text='Apply Filters', variable=self.apply_filter, state=tk.DISABLED)
        self.apply_filter_btn.pack(expand=1)
        self.apply_filter.set(value=False)

        self.execute_btn = ttk.Button(settings_type_panel, text='Execute', state=tk.DISABLED, command=self.execute)
        self.execute_btn.pack(expand=True, pady=5)

        sample_type_panel = ttk.Frame(group_panel, borderwidth=1, relief='groove')
        sample_type_panel.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(sample_type_panel, text="Sample Type:", width=12, anchor='e').grid(row=0, column=0, rowspan=2, padx=10, sticky='nse', pady=5)

        sample_type_option_panel = ttk.Frame(sample_type_panel, borderwidth=1, relief='groove')
        sample_type_option_panel.grid(row=0, column=1, padx=10, sticky='nsw')

        self.file_type_entry = tk.StringVar()
        ttk.Radiobutton(sample_type_option_panel, text='EDF File', variable=self.file_type_entry, value='edf').grid(row=0, column=0, padx=10, sticky='nsw', pady=5)
        ttk.Radiobutton(sample_type_option_panel, text='Annotation Epochs', variable=self.file_type_entry, value='annot').grid(row=1, column=0, padx=10, sticky='nsw', pady=5)
        self.file_type_entry.set(value='edf')

        sample_type_panel.rowconfigure(0, weight=1)

        output_path_panel = ttk.Frame(group_panel, borderwidth=1, relief='groove')
        output_path_panel.pack(fill='x')

        ttk.Label(output_path_panel, text="Output Path:", width=12, anchor='e').grid(row=0, column=0, padx=10, sticky='nse', pady=5)

        self.output_path_entry = ttk.Entry(output_path_panel, width=35, textvariable='folder_path_output', font=(self.font_name, self.font_size))
        self.output_path_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Button(output_path_panel, text='Browse', command=self.browseOutputFolder).grid(row=0, column=2, padx=10)

        self.status_textarea = scrolledtext.ScrolledText(input_panel, borderwidth=1, state=tk.DISABLED, relief='groove')
        self.status_textarea.pack(fill='both')

    # --------------------------------------------------------------------------
    def setOutputPanel(self):
    
        output_panel = ttk.Frame(self.master, width=self.width-20, height=int(self.height*0.7), borderwidth=1, relief='groove')
        output_panel.pack(padx=10)
        output_panel.pack_propagate(0)

        tab_control = ttk.Notebook(output_panel)
        tab_control.pack(expand=True, fill='both')

        style = ttk.Style()
        style.configure("mystyle.Treeview", highlightthickness=0, bd=0) # Modify the font of the body
        style.configure("mystyle.Treeview.Heading", font=(self.font_name, self.font_size,'bold')) # Modify the font of the headings
        style.layout("mystyle.Treeview", [('mystyle.Treeview.treearea', {'sticky': 'nswe'})]) # Remove the borders

        self.output_plot = tk.Canvas(tab_control, borderwidth=1, relief='solid')
        self.output_sc_st = ttk.Treeview(tab_control, selectmode='browse', style="mystyle.Treeview")
        #self.output_sc_st.pack(side='left')
        self.output_ct = ttk.Treeview(tab_control, style="mystyle.Treeview")
        #self.output_ct.pack(side='left')

        # Constructing vertical scrollbar
        # with treeview
        verscrlbar = ttk.Scrollbar(self.output_sc_st,
                                orient ="vertical",
                                command = self.output_sc_st.yview)
        
        # Calling pack method w.r.to vertical
        # scrollbar
        verscrlbar.pack(side ='right', fill ='y')
        # Configuring treeview
        self.output_sc_st.configure(yscrollcommand = verscrlbar.set)
        self.output_sc_st.tag_configure('odd', background='#E8E8E8')
        self.output_sc_st.tag_configure('even', background='#DFDFDF')

        tab_control.add(self.output_plot, text='Visualization')
        tab_control.add(self.output_sc_st, text='Sleep Cycles and Stages')
        tab_control.add(self.output_ct, text='NREM Cut Options')

        #self.output_ct.pack_forget()

    # --------------------------------------------------------------------------
    def browseInputFile(self):

        if self.file_type_entry.get() == 'annot':
            file_types = (("Text files", "*.txt"), ("all files", "*.*"))
        else:
            file_types = (("EDF files", "*.edf"), ("all files", "*.*"))

        file_name = filedialog.askopenfilename(initialdir = "/",
                                          title = "Select an input file",
                                          filetypes = file_types)

        self.sample_path_entry.delete(0, tk.END)
        self.sample_path_entry.insert(0, file_name)

    # --------------------------------------------------------------------------
    def browseOutputFolder(self):

        folder_name = filedialog.askdirectory(initialdir = "/",
                                          title = "Select a output directory")

        self.output_path_entry.delete(0, tk.END)
        self.output_path_entry.insert(0, folder_name)

    # --------------------------------------------------------------------------
    def openSettingsDialog(self):
        
        self.settings_obj = SettingsDialog(self.master, self.controller)

    # --------------------------------------------------------------------------
    def loadData(self):

        if self.controller.loadSleepData(self):
            self.config_btn.config(state=tk.NORMAL)
            self.apply_filter_btn.config(state=tk.NORMAL)
            self.execute_btn.config(state=tk.NORMAL)

    # --------------------------------------------------------------------------
    def clearTree(self, tree):
        for item in tree.get_children():
            tree.delete(item)

    # --------------------------------------------------------------------------
    def execute(self):

        print('Showing outputs')

        self.output_plot.delete('all')
        x, y = self.output_plot.winfo_width()//2, self.output_plot.winfo_height()//2
        self.output_plot.create_text(x, y, text="Generating Visualization...", fill="black", font=('Courier 40 bold'))
        self.master.update()
        self.controller.execute(self)

        img_path = os.path.join(self.controller.scv_obj.folder_cache, f'{self.controller.scv_obj.sample_name}.jpg')
        if os.path.exists(img_path): 
            img = Image.open(img_path)
            w, h = self.output_plot.winfo_width(), self.output_plot.winfo_height()
            img.thumbnail((w, h), Image.ANTIALIAS)
            bg = ImageTk.PhotoImage(img)
            self.output_plot.create_image(int(w//2), int(h//2), image = bg, anchor = tk.CENTER)
            self.output_plot.image = bg
        else:
            self.output_plot.delete('all')
            x, y = self.output_plot.winfo_width()//2, self.output_plot.winfo_height()//2
            self.output_plot.create_text(x, y, text="Failed to generate visualization", fill="black", font=('Helvetica 40 bold'))

        self.clearTree(self.output_sc_st)

        self.output_sc_st['columns']= ('EPOCH', 'SLEEP CYCLE INDEX','SLEEP CYCLE', 'SLEEP STAGE')
        self.output_sc_st.column("#0", width=0,  stretch=tk.NO)
        self.output_sc_st.column("EPOCH", anchor=tk.CENTER, width=80)
        self.output_sc_st.column("SLEEP CYCLE INDEX", anchor=tk.CENTER, width=80)
        self.output_sc_st.column("SLEEP CYCLE", anchor=tk.CENTER, width=80)
        self.output_sc_st.column("SLEEP STAGE", anchor=tk.CENTER, width=80)

        self.output_sc_st.heading("#0", text="", anchor=tk.CENTER)
        self.output_sc_st.heading("EPOCH", text="EPOCH",anchor=tk.CENTER)
        self.output_sc_st.heading("SLEEP CYCLE INDEX", text="SLEEP CYCLE INDEX", anchor=tk.CENTER)
        self.output_sc_st.heading("SLEEP CYCLE", text="SLEEP CYCLE", anchor=tk.CENTER)
        self.output_sc_st.heading("SLEEP STAGE", text="SLEEP STAGE", anchor=tk.CENTER)

        sc_path = os.path.join(self.controller.scv_obj.folder_cache, f'{self.controller.scv_obj.sample_name}_sc.txt')
        st_path = os.path.join(self.controller.scv_obj.folder_cache, f'{self.controller.scv_obj.sample_name}_st.txt')
        if os.path.exists(sc_path) and os.path.exists(st_path):
            data_sc, data_st = readFileInTable(sc_path), readFileInTable(st_path)
            data_combined = []
            for i, v in enumerate(zip(data_sc, data_st)):
                row = v[0] + v[1]
                if i==0 or (row != last_unique_row):
                    if i > 0:
                        if last_unique_row_i+1 == i: data_combined.append([i] + last_unique_row)
                        else: data_combined.append([f'{last_unique_row_i+1}-{i}'] + last_unique_row)
                    last_unique_row = row
                    last_unique_row_i = i

                if i == len(data_sc)-1:
                    if last_unique_row_i == i: data_combined.append([i+1] + last_unique_row)
                    else: data_combined.append([f'{last_unique_row_i+1}-{i+1}'] + last_unique_row)

            for i, v in enumerate(data_combined):
                self.output_sc_st.insert(parent='', index='end', iid=i, text='', values=tuple(v), tags=('odd' if i % 2 else "even"))

        #self.output_ct.pack(side='left')

# --------------------------------------------------------------------------
class CLIInterface():

    # --------------------------------------------------------------------------
    def __init__(self, controller):
        self.controller = controller

        self.controller.loadSleepData()
        self.controller.execute()
        
# --------------------------------------------------------------------------
if __name__ == "__main__":

    try:
        app = MainDialog(DesktopUIController())
    except tk.TclError as error:
        if 'no display' in error.args[0]: app = CLIInterface(CLIController())