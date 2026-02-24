# TagConfig.py
# Filter Configuration dialog for AnnouncementWindow+
# ----------------------------------------------------------------------------------
# This version includes the following fixes and improvements:
#   - Normalizes category.show maps (int keys, real booleans) so initial Y/N states
#     render correctly even if the JSON contains string values like "true"/"false".
#   - Ensures every Category owns its own show dict to prevent shared-state bugs
#     (previously, toggling one row could affect others).
#   - Marks Y/N toggles as dirty and saves on Accept even if no regex text changed.
#
# Drop-in replacement for the original TagConfig.py used by the project.
# ----------------------------------------------------------------------------------

import sys
if sys.version_info.major == 2:
    import Tkinter
    import tkColorChooser
    import tkFont
elif sys.version_info.major == 3:
    import tkinter as Tkinter
    import tkinter.colorchooser as tkColorChooser
    import tkinter.font as tkFont
else:
    raise UserWarning("unknown python version?!")

import re
from functools import partial

import Filters
import Config
import util

LEFT = Tkinter.LEFT
RIGHT = Tkinter.RIGHT
CENTER = Tkinter.CENTER

# Flags used by the dialog:
RE_MODIFIED = False           # set when any regex text is changed
FILTERS_DIRTY = False         # set when any Y/N window-visibility toggle changes

# ------------------------------- helpers ------------------------------------ #

def _normalize_show(show_map):
    """
    Ensure window->bool mapping uses int keys and real booleans.
    Accepts 'true'/'false' (case-insensitive) and returns a NEW dict.
    """
    norm = {}
    if not isinstance(show_map, dict):
        return norm
    for k, v in show_map.items():
        try:
            ik = int(k)
        except Exception:
            ik = k
        if isinstance(v, bool):
            norm[ik] = v
        else:
            norm[ik] = (str(v).strip().lower() == "true")
    return norm



# ------------------------------- widgets ------------------------------------ #

class ExpressionBar(Tkinter.Frame):
    """
    One editable regex row inside a CategoryBar (per expression).
    """
    def __init__(self, parent, category, expression_index):
        Tkinter.Frame.__init__(self, parent)
        self.parent = parent
        self.category = category
        self.index = expression_index

        # Pull the compiled regex object and current pattern
        self.expression = None
        pattern = ""
        try:
            self.expression = category.re_expressions[self.index]
            pattern = getattr(self.expression, "pattern", "")
        except Exception:
            # category may not have expressions populated yet
            pattern = ""

        self.string_ = Tkinter.StringVar()
        self.string_.set(pattern)

        modcommand = self.register(self.exp_modified)

        self.entry = Tkinter.Entry(
            self,
            width=300,
            validate='key',
            validatecommand=(modcommand, '%P'),
            textvariable=self.string_
        )
        self.entry.pack(side=LEFT)

        # spacer
        Tkinter.Label(self, text=" ").pack(side=RIGHT)

    def exp_modified(self, text):
        """
        Recompile and store the modified regex; mark dialog as modified.
        """
        global RE_MODIFIED
        try:
            current = getattr(self.expression, "pattern", "")
        except Exception:
            current = ""

        if text == current:
            return True

        try:
            # compile and store back into the category model
            compiled = re.compile(text)
            self.expression = compiled
            try:
                self.category.re_expressions[self.index] = compiled
            except Exception:
                pass
            RE_MODIFIED = True
            return True
        except Exception:
            # refuse invalid regex changes at keystroke-level validation
            return False


