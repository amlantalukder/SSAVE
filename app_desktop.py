import os, sys, re
import tkinter as tk
from tkinter import Tk, ttk, font, filedialog, scrolledtext, messagebox
from matplotlib import widgets
import numpy as np
import pdb

from utils import readFileInTable
from PIL import ImageTk, Image
from controller import DesktopUIController, CLIController
from functools import partial

class CbTreeview(ttk.Treeview):
    def __init__(self, master, font_name, font_size, **kw):
        kw.setdefault('style', 'cb.Treeview')
        kw.setdefault('show', 'headings')  # hide column #0
        ttk.Treeview.__init__(self, master, **kw)
        pwd = os.path.dirname(__file__)

        self._im_checked = ImageTk.PhotoImage(Image.open(os.path.join(pwd, 'checked.png')))
        self._im_unchecked = ImageTk.PhotoImage(Image.open(os.path.join(pwd, 'unchecked.png'))) 
        # create checheckbox images
        #self._im_checked = tk.PhotoImage('checked',
        #                                 data=b'GIF89a\x0e\x00\x0e\x00\xf0\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x0e\x00\x0e\x00\x00\x02#\x04\x82\xa9v\xc8\xef\xdc\x83k\x9ap\xe5\xc4\x99S\x96l^\x83qZ\xd7\x8d$\xa8\xae\x99\x15Zl#\xd3\xa9"\x15\x00;',
        #                                 master=self)
        #self._im_unchecked = tk.PhotoImage('unchecked',
        #                                   data=b'GIF89a\x0e\x00\x0e\x00\xf0\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x0e\x00\x0e\x00\x00\x02\x1e\x04\x82\xa9v\xc1\xdf"|i\xc2j\x19\xce\x06q\xed|\xd2\xe7\x89%yZ^J\x85\x8d\xb2\x00\x05\x00;',
        #                                   master=self)

        self.font_name = font_name
        self.font_size = font_size

        style = ttk.Style(self)
        #style.configure('Treeview', rowheight=30)
        style.configure("cb.Treeview", highlightthickness=0, bd=0, rowheight=30)
        style.configure("cb.Treeview.Heading", font=(self.font_name, self.font_size, 'bold'))
        style.layout('cb.Treeview.Row', [('Treeitem.row', {'sticky': 'nswe'}),
                                        ('Treeitem.image', {'side': 'right', 'sticky': 'e'})])
        # put image on the right
        '''
        style.layout('cb.Treeview.Row',
                     [('Treeitem.row', {'sticky': 'nswe'}),
                      ('Treeitem.image', {'sticky': 'nswe'})])
        '''
        # use tags to set the checkbox state
        self.tag_configure('checked', image=self._im_checked) #image='checked')
        self.tag_configure('unchecked', image=self._im_unchecked) #image='unchecked')

    def tag_add(self, item, tags):
        new_tags = tuple(self.item(item, 'tags')) + tuple(tags)
        self.item(item, tags=new_tags)

    def tag_remove(self, item, tag):
        tags = list(self.item(item, 'tags'))
        tags.remove(tag)
        self.item(item, tags=tags)

    def insert(self, parent, index, iid=None, checked=False, **kw):
        item = ttk.Treeview.insert(self, parent, index, iid, **kw)
        self.tag_add(item, (item, 'unchecked' if not checked else 'checked'))
        self.tag_bind(item, '<ButtonRelease-1>',
                      lambda event: self._on_click(event, item))

    def _on_click(self, event, item):
        """Handle click on items."""
        if self.identify_row(event.y) == item:
            if self.identify_column(event.x) == '#4': # click in 'Served' column
                # toggle checkbox image
                if self.tag_has('checked', item):
                    self.tag_remove(item, 'checked')
                    self.tag_add(item, ('unchecked',))
                else:
                    self.tag_remove(item, 'unchecked')
                    self.tag_add(item, ('checked',))

    def get(self):
        values = []
        for item in self.get_children():
            if self.tag_has('checked', item):
                values.append(int(self.item(item, 'values')[2]))
        return values

