import sys
if sys.version_info.major == 2:
    import Tkinter
    import tkFileDialog
    import tkColorChooser
    import tkFont
    import tkSimpleDialog
elif  sys.version_info.major == 3:
    import tkinter as Tkinter
    import tkinter.filedialog as tkFileDialog
    import tkinter.colorchooser as tkColorChooser
    import tkinter.font as tkFont
    import tkinter.simpledialog as tkSimpleDialog
else:
    raise UserWarning("unknown python version?!")

import re
import tkFontChooser
import Config
import Editor
import Filters
import WordColor
import GamelogReader
import util
import os
import TagConfig
from collections import OrderedDict

# import psutil,time

def dict_to_font(dict_):
    return tkFont.Font(family=dict_["family"], size=dict_["size"], weight=dict_["weight"], slant=dict_["slant"], overstrike=dict_["overstrike"], underline=dict_["underline"])

class announcement_window(Tkinter.Frame):
    def __init__(self, parent, id_):
        Tkinter.Frame.__init__(self, parent)
        self.parent = parent
        self.id = id_
        self.show_tags = False
        self.index_dict = {}
        Filters.expressions.add_window(self.id)
        self.customFont = dict_to_font(self.parent.gui_data['font_w%s' % self.id])
        self.config_gui = None
        self.vsb_pos = 1.0
        self.init_text_window()
        self.init_pulldown()

    def init_text_window(self):
        # Title Label
        try:
            title = Config.settings.window_titles[self.id]
        except:
            title = "Window %d" % self.id
            
        self.header_frame = Tkinter.Frame(self, bg="gray")
        self.header_frame.pack(side="top", fill="x")

        # Title Label (Left)
        self.title_label = Tkinter.Label(self.header_frame, text=title, bg="gray", fg="white", font=("Helvetica", 10, "bold"))
        self.title_label.pack(side="left")
        self.title_label.bind("<Double-Button-1>", self.edit_title)

        # ID Label (Right of Title)
        self.id_label = Tkinter.Label(self.header_frame, text="[%d]" % self.id, bg="gray", fg="lightgray", font=("Helvetica", 8, "bold"))
        self.id_label.pack(side="left", padx=10)

        self.text = Tkinter.Text(self, bg="black", wrap="word", font=self.customFont)
        self.vsb = Tkinter.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.text.config(cursor="")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.bind(util.mouse_buttons.right, self.popup)

        # link methods
        self.insert = self.text.insert
        self.delete = self.text.delete
        self.get = self.text.get
        self.index = self.text.index
        self.search = self.text.search
        self.tag_add = self.text.tag_add
        self.tag_config = self.text.tag_config
        self.tag_delete = self.text.tag_delete
        self.tag_names = self.text.tag_names
        self.tag_cget = self.text.tag_cget
        self.config = self.text.config
        self.yview = self.text.yview

    def edit_title(self, event):
        new_title = tkSimpleDialog.askstring("Rename Window", "Enter new title:", initialvalue=Config.settings.window_titles[self.id], parent=self)
        if new_title:
            self.title_label.config(text=new_title)
            Config.settings.window_titles[self.id] = new_title
            Config.settings.save()

    def init_pulldown(self):
        self.pulldown = Tkinter.Menu(self, tearoff=0)
        bg = "white"
        if util.platform.win or util.platform.osx:
            bg = "SystemMenu"
        self.pulldown.add_command(label="Window %d" % self.id, activebackground=bg, activeforeground="black")
        self.pulldown.add("separator")
        self.pulldown.add_command(label="Change Font", command=self.edit_font)
        self.pulldown.add_command(label="Toggle Tags", command=self.toggle_tags)
        self.pulldown.add_command(label="Clear Window", command=self.clear_window)

    def popup(self, event):
        if self.focus_get() is not None:
            self.pulldown.tk_popup(event.x_root, event.y_root)

    def toggle_tags(self):
        self.show_tags = not self.show_tags
        self.config(state="normal")
        self.gen_tags()
        self.config(state="disabled")

    def edit_font(self):
        tup = tkFontChooser.askChooseFont(self.parent, defaultfont=self.customFont)
        if tup is not None:
            self.customFont = tkFont.Font(font=tup)
            self.parent.gui_data['font_w%s' % self.id] = self.customFont.actual()
            self.config(font=self.customFont)

    def close_config_gui(self):
        self.config_gui.destroy()
        self.config_gui = None
        Filters.expressions.save_filter_data()
        Filters.expressions.reload()
        self.parent.gen_tags()

    def clear_window(self):
        self.config(state="normal")
        self.delete('1.0', "end")
        self.gen_tags(clear_index_dict=True)
        self.config(state="disabled")

    def gen_tags(self, clear_index_dict=False):
        """Generate the tkinter tags for coloring
        """        
        self.vsb_pos = (self.vsb.get()[1])
        colordict=Config.settings.word_color_dict
        for group_ in Filters.expressions.groups.items():
            # Group Coloring
            group = group_[1]
            for category_ in group.categories.items():
                category = category_[1]
                tag_name = "%s.%s" % (group.group, category.category)
                # set_elide =
                self.tag_config('%s.elide' % tag_name, foreground="#FFF", elide=not (self.show_tags and category.get_show(self.id)))
                self.tag_config(tag_name, foreground=group.color, elide=not category.get_show(self.id))
                if clear_index_dict:
                    self.index_dict[tag_name] = 0
                elif not (tag_name in self.index_dict):
                    self.index_dict[tag_name] = 0
        for color in colordict:
            # Word Coloring
            self.tag_config(color, foreground=colordict[color][0], background=colordict[color][1])
        if self.vsb_pos == 1.0:
            self.yview("end")


    def insert_ann(self, ann):
        def insert():
            anngroup = ann.get_group()
            anncat   = ann.get_category()
            tag_name = "%s.%s" % (anngroup, anncat)

            # prefix ([group][category]) as in the original
            self.insert("end", "[%s][%s] " % (anngroup, anncat), '%s.elide' % tag_name)

            text  = ann.get_text()
            words = WordColor.wd.get_all_group_words(anngroup) or []

            if words:
                # Build regex that captures the WORD and the following separator (space/punct/EOL).
                # We tag only the word, then re-emit the exact separator so spacing/punctuation remains intact.
                pattern = r'(\b(?:' + '|'.join(map(re.escape, words)) + r')\b)(?P<sep>\s|[.,;:!?)\]]|$)'
                regex = re.compile(pattern)

                pos = 0
                for m in regex.finditer(text):
                    # 1) Text before match (unchanged)
                    if m.start() > pos:
                        self.insert("end", text[pos:m.start()], tag_name)

                    # 2) Matched word
                    word = m.group(1)
                    self.insert("end", word, tag_name)

                    # Tag the word span we just inserted
                    colorname = WordColor.wd.get_colorname(word, anngroup)
                    if colorname:
                        start = "end-" + str(1 + len(word)) + "c"
                        end   = "end-1c"
                        self.tag_add(colorname, start, end)

                    # 3) The exact following separator (space/punct/EOL)
                    sep = m.group('sep')
                    if sep:
                        self.insert("end", sep, tag_name)

                    pos = m.end()

                # 4) Remainder after the last match
                if pos < len(text):
                    self.insert("end", text[pos:], tag_name)
            else:
                # No color words configured for this group — insert as-is
                self.insert("end", text, tag_name)

            self.trim_announcements(tag_name)

        if ann.get_show(self.id):
            insert()
        elif Config.settings.save_hidden_announcements:
            insert()


    def trim_announcements(self, tag_name):
        if Config.settings.trim_announcements[self.id]:
            self.index_dict[tag_name] += 1
            if self.index_dict[tag_name] > Config.settings.trim_announcements[self.id]:
                index = int(float(self.text.index('%s.first' % tag_name)))
                self.delete("%d.0" % index, "%d.0" % (index + 1))