class CategoryBar(Tkinter.Frame):
    """
    One row for a category:
      - Category label
      - Window visibility buttons (Y/N) per window index
      - Expandable list of ExpressionBars (regex list)
    """
    def __init__(self, parent, category, topparent, dialog):
        Tkinter.Frame.__init__(self, parent)
        self.parent = parent
        self.topparent = topparent
        self.dialog = dialog
        self.category = category
        self.is_grid = False

        # Normalize and deep-copy the show map so each Category has its own dict
        try:
            self.category.show = dict(_normalize_show(self.category.show))
        except Exception:
            # make sure show exists
            if not hasattr(self.category, "show") or not isinstance(self.category.show, dict):
                self.category.show = {}

        # expand/collapse control
        self.expand_button = Tkinter.Button(self, text="+", command=self.expand, width=1)
        self.expand_button.grid(row=0, column=0, sticky='w')

        # row frame (category name + window toggles)
        row_frame = Tkinter.Frame(self, background="lightgray")

        label = Tkinter.Label(
            row_frame,
            text=getattr(self.category, "category", ""),
            anchor="w",
            width=15,
            background='lightgray'
        )
        label.grid(row=0, column=0, sticky="w")

        col_ = 1
        # Create per-window toggle buttons
        for window, show in self.category.show.items():
            cbutton = Tkinter.Button(row_frame, background="gray", text="N", width=2)
            cbutton.config(command=partial(self.set_show, window, cbutton))
            cbutton.grid(row=0, column=col_)
            if bool(show):
                cbutton.config(text="Y", background="green")
            col_ += 1

        row_frame.grid(row=0, column=1, sticky="w")

        # expressions pane (hidden by default)
        self.expression_frame = Tkinter.Frame(self)

        try:
            expr_count = len(self.category.re_expressions)
        except Exception:
            expr_count = 0

        for row_ in range(0, expr_count):
            e_ = ExpressionBar(self.expression_frame, self.category, row_)
            e_.grid(row=row_, column=0, sticky="w")

    def set_show(self, window, button):
        """
        Toggle visibility for the given window index and update the button.
        """
        global FILTERS_DIRTY

        current = bool(self.category.show.get(window, False))
        new_val = not current
        self.category.show[window] = new_val
        FILTERS_DIRTY = True

        if new_val:
            button.config(text="Y", background="green")
        else:
            button.config(text="N", background="gray")

        try:
            print('Category: %s Window: %s Show: %s' %
                  (str(getattr(self.category, "category", "")), str(window), str(int(new_val))))
        except Exception:
            pass

    def expand(self):
        """
        Toggle the expressions list visibility.
        """
        if not self.is_grid:
            self.expression_frame.grid(row=1, column=1, sticky='w')
            self.expand_button.config(text="-")
        else:
            self.expression_frame.grid_forget()
            self.expand_button.config(text="+")
        self.is_grid = not self.is_grid

        self.dialog.resize()