def motion_handler(tree, event):
    f = font.Font(font='TkDefaultFont')
    # A helper function that will wrap a given value based on column width
    def adjust_newlines(val, width, pad=10):
        if not isinstance(val, str):
            return val
        else:
            words = val.split()
            lines = [[],]
            for word in words:
                line = lines[-1] + [word,]
                if f.measure(' '.join(line)) < (width - pad):
                    lines[-1].append(word)
                else:
                    lines[-1] = ' '.join(lines[-1])
                    lines.append([word,])

            if isinstance(lines[-1], list):
                lines[-1] = ' '.join(lines[-1])

            return '\n'.join(lines)

    if (event is None) or (tree.identify_region(event.x, event.y) == "separator"):
        # You may be able to use this to only adjust the two columns that you care about
        # print(tree.identify_column(event.x))

        col_widths = [tree.column(cid)['width'] for cid in tree['columns']]

        for iid in tree.get_children():
            new_vals = []
            for (v,w) in zip(tree.item(iid)['values'], col_widths):
                new_vals.append(adjust_newlines(v, w))
            tree.item(iid, values=new_vals)

'''
root = tk.Tk()
tree = CbTreeview(root, columns=("Table No.", "Order", "Time", "Served"),
                  height=400, selectmode="extended")

tree.heading('Table No.', text="Table No.", anchor='w')
tree.heading('Order', text="Order", anchor='w')
tree.heading('Time', text="Time", anchor='w')
tree.heading('Served', text="Served", anchor='w')
tree.column('#1', stretch='no', minwidth=0, width=100)
tree.column('#2', stretch='no', minwidth=0, width=600)
tree.column('#3', stretch='no', minwidth=0, width=100)
tree.column('#4', stretch='no', minwidth=0, width=70)

tree.pack(fill='both')

for i in range(5):
    tree.insert('', 'end', values=(i, i, i))
root.mainloop()
'''

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
    def clearTree(self, tree):
        for item in tree.get_children():
            tree.delete(item)

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

        ch_panel = tk.Frame(self.ch_sel, borderwidth=1, relief='solid')
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

        tk.Label(self.st_sel, text='These are the events found in your EDF file. Please select those that are sleep stages.', font=(self.font_name, self.font_size, 'bold')).pack(pady=(10, 0))

        annotation_panel_left = tk.Frame(self.st_sel, width=300, borderwidth=1, relief='solid')
        annotation_panel_left.pack(side="left", fill=tk.Y, padx=10, pady=10)
        annotation_panel_left.pack_propagate(0)

        tk.Label(annotation_panel_left, text='All Annotations', bg="#717a82", fg='white').pack(fill=tk.X)

        container1 = tk.Frame(annotation_panel_left)
        container1.pack(fill=tk.BOTH, expand=True)
        container2 = tk.Frame(container1)
        container2.pack(side='top', fill='both', expand=True)
        canvas = tk.Canvas(container2, width=270)
        canvas.pack(side="left", fill=tk.Y)
        canvas.pack_propagate(0)
        vscrollbar = ttk.Scrollbar(container2, orient="vertical", command=canvas.yview)
        vscrollbar.pack(side="right", fill=tk.Y)
        hscrollbar = ttk.Scrollbar(container1, orient="horizontal", command=canvas.xview)
        hscrollbar.pack(side="bottom", fill="x")
        
        self.st_panel_left = tk.Frame(canvas)
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

        move_btn_panel = tk.Frame(self.st_sel, width=40)
        move_btn_panel.pack(side="left", fill=tk.Y, padx=10, pady=10)
        move_btn_panel.pack_propagate(0)
        
        move_btn_group_panel = tk.Frame(move_btn_panel, height=160)
        move_btn_group_panel.pack(fill=tk.X)
        move_btn_group_panel.pack_propagate(0)

        move_left_btn_panel = tk.Frame(move_btn_group_panel, bg="#ececec")
        move_left_btn_panel.pack(expand=True, fill=tk.Y)
        move_right_btn_panel = tk.Frame(move_btn_panel)
        move_right_btn_panel.pack(expand=True, fill=tk.Y)
        tk.Button(move_left_btn_panel, text='<<', command=self.moveAnnotsToLeftPanel).pack(side='bottom')
        tk.Button(move_right_btn_panel, text='>>', command=self.moveAnnotsToRightPanel).pack(side='top')

        move_no_button_panel = tk.Frame(move_btn_panel)
        move_no_button_panel.pack(fill=tk.Y, expand=True)

        config = self.controller.getConfig()
        
        annotation_panel_right = tk.Frame(self.st_sel, borderwidth=1, relief='solid')
        annotation_panel_right.pack(side="left", fill=tk.BOTH, padx=10, pady=10, expand=True)
        
        tk.Label(annotation_panel_right, text='Assigned Annotations', bg="#717a82", fg='white').pack(fill=tk.X)
        
        annotation_st_panel = tk.Frame(annotation_panel_right)
        annotation_st_panel.pack(fill=tk.BOTH)

        self.st_options = ttk.Combobox(annotation_st_panel, values=config.SLEEP_STAGE_ALL_NAMES, state='readonly', font=(self.font_name, self.font_size))
        self.st_options.bind('<<ComboboxSelected>>', self.loadAnnotsRightPanel)
        self.st_options.pack(fill=tk.X, padx=10)
        self.st_options.current(0)
        container11 = tk.Frame(annotation_st_panel, borderwidth=1, relief='solid')
        container11.pack(fill=tk.BOTH, padx=10, pady=(0, 10))
        container21 = tk.Frame(container11)
        container21.pack(side='top', fill='both', expand=True)
        canvas1 = tk.Canvas(container21)
        canvas1.pack(side="left", fill="both")
        vscrollbar1 = ttk.Scrollbar(container21, orient="vertical", command=canvas1.yview)
        vscrollbar1.pack(side="right", fill="y")
        hscrollbar1 = ttk.Scrollbar(container11, orient="horizontal", command=canvas1.xview)
        hscrollbar1.pack(side="bottom", fill="x")
        
        self.st_panel_right = tk.Frame(canvas1)
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

        annotation_st_sel = tk.Frame(annotation_panel_right, borderwidth=1, relief='solid')
        annotation_st_sel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(annotation_st_sel, text="The following events are assigned to the sleep stages", font=(self.font_name, self.font_size, 'bold')).pack(padx=10, pady=10)

        style = ttk.Style()
        style.configure("mystyle.Treeview", highlightthickness=0, bd=0) # Modify the font of the body
        style.configure("mystyle.Treeview.Heading", font=(self.font_name, self.font_size, 'bold')) # Modify the font of the headings
        style.layout("mystyle.Treeview", [('mystyle.Treeview.treearea', {'sticky': 'nswe'})]) # Remove the borders

        self.st_annotations = ttk.Treeview(annotation_st_sel, style="mystyle.Treeview")
        self.st_annotations.pack(fill=tk.BOTH, expand=1)

        self.st_annotations['columns']= ('SLEEP STAGES', 'SELECTED SLEEP STAGES')
        self.st_annotations.column("#0", width=0,  stretch=tk.NO)
        self.st_annotations.column("SLEEP STAGES", anchor=tk.CENTER, width=20)
        self.st_annotations.column("SELECTED SLEEP STAGES", anchor=tk.CENTER, width=80)

        self.st_annotations.heading("#0", text="", anchor=tk.CENTER)
        self.st_annotations.heading("SLEEP STAGES", text="SLEEP STAGES",anchor=tk.CENTER)
        self.st_annotations.heading("SELECTED SLEEP STAGES", text="SELECTED SLEEP STAGES", anchor=tk.CENTER)

        self.st_annotations.tag_configure('odd', background='#E8E8E8')
        self.st_annotations.tag_configure('even', background='#DFDFDF')

        self.st_annotations.bind('<B1-Motion>', partial(motion_handler, self.st_annotations))
        motion_handler(self.st_annotations, None)

        self.annot_values, self.annot_checkbuttons_left, self.annot_checkbuttons_right = {}, {}, {}
        for i in range(len(self.controller.annotations_all)):
            annot_name = self.controller.annotations_all[i]
            self.annot_values[annot_name] = tk.BooleanVar()
            if annot_name.lower() not in config.sleep_stage_event_to_id_mapping:
                self.annot_checkbuttons_left[annot_name] = 'TBD'
            else:
                for st_stage_ind in range(len(config.SLEEP_STAGE_ALL_NAMES)):
                    if config.sleep_stage_event_to_id_mapping[annot_name.lower()] == config.SLEEP_STAGES_ALL[st_stage_ind]:
                        if st_stage_ind not in self.annot_checkbuttons_right:
                            self.annot_checkbuttons_right[st_stage_ind] = {}
                        self.annot_checkbuttons_right[st_stage_ind][annot_name] = 'TBD'

        self.loadAnnotsLeftPanel()
        self.loadAnnotsRightPanel()
        self.loadSTAnnotationTable()

    # --------------------------------------------------------------------------
    def setFilterSettingsPanel(self):

        config = self.controller.getConfig()

        vcmd = (self.master.register(self.callback))

        notch_panel = tk.Frame(self.filter_sel, borderwidth=1, relief='solid')
        notch_panel.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(notch_panel, text="Notch filter frequency (Hz):", width=63, anchor='e', font=(self.font_name, self.font_size-2)).grid(row=0, column=0, padx=10, sticky='nse')
        self.notch_freq_entry = ttk.Entry(notch_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.notch_freq_entry.insert(tk.END, config.FILTERS['notch'])
        self.notch_freq_entry.grid(row=0, column=1, padx=10)

        bandpass_panel = tk.LabelFrame(self.filter_sel, text='Bandpass filter options', borderwidth=1, relief='solid')
        bandpass_panel.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(bandpass_panel, text="Minimum frequency (Hz):", width=63, anchor='e', font=(self.font_name, self.font_size-2)).grid(row=0, column=0, padx=10, sticky='nse')
        self.bandpass_min_freq_entry = ttk.Entry(bandpass_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.bandpass_min_freq_entry.insert(tk.END, config.FILTERS['bandpass'][0])
        self.bandpass_min_freq_entry.grid(row=0, column=1, padx=10)

        tk.Label(bandpass_panel, text="Maximum frequency (Hz):", width=63, anchor='e', font=(self.font_name, self.font_size-2)).grid(row=1, column=0, padx=10, sticky='nse')
        self.bandpass_max_freq_entry = ttk.Entry(bandpass_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.bandpass_max_freq_entry.insert(tk.END, config.FILTERS['bandpass'][1])
        self.bandpass_max_freq_entry.grid(row=1, column=1, padx=10)

        amplitude_max_panel = tk.Frame(self.filter_sel, borderwidth=1, relief='solid')
        amplitude_max_panel.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(amplitude_max_panel, text="Maximum amplitude (micro Volt):", width=63, anchor='e', font=(self.font_name, self.font_size-2)).grid(row=0, column=0, padx=10, sticky='nse')
        self.amplitude_max_entry = ttk.Entry(amplitude_max_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.amplitude_max_entry.insert(tk.END, config.FILTERS['amplitude_max'])
        self.amplitude_max_entry.grid(row=0, column=1, padx=10)

        flat_signal_filter_panel = tk.LabelFrame(self.filter_sel, text='Flat signal filter options', borderwidth=1, relief='solid')
        flat_signal_filter_panel.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(flat_signal_filter_panel, text="Duration (seconds):", width=63, anchor='e', font=(self.font_name, self.font_size-2)).grid(row=0, column=0, padx=10, sticky='nse')
        self.flat_signal_duration_entry = ttk.Entry(flat_signal_filter_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.flat_signal_duration_entry.insert(tk.END, config.FILTERS['flat_signal'][0])
        self.flat_signal_duration_entry.grid(row=0, column=1, padx=10)

        tk.Label(flat_signal_filter_panel, text="Minimum frequency standard deviation in flat signal duration:", width=63, anchor='e', font=(self.font_name, self.font_size-2)).grid(row=1, column=0, padx=10, sticky='nse')
        self.freq_std_min_flat_entry = ttk.Entry(flat_signal_filter_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.freq_std_min_flat_entry.insert(tk.END, config.FILTERS['flat_signal'][1])
        self.freq_std_min_flat_entry.grid(row=1, column=1, padx=10)

        tk.Label(flat_signal_filter_panel, text="Minimum frequency standard deviation in an epoch:", width=63, anchor='e', font=(self.font_name, self.font_size-2)).grid(row=2, column=0, padx=10, sticky='nse')
        self.freq_std_min_epoch_entry = ttk.Entry(flat_signal_filter_panel, font=(self.font_name, self.font_size), width=8, validate='all', validatecommand=(vcmd, '%P'))
        self.freq_std_min_epoch_entry.insert(tk.END, config.FILTERS['flat_signal'][2])
        self.freq_std_min_epoch_entry.grid(row=2, column=1, padx=10)

        bad_annots_panel = tk.LabelFrame(self.filter_sel, text='Annotations to remove from consideration')
        bad_annots_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        container1 = tk.Frame(bad_annots_panel)
        container1.pack(fill=tk.BOTH, expand=True)
        container2 = tk.Frame(container1)
        container2.pack(side="top", fill=tk.BOTH, expand=True)
        self.bad_annots_list = tk.Listbox(container2, selectmode="multiple", font=(self.font_name, self.font_size-2))
        self.bad_annots_list.pack(side="left", fill=tk.BOTH, expand=True)
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

        epoch_size_panel = tk.Frame(self.epoch_sel, borderwidth=1, relief='solid')
        epoch_size_panel.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(epoch_size_panel, text="Epoch Size (Seconds):", width=63, anchor='e', font=(self.font_name, self.font_size-2)).grid(row=0, column=0, padx=10, sticky='nse')
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
    def loadSTAnnotationTable(self):

        self.clearTree(self.st_annotations)
        config = self.controller.getConfig()
        for st_stage_ind, st_name in enumerate(config.SLEEP_STAGE_ALL_NAMES):
            annots = ', '.join(sorted(self.annot_checkbuttons_right[st_stage_ind].keys()))
            self.st_annotations.insert(parent='', index='end', iid=st_stage_ind, text='', values=(st_name, annots), tags=('odd' if st_stage_ind % 2 else "even"))

    # --------------------------------------------------------------------------
    def loadAnnotsLeftPanel(self):

        for i, annot_name in enumerate(sorted(list(self.annot_values.keys()))):
            if annot_name in self.annot_checkbuttons_left and self.annot_checkbuttons_left[annot_name] is not None:
                self.annot_checkbuttons_left[annot_name] = tk.Checkbutton(self.st_panel_left, text=annot_name, variable=self.annot_values[annot_name], onvalue=True, offvalue=False, font=(self.font_name, self.font_size-2))
                self.annot_checkbuttons_left[annot_name].grid(row=i, column=0, padx=5, pady=5, sticky='nw')
                self.annot_values[annot_name].set(False)

    # --------------------------------------------------------------------------
    def loadAnnotsRightPanel(self, event=None):
        
        st_stage_ind = self.st_options.current()
        for child in self.st_panel_right.winfo_children():
            child.destroy()

        for i, annot_name in enumerate(sorted(list(self.annot_values.keys()))):
            if annot_name in self.annot_checkbuttons_right[st_stage_ind] and self.annot_checkbuttons_right[st_stage_ind][annot_name] is not None:
                self.annot_checkbuttons_right[st_stage_ind][annot_name] = tk.Checkbutton(self.st_panel_right, text=annot_name, variable=self.annot_values[annot_name], onvalue=True, offvalue=False, font=(self.font_name, self.font_size-2))
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
                    self.annot_checkbuttons_left[annot_name] = 'TBD'

        self.loadAnnotsLeftPanel()
        self.loadSTAnnotationTable()

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
        self.loadSTAnnotationTable()

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
    img_path = None

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
        master.configure(bg='white') 
        master.mainloop()

    # --------------------------------------------------------------------------
    def setInputPanel(self):

        # Set input panel
        input_panel = tk.Frame(self.master, width=self.width-20, height=int(self.height*0.3), borderwidth=1, relief='groove')
        input_panel.pack(padx=10)
        input_panel.pack_propagate(0)

        sample_path_panel = tk.Frame(input_panel)
        sample_path_panel.pack(fill=tk.X)

        group_panel2 = tk.Frame(sample_path_panel, width=200, borderwidth=1, relief='groove')
        group_panel2.pack(side=tk.RIGHT, fill=tk.Y)
        group_panel2.pack_propagate(0)
        
        ttk.Button(group_panel2, text='Load', command=self.loadData).pack(expand=True)

        group_panel1 = tk.Frame(sample_path_panel, borderwidth=1, relief='groove')
        group_panel1.pack(side=tk.TOP, fill=tk.BOTH)

        tk.Label(group_panel1, text="Sample Path:", width=12, anchor='e').grid(row=0, column=0, padx=10, sticky='nse', pady=5)

        self.sample_path_entry = ttk.Entry(group_panel1, width=35, textvariable='file_path_sample', font=(self.font_name, self.font_size))
        self.sample_path_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Button(group_panel1, text='Browse', command=self.browseInputFile).grid(row=0, column=2, padx=10)

        group_panel = tk.Frame(input_panel)
        group_panel.pack(fill=tk.X)

        settings_type_panel = tk.Frame(group_panel, width=200, borderwidth=1, relief='groove')
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

        sample_type_panel = tk.Frame(group_panel, borderwidth=1, relief='groove')
        sample_type_panel.pack(side=tk.TOP, fill=tk.X)

        tk.Label(sample_type_panel, text="Sample Type:", width=12, anchor='e').grid(row=0, column=0, rowspan=2, padx=10, sticky='nse', pady=5)

        sample_type_option_panel = tk.Frame(sample_type_panel, borderwidth=1, relief='groove')
        sample_type_option_panel.grid(row=0, column=1, padx=10, sticky='nsw')

        self.file_type_entry = tk.StringVar()
        ttk.Radiobutton(sample_type_option_panel, text='EDF File', variable=self.file_type_entry, value='edf').grid(row=0, column=0, padx=10, sticky='nsw', pady=5)
        ttk.Radiobutton(sample_type_option_panel, text='Annotation Epochs', variable=self.file_type_entry, value='annot').grid(row=1, column=0, padx=10, sticky='nsw', pady=5)
        self.file_type_entry.set(value='edf')

        sample_type_panel.rowconfigure(0, weight=1)

        output_path_panel = tk.Frame(group_panel, borderwidth=1, relief='groove')
        output_path_panel.pack(fill='x')

        tk.Label(output_path_panel, text="Output Path:", width=12, anchor='e').grid(row=0, column=0, padx=10, sticky='nse', pady=5)

        self.output_path_entry = ttk.Entry(output_path_panel, width=35, textvariable='folder_path_output', font=(self.font_name, self.font_size))
        self.output_path_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Button(output_path_panel, text='Browse', command=self.browseOutputFolder).grid(row=0, column=2, padx=10)

        self.status_textarea = scrolledtext.ScrolledText(input_panel, borderwidth=1, state=tk.DISABLED, relief='groove')
        self.status_textarea.pack(fill='both')

    # --------------------------------------------------------------------------
    def setOutputPanel(self):
    
        output_panel = tk.Frame(self.master, width=self.width-20, height=int(self.height*0.7), borderwidth=1, relief='groove')
        output_panel.pack(padx=10)
        output_panel.pack_propagate(0)

        self.tab_control = ttk.Notebook(output_panel)
        self.tab_control.pack(expand=True, fill='both')

        style = ttk.Style()
        style.configure("mystyle.Treeview", highlightthickness=0, bd=0) # Modify the font of the body
        style.configure("mystyle.Treeview.Heading", font=(self.font_name, self.font_size, 'bold')) # Modify the font of the headings
        style.layout("mystyle.Treeview", [('mystyle.Treeview.treearea', {'sticky': 'nswe'})]) # Remove the borders

        self.output_plot = tk.Canvas(self.tab_control, borderwidth=1, relief='solid')
        self.output_sc_st = ttk.Treeview(self.tab_control, selectmode='browse', style="mystyle.Treeview")

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

        self.output_sc_st.tag_configure('odd', background='#E8E8E8')
        self.output_sc_st.tag_configure('even', background='#DFDFDF')

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

        self.ct_options = tk.Frame(self.tab_control)
        self.ct_options.pack(fill=tk.BOTH, expand=1)
        #self.ct_options.pack_propagate(0)

        tk.Label(self.ct_options, text="We have found cut options for long NREM cycle. Please select the options you like and click 'Execute'.", anchor='e').pack()

        cut_table_container = tk.Frame(self.ct_options, height=100, borderwidth=1, relief='solid')
        cut_table_container.pack(fill=tk.X, pady=10)
        cut_table_container.pack_propagate(0)
        self.cut_table = CbTreeview(cut_table_container, self.font_name, self.font_size)#, style="mystyle.Treeview")
        self.cut_table.pack(fill=tk.X)

        self.cut_table.tag_configure('odd', background='#E8E8E8')
        self.cut_table.tag_configure('even', background='#DFDFDF')

        self.cut_table['columns']= ('NREMP EPOCH RANGE', 'SLEEP CYCLE INDEX','CUT POINT EPOCH', 'SELECT')
        self.cut_table.column("#0", width=0,  stretch=tk.NO)
        self.cut_table.column("NREMP EPOCH RANGE", anchor=tk.CENTER, width=80)
        self.cut_table.column("SLEEP CYCLE INDEX", anchor=tk.CENTER, width=80)
        self.cut_table.column("CUT POINT EPOCH", anchor=tk.CENTER, width=80)
        self.cut_table.column("SELECT", anchor=tk.CENTER, width=80)

        self.cut_table.heading("#0", text="", anchor=tk.CENTER)
        self.cut_table.heading("NREMP EPOCH RANGE", text="NREMP EPOCH RANGE",anchor=tk.CENTER)
        self.cut_table.heading("SLEEP CYCLE INDEX", text="SLEEP CYCLE INDEX", anchor=tk.CENTER)
        self.cut_table.heading("CUT POINT EPOCH", text="CUT POINT EPOCH", anchor=tk.CENTER)
        self.cut_table.heading("SELECT", text="SELECT", anchor=tk.CENTER)

        self.cut_plot = tk.Canvas(self.ct_options, borderwidth=1, relief='solid')
        self.cut_plot.pack(expand=1, fill=tk.BOTH, ipadx=10, ipady=10)
        self.cut_plot.bind("<Configure>", lambda event: self.showPlot(self.cut_plot))

        self.tab_control.add(self.output_plot, text='Visualization')
        self.tab_control.add(self.output_sc_st, text='Sleep Cycles and Stages')
        self.tab_control.add(self.ct_options, text='NREM Cut Options')

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
    def whileLoadingPlot(self, ele):
    
        ele.delete('all')
        x, y = ele.winfo_width()//2, ele.winfo_height()//2
        ele.create_text(x, y, text="Generating Visualization...", fill="black", font=(f'{self.font_name} {self.font_size+10} bold'))
        self.master.update()

    # --------------------------------------------------------------------------
    def showPlot(self, ele):

        ele.delete('all')
        if os.path.exists(self.img_path): 
            img = Image.open(self.img_path)
            w, h = ele.winfo_width(), ele.winfo_height()
            img.thumbnail((w, h), Image.ANTIALIAS)
            bg = ImageTk.PhotoImage(img)
            ele.create_image(int(w//2), int(h//2), image = bg, anchor = tk.CENTER)
            ele.image = bg
        else:
            x, y = ele.winfo_width()//2, ele.winfo_height()//2
            ele.create_text(x, y, text="Failed to generate visualization", fill="black", font=(f'{self.font_name} {self.font_size+10} bold'))

        self.master.update()

    # --------------------------------------------------------------------------
    def execute(self):

        print('Showing outputs')
        self.whileLoadingPlot(self.output_plot)
        self.whileLoadingPlot(self.cut_plot)
        self.controller.execute(self)

        self.img_path = os.path.join(self.controller.scv_obj.folder_cache, f'{self.controller.scv_obj.sample_name}.jpg')
        self.showPlot(self.output_plot)
        self.showPlot(self.cut_plot)
        self.clearTree(self.output_sc_st)

        sc_path = os.path.join(self.controller.scv_obj.folder_cache, f'{self.controller.scv_obj.sample_name}_sc.txt')
        st_path = os.path.join(self.controller.scv_obj.folder_cache, f'{self.controller.scv_obj.sample_name}_st.txt')
        if os.path.exists(sc_path) and os.path.exists(st_path):
            data_sc = [item[1:] for item in readFileInTable(sc_path)]
            data_st = [item[1:] for item in readFileInTable(st_path)]
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

        if len(self.controller.scv_obj.cut_options) > 0:
            cut_options, cut_options_selected = self.controller.scv_obj.cut_options, self.controller.scv_obj.cut_options_selected
            self.clearTree(self.cut_table)
            for i, epoch in enumerate(cut_options):
                checked = (epoch in cut_options_selected)
                sc_index = data_sc[epoch][0]

                for start in range(epoch, -1, -1):
                    if sc_index != data_sc[start][0]: break
                for end in range(epoch, len(data_sc)):
                    if sc_index != data_sc[end][0]: break

                epoch_range = f'{start}-{end}'
                self.cut_table.insert(parent='', index='end', iid=i, text='', values=(epoch_range, sc_index, epoch), tags=('odd' if i % 2 else "even"), checked=checked)   

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