class main_gui(Tkinter.Tk):
    def __init__(self):
        Tkinter.Tk.__init__(self)
        self.iconbitmap(Config.settings.icon_path)
        self.title("Announcement Window+ v1.5.0")
        self.protocol('WM_DELETE_WINDOW', self.clean_exit)
        self.pack_propagate(False)
        self.config(bg="Gray", height=700, width=640)
        self.customFont = tkFont.Font(family='Lao UI', size=10)
        self.gui_data = Config.settings.load_gui_data()
        self.gamelog = GamelogReader.gamelog()
        self.connect()
        self.announcement_windows = OrderedDict([])
        self.cpu_max = {}
        self.py = None
        if self.gui_data is None:
            self.gui_data = {"sash_place":int(700 / 3.236)}

        # Ensure font data exists for all windows
        for i in range(Config.settings.window_count):
            if 'font_w%s' % i not in self.gui_data:
                self.gui_data['font_w%s' % i] = self.customFont.actual()
        self.locked = False
        self.init_menu()
        self.init_windows()
        self.gen_tags()
        # self.parallel()
        self.get_announcements(old=Config.settings.load_previous_announcements)
        self.pack_announcements()

    def init_menu(self):
        self.menu = Tkinter.Menu(self, tearoff=0)

        options_menu = Tkinter.Menu(self.menu, tearoff=0)
        options_menu.add_command(label="Filter Configuration", command=self.config_gui)
        options_menu.add_command(label="Edit filters.txt", command=self.open_filters)
        options_menu.add_command(label="Reload wordcolor.txt", command=WordColor.wd.reload)
        options_menu.add_command(label="Reload filters.txt", command=Filters.expressions.reload)
        options_menu.add_command(label="Reload Settings", command=self.reload_settings)

        self.settings_menu = Tkinter.Menu(self.menu, tearoff=0)
        self.settings_menu.add_command(label="Set Directory", command=self.askpath)
        self.settings_menu.add_command(label="Lock Window", command=self.lock_window)
        self.menu.add_cascade(label="Settings", menu=self.settings_menu)
        self.menu.add_separator()
        self.menu.add_cascade(label="Options", menu=options_menu)
        # self.menu.add_command(label="Dump CPU info",command = self.dump_info)

        self.config(menu=self.menu)

    def connect(self):
        if not self.gamelog.connect():
            # TODO: add dialog when gamelog is not found
            pass

    def dump_info(self):
        print('CPU-MAX:%f' % max(self.cpu_max["CPU"]))
        print('CPU-AVG:%f' % (sum(self.cpu_max["CPU"]) / len(self.cpu_max["CPU"])))

        print('MEM-MAX:%f MB' % max(self.cpu_max["MEM"]))
        print('MEM-AVG:%f MB' % (sum(self.cpu_max["MEM"]) / len(self.cpu_max["MEM"])))
        self.cpu_max["CPU"] = []
        self.cpu_max["MEM"] = []

    def init_windows(self):
        # self.panel = Tkinter.PanedWindow(self, orient="vertical", sashwidth=5)
        # self.panel.pack(fill="both", expand=1)

        cols = 2
        for i in range(0, Config.settings.window_count):
            self.announcement_windows[i] = announcement_window(self, i)
            row = i // cols
            col = i % cols
            self.announcement_windows[i].grid(row=row, column=col, sticky="nsew")
        
        # Configure Grid Weights
        # Columns
        for c in range(cols):
            self.grid_columnconfigure(c, weight=1)
        # Rows
        import math
        rows = int(math.ceil(Config.settings.window_count / float(cols)))
        for r in range(rows):
            self.grid_rowconfigure(r, weight=1)

        # self.panel.update_idletasks()
        # try:
        #     self.panel.sash_place(0, 0, self.gui_data["sash_place"])
        # except:
        #     pass

    def gen_tags(self):
        Filters.expressions.reload()
        for announcement_win in self.announcement_windows.items():
            announcement_win[1].config(state="normal")
            announcement_win[1].gen_tags()
            announcement_win[1].config(state="disabled")

    def clean_exit(self):
        # self.gui_data["sash_place"] = self.panel.sash_coord(0)[1]
        Config.settings.save_gui_data(self.gui_data)
        self.destroy()

    def reload_settings(self):
        Config.settings.load()
        self.gen_tags()

    def edit_filters(self):
        Editor.TextEditor(Config.settings.filters_path)

    def open_filters(self):
        Editor.native_open(Config.settings.filters_path)

    def config_gui(self):
        Filters.expressions.reload()
        TagConfig.MainDialog(self)
        self.gen_tags()

    def askpath(self):
        path = Config.settings.get_gamelog_path()
        if os.path.isfile(path):
            new_path = tkFileDialog.askopenfilename(initialfile=path, parent=self, filetypes=[('log files', '.log'),('text files', '.txt'),('all files', '*.*')], title="Locate DwarfFortress/annc.log")
        else:
            new_path = tkFileDialog.askopenfilename(initialdir=path, parent=self, filetypes=[('log files', '.log'),('text files', '.txt'),('all files', '*.*')], title="Locate DwarfFortress/annc.log")
        if os.path.isfile(new_path):
            Config.settings.set_gamelog_path(new_path)
            Config.settings.save()
            self.connect()

    def lock_window(self):
        self.locked = not self.locked
        if util.platform.win:
            # Window decorations are not restored correctly on OS X when unlocking
            self.overrideredirect(self.locked)
        self.wm_attributes("-topmost", self.locked)
        tog_ = 'Unlock Window' if self.locked else 'Lock Window'
        self.settings_menu.entryconfig(self.settings_menu.index('end'), label=tog_)

    def get_announcements(self, old=False):
        if old:
            new_announcements = self.gamelog.get_old_announcements()
        else:
            new_announcements = self.gamelog.new()
        if new_announcements:
            for announcement_win in self.announcement_windows.items():
                announcement_win[1].vsb_pos = (announcement_win[1].vsb.get()[1])  # Jumps to end of list if the users scrollbar is @ end of list, otherwise holds current position
                announcement_win[1].text.config(state="normal")
            for ann in new_announcements:
                for announcement_win in self.announcement_windows.items():
                    announcement_win[1].insert_ann(ann)
            for announcement_win in self.announcement_windows.items():
                if announcement_win[1].vsb_pos == 1.0:
                    announcement_win[1].yview("end")
                announcement_win[1].text.config(state="disabled")
        self.after(1000, self.get_announcements)

    def pack_announcements(self):
        for announcement_win in self.announcement_windows.items():
            announcement_win[1].text.pack(side="top", fill="both", expand=True)
            # Why doesn't this always move to the end when you launch with setting: load_previous_announcements = True  ??
            announcement_win[1].yview("end")

    #===========================================================================
    # def parallel(self): #TODO: remove
    #     def find_process():
    #         for pid in psutil.pids():
    #             if psutil.Process(pid).name() == "python.exe":
    #                 if abs(psutil.Process(pid).create_time()-time.time()) < 5:
    #                     #was made less than 5 seconds ago
    #                     return psutil.Process(pid)
    #     if self.py is None:
    #         self.py = find_process()
    #         self.cpu_max["CPU"] = []
    #         self.cpu_max["MEM"] = []
    #         self.py.cpu_percent()
    #     else:
    #         self.cpu_max["MEM"].append(self.py.memory_info().rss/(1000*1024))
    #         self.cpu_max["CPU"].append(self.py.cpu_percent())
    #     self.after(5000,self.parallel)
    #
    #===========================================================================

if __name__ == "__main__":
    app = main_gui()
    app.mainloop()