class GroupBar(Tkinter.Frame):
    """
    Group header row and its list of CategoryBar rows.
    """
    def __init__(self, parent, group, dialog):
        Tkinter.Frame.__init__(self, parent)
        self.parent = parent
        self.group = group
        self.dialog = dialog
        self.is_grid = False

        if not hasattr(self.group, "color") or not self.group.color:
            self.group.color = "#808080"

        self.expand_button = Tkinter.Button(self, text="+", command=self.expand, width=1)
        self.expand_button.grid(row=0, column=0, sticky='w')

        header = Tkinter.Frame(self)

        label = Tkinter.Label(header, text=getattr(group, "group", ""), anchor="w", width=15, pady=0)
        label.grid(row=0, column=0)

        # Color chooser for the group color if supported by model

        # Get current group color (defaults to gray if not set)
        #current_color = getattr(self.group, "color", "#808080")
        current_color = self.group.color

        self.color_button = Tkinter.Button(
            header,
            text="Color",
            command=self.set_color,
            fg=current_color,                # text color = chosen color
            bg="black",                      # background fixed to black
            activeforeground=current_color,  # keep same text color when active
            activebackground="black",        # keep black bg when active
        )

        self.color_button.grid(row=0, column=1)

        header.grid(row=0, column=1, sticky="w")

        # Categories frame
        self.category_frame = Tkinter.Frame(self)

        # Title row for window indices (uses the first category as reference)
        title_frame = Tkinter.Frame(self.category_frame)
        gridrow = Tkinter.Frame(title_frame)
        label_frame = Tkinter.Frame(gridrow, width=128, height=21, background="gray")
        label_frame.pack_propagate(0)
        Tkinter.Label(label_frame, text="Window Visibility:", anchor="e", background="gray").pack(side=RIGHT)
        label_frame.grid(row=0, column=0, sticky="w")

        col_ = 1
        # Determine window count from first category (if any)
        first_cat = None
        try:
            for _name, cat in getattr(self.group, "categories", {}).items():
                first_cat = cat
                break
        except Exception:
            pass

        if first_cat and isinstance(getattr(first_cat, "show", {}), dict):
            for window in sorted(first_cat.show.keys()):
                win_frame = Tkinter.Frame(gridrow, width=18, height=21)
                win_frame.pack_propagate(0)
                Tkinter.Label(win_frame, text=str(window).rjust(3), anchor="w", background="gray").pack(fill="both", expand=True)
                win_frame.grid(row=0, column=col_)
                col_ += 1

        gridrow.grid(row=0, column=1, sticky="w")
        
        if hasattr(self.dialog, "_min_header_row") is False:
            self.dialog._min_header_row = gridrow

        title_frame.grid(row=0, column=0, sticky="w")

        # Populate categories
        row_ = 1
        try:
            items_iter = getattr(self.group, "categories", {}).items()
        except Exception:
            items_iter = []
        for _cname, category in items_iter:
            cbar = CategoryBar(self.category_frame, category, self.parent, dialog=self.dialog)
            cbar.grid(row=row_, column=0, sticky="w")
            row_ += 1

    
    
    def set_color(self):
        # Determine the current color to preselect
        current_color = getattr(self.group, "color", None)
        if not current_color:
            try:
                current_color = self.color_button.cget("fg")
            except Exception:
                current_color = "#808080"

        # Open the chooser with the current color preselected
        _rgb_tuple, chosen_hex = tkColorChooser.askcolor(
            parent=self,
            initialcolor=current_color
        )

        if chosen_hex is not None:
            try:
                # Persist to your model
                if hasattr(self.group, "set_color"):
                    self.group.set_color(chosen_hex)
                else:
                    self.group.color = chosen_hex

                # Re-style the button to reflect the new color
                self.color_button.config(
                    fg=chosen_hex,
                    bg="black",
                    activeforeground=chosen_hex,
                    activebackground="black",
                )

                # Mark UI dirty if you track that state
                global FILTERS_DIRTY
                FILTERS_DIRTY = True

            except Exception:
                pass


    def expand(self):
        """
        Toggle showing all categories of the group.
        """
        if not self.is_grid:
            self.category_frame.grid(row=1, column=1, sticky='w')
            self.expand_button.config(text="-")
        else:
            self.category_frame.grid_forget()
            self.expand_button.config(text="+")
        self.is_grid = not self.is_grid

        self.dialog.resize()


# ------------------------------- dialog ------------------------------------- #

class MainDialog(Tkinter.Toplevel):
    """
    The Filter Configuration dialog.
    """
    def __init__(self, parent, expressions=None):
        Tkinter.Toplevel.__init__(self, parent)

        self.parent = parent

        # Ensure the dialog always has a model to render:
        # 1) Use the provided model if passed.
        # 2) Fall back to Filters.expressions (used elsewhere in the app).
        # 3) As a last resort, try Filters.load() if the fork exposes it.
        self.expressions = expressions if expressions is not None else getattr(Filters, "expressions", None)
        if self.expressions is None and hasattr(Filters, "load"):
            try:
                self.expressions = Filters.load()
            except Exception as ex:
                print("Warning: Filters.load() failed:", ex)

        # Some forks provide expressions.reload() to rebuild from disk
        try:
            if self.expressions is not None and hasattr(self.expressions, "reload"):
                self.expressions.reload()
        except Exception as ex:
            print("Warning: expressions.reload() failed:", ex)

        # Debug: print what we ended up with so we can diagnose quickly
        try:
            grp = getattr(self.expressions, "groups", {})
            print("TagConfig: model ok | groups:", len(grp) if hasattr(grp, "keys") else "n/a")
        except Exception as ex:
            print("TagConfig: no model to render:", ex)

        # Usual window wiring
        self.withdraw()
        try:
            self.iconbitmap(Config.settings.icon_path)
        except Exception:
            pass

        if parent.winfo_viewable():
            self.transient(parent)
        self.resizable(1, 1)
        self.title("Filter Configuration")
        self.result = None

        self.gen_body()
        if not hasattr(self, "initial_focus") or not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        if self.parent is not None:
            try:
                self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
            except Exception:
                pass

        self.deiconify()  # become visible now
        self.initial_focus.focus_set()

        # wait for window to appear before grab_set
        self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

    def gen_body(self):
        self.body_frame = Tkinter.Frame(self)
        self.initial_focus = self.body(self.body_frame)
        # Size the canvas after layout completes
        self.after(0, self._set_initial_width)


        if not util.platform.osx:
            menu = Tkinter.Menu(self)
            menu.add_command(label="Accept", command=self.ok)
            menu.add_command(label="Cancel", command=self.cancel)
            self.config(menu=menu)
        else:
            # macOS doesn't put menu on dialogs by default; show inline buttons
            frame = Tkinter.Frame(self.body_frame)
            ok_button = Tkinter.Button(frame, text="Accept", command=self.ok)
            cancel_button = Tkinter.Button(frame, text="Cancel", command=self.cancel)
            ok_button.pack(side=LEFT)
            cancel_button.pack(side=RIGHT)
            frame.grid(row=0, column=0, sticky='sw')

        self.body_frame.grid(row=1, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.body_frame.grid_columnconfigure(0, weight=1)
        self.body_frame.grid_rowconfigure(0, weight=1)
        self.body_frame.grid_rowconfigure(1, weight=0)


    def body(self, master):
        # Canvas + inner content frame
        canvas = Tkinter.Canvas(master, borderwidth=0, highlightthickness=0)
        frame = Tkinter.Frame(canvas)

        # Scrollbars
        vscroll = Tkinter.Scrollbar(master, orient="vertical", command=canvas.yview)

        # Fixed-height wrapper row for the horizontal scrollbar (prevents height changes)
        sb_row = Tkinter.Frame(master, height=18)            # pick a height you like (16–18 typical)
        sb_row.grid(row=1, column=0, columnspan=2, sticky="ew")
        sb_row.grid_propagate(False)                         # lock the row height
        sb_row.pack_propagate(False)

        hscroll = Tkinter.Scrollbar(sb_row, orient="horizontal", command=canvas.xview)
        hscroll.configure(width=16)                          # scrollbar thickness in px (height for horizontal)
        hscroll.pack(side="top", fill="x", expand=False, pady=0, ipady=0)

        # Wire canvas to both scrollbars
        canvas.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        # Layout: [col 0 = canvas][col 1 = vscroll]; hscroll is inside sb_row
        canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        #hscroll.pack(side="top", fill="x")                  # pack inside the fixed-height wrapper

        # Grid weights: canvas grows; vscroll fixed; hscroll row fixed height
        master.grid_columnconfigure(0, weight=1)            # canvas column grows horizontally
        master.grid_columnconfigure(1, weight=0)            # vscroll column remains fixed
        master.grid_rowconfigure(0, weight=1)               # canvas row grows vertically
        master.grid_rowconfigure(1, weight=0)               # hscroll wrapper row stays fixed

        # Put the content frame into the canvas
        window_id = canvas.create_window((0, 0), window=frame, anchor="nw")
        self._window_id = window_id
        
        # Keep scrollregion in sync with content size
        def _on_frame_configure(event):
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except Exception:
                pass

        # Smart width handling:
        # - If the canvas is wider than the content, expand the inner frame to match (no horizontal scroll needed)
        # - If the canvas is narrower than the content, keep the content width (horizontal scrollbar remains useful)
        
        def _on_canvas_configure(event):
            try:
                # keep scrollregion current
                canvas.configure(scrollregion=canvas.bbox("all"))

                # grow inner frame to at least the canvas height (no big blank gap)
                frame.update_idletasks()
                natural_h = frame.winfo_reqheight()
                new_h = max(natural_h, event.height)
                canvas.itemconfig(window_id, height=new_h)
            except Exception:
                pass


        # Bind updates
        frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Populate groups
        try:
            groups = getattr(self.expressions, "groups", {})
            items_iter = groups.items() if hasattr(groups, "items") else []
        except Exception:
            items_iter = []

        row_ = 0
        for _gname, group in items_iter:
            gbar = GroupBar(frame, group, dialog=self)
            gbar.grid(row=row_, column=0, sticky="w", padx=4, pady=2)
            row_ += 1

        # Expose refs for sizing elsewhere
        self._canvas = canvas
        self._inner_frame = frame
        self._vscroll = vscroll
        self._hscroll = hscroll

        return frame


    def resize(self):
        """
        Re-pack / adjust geometry after expand/collapse events.
        """
        try:
            #self.update_idletasks()
            self.after_idle(self.refresh_scrollarea)
        except Exception:
            pass
    
    def refresh_scrollarea(self):
        """Recompute canvas scrollregion and ensure the inner window height matches the visible canvas."""
        try:
            # Make sure all newly expanded/collapsed widgets are realized
            self._inner_frame.update_idletasks()

            # Update scrollregion to the new content size
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))

            # Remove the vertical blank band by ensuring the inner window is at least canvas height
            natural_h = self._inner_frame.winfo_reqheight()
            visible_h = self._canvas.winfo_height()
            new_h = max(natural_h, visible_h)

            # Apply to the created inner window
            if hasattr(self, "_window_id") and self._window_id:
                self._canvas.itemconfig(self._window_id, height=new_h)
        except Exception:
            pass


    def _set_initial_width(self):
        """Clamp the canvas width to the natural content width (plus a bit),
        so the dialog isn't excessively wide; overflow uses the bottom scrollbar."""
        try:
            # Measure the natural width of the inner content
            self._inner_frame.update_idletasks()
            natural = self._inner_frame.winfo_reqwidth()

            # Measure the TRUE minimum from the Window Visibility (Y/N) header
            min_from_header = None
            header = getattr(self, "_min_header_row", None)
            if header is not None:
                header.update_idletasks()
                min_from_header = header.winfo_reqwidth()

            # Tweak these to taste:
            #MIN_W = 20    # a little wider than the Y/N area
            MAX_W = 520    # prevents sprawling
            PAD   = 32     # small gutter
            
            if min_from_header is not None:
                MIN_W = min_from_header + PAD
            else:
                MIN_W = 300  # fallback safety

            target = max(MIN_W, min(natural + PAD, MAX_W))

            # Apply width to the canvas; height handled by layout + vscroll
            self._canvas.configure(width=target)
            
            # Compute outer window width = canvas + vertical scrollbar + small gutters
            self.update_idletasks()
            outer_w = target + self._vscroll.winfo_reqwidth() + 8   # +8 for a tiny right gutter
            outer_h = self.winfo_reqheight()

            # Apply toplevel geometry so the window matches this width
            # (We preserve the current Y-size; vertical stretch is handled by grid + vscroll)
            x = self.winfo_rootx() if self.winfo_ismapped() else 100
            y = self.winfo_rooty() if self.winfo_ismapped() else 100

            self.geometry(f"{outer_w}x{outer_h}+{x}+{y}")
            #self.geometry(f"{outer_w}x{outer_h}")

            # Also set a sensible minimum
            #self.minsize(outer_w, outer_h)
            self.minsize(min_w + self._vscroll.winfo_reqwidth() + 6, outer_h)
            # # Set a minimum dialog size so it doesn't collapse too small
            #self.update_idletasks()
            #self.minsize(target + self._vscroll.winfo_reqwidth(),
            #            self.winfo_reqheight())

        except Exception:
            # Fail-safe: ignore errors; scrollbars still work
            pass

    # Persist changes when user hits Accept


    def ok(self):
        global RE_MODIFIED, FILTERS_DIRTY
        try:
            if RE_MODIFIED or FILTERS_DIRTY:
                expr = getattr(Filters, "expressions", None) or self.expressions

                # Save regex edits first (if present)
                if expr is not None and hasattr(expr, "save_filter_expressions"):
                    try:
                        expr.save_filter_expressions()
                    except Exception as ex:
                        print("Warning: save_filter_expressions failed:", ex)

                # Save window visibility (Y/N) + other filter data
                if expr is not None and hasattr(expr, "save_filter_data"):
                    try:
                        expr.save_filter_data()
                    except Exception as ex:
                        print("Warning: save_filter_data failed:", ex)

                if expr is None:
                    print("Warning: no expressions object available to save")

            # reset flags after attempting save
            RE_MODIFIED = False
            FILTERS_DIRTY = False

        except Exception as ex:
            print("Warning: failed to persist filters:", ex)

        # Close dialog
        self.withdraw()
        self.update_idletasks()
        self.cancel()



    def cancel(self, event=None):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()