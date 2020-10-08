#!/usr/bin/env python3

# TODO: popup width should match entry width
# TODO: add scroll with mousewheel when hovering over canvas
# TODO: add scroll with arrow key movement
# TODO: add fake scroll for very long data lists
# TODO: optional show all options dropdown trigger

import tkinter as tk

# default color palette
COLORS = dict(
    selected_color = 'light blue',
    hover_color = 'teal',
    normal_color = 'white')

class SelectLabel(tk.Frame):
    """this widget is a single row item in the result list
    turn color when hovered, allow for selection"""
    def __init__(self, master, controller, colors=COLORS, **kwargs):
        self.text = kwargs.pop('text','')
        self.command = kwargs.pop('command', None)
        self.colors = colors
        self.controller = controller
        super().__init__(master, relief=tk.SUNKEN, bd=1, **kwargs)
        self.prefix = tk.Label(self, bd=0, padx=0, bg=self.colors['normal_color'])
        self.prefix.pack(side=tk.LEFT)
        self.select_core = tk.Label(self, bd=0, padx=0, bg=self.colors['selected_color'])
        self.select_core.pack(side=tk.LEFT)
        self.rest = tk.Label(self, text=self.text, bd=0, padx=0, anchor=tk.W, bg=self.colors['normal_color'])
        self.rest.pack(fill=tk.X, expand=True)
        self.rest.bind('<Button-1>', self.choose)
        self.select_core.bind('<Button-1>', self.choose)
        self.prefix.bind('<Button-1>', self.choose)
        self.bind('<Enter>', self.highlight)
        self.bind('<Leave>', self.lowlight)

        self.next = None
        self.previous = None

    def choose(self, event=None):
        if self.command:
            self.command(self.text)

    def highlight(self, event=None):
        if self.controller.selected is not None:
            self.controller.selected.lowlight()
        self.controller.selected = self

        self.prefix.config(bg=self.colors['hover_color'])
        self.select_core.config(bg=self.colors['hover_color'])
        self.rest.config(bg=self.colors['hover_color'])

    def lowlight(self, event=None):
        # will be called twice
        # by the mouse leave AND other.mouse enter ... i'm ok with this (for now)
        self.prefix.config(bg=self.colors['normal_color'])
        if self.select_core['text']:
            self.select_core.config(bg=self.colors['selected_color'])
        else:
            # this case should never happen, zero matches should delete the label.
            self.select_core.config(bg=self.colors['normal_color'])
        self.rest.config(bg=self.colors['normal_color'])

    def select(self, start=None, end=None):
        """
        select(int) ==>
        select((start, end)) OR select(start, end) ==>
        """
        try:
            start, end = start
        except:
            pass
        if start is None:
            start, end = 0, 0
        if end is None:
            start, end = 0, start
        self.prefix.config(text=self.text[:start])
        self.select_core.config(text=self.text[start:end])
        self.rest.config(text=self.text[end:])

def startswith_keepcase(whole_phrase, search_phrase):
    if whole_phrase.startswith(search_phrase):
        return 0, len(search_phrase)

def startswith(whole_phrase, search_phrase):
    if whole_phrase.casefold().startswith(search_phrase.casefold()):
        return len(search_phrase)

def contains(whole_phrase, search_phrase):
    idx = whole_phrase.casefold().find(search_phrase.casefold())
    if idx >= 0:
        return idx, len(search_phrase) + idx

functions = dict(
    startswith = startswith,
    contains = contains,
    startswith_keepcase = startswith_keepcase,
    )

class OptionBox(tk.Frame):
    """the popup widget"""
    def __init__(self, master, options=[], command=None, colors=COLORS, **kwargs):
        super().__init__(master, **kwargs)
        self.colors = colors
        self.items = [] # a list of SelectLabel objects
        self.command = command
        self.selected = None
        self.disp_frame = self

    def move_down(self):
        if self.selected is None and self.items:
            self.items[0].highlight()
        elif self.selected is not None:
            self.selected.next.highlight()

    def move_up(self):
        if self.selected is None and self.items:
            self.items[0].previous.highlight()
        elif self.selected is not None:
            self.selected.previous.highlight()

    def lowlight(self):
        if self.selected is not None:
            self.selected.lowlight()
        self.selected = None

    def remake(self, options):
        current = {lbl.text:lbl for lbl in self.items}
        self.items = []
        for text, match in options:
            if text in current:
                lbl = current.pop(text)
                lbl.pack_forget()
            else:
                lbl = SelectLabel(self.disp_frame, controller=self, command=self.command, text=text, colors=self.colors)
            lbl.pack(expand=True, fill=tk.X)
            lbl.select(match)
            self.items.append(lbl)

        # delete all remaining labels
        for child in current.values():
            child.destroy()

        # set up linked list
        if self.items:
            for a, b, c in zip(self.items, self.items[1:] + [self.items[0]], [self.items[-1]] + self.items[:-1]):
                a.next, a.previous = b, c

        self.master.update_idletasks()  # Needed on MacOS -- see #34275.

class OptionBoxScroll(OptionBox):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        WIDTH = 130
        HEIGHT = 200
        canvas = tk.Canvas(self, width=WIDTH, height=HEIGHT)
        canvas.pack(side=tk.LEFT)
        vsb = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        canvas.configure(yscrollcommand = vsb.set)
        self.disp_frame = tk.Frame(canvas)
        self.disp_frame.columnconfigure(0, minsize=WIDTH)
        canvas.create_window(0, 0, window=self.disp_frame, anchor='nw')

        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        canvas.bind('<Configure>', on_configure)

class OptionBoxWarn(OptionBox):
    # subclass OptionBox instead of Frame simply to consume kwargs and populate vars
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self.lbl = tk.Label(self)
        self.lbl.pack()

    def remake(self, options):
        self.lbl.config(text=f"<{len(options)} items match>")

class Autocomplete(tk.Entry):
    """
    A type of tk.Entry that will pop up a list of matching choices as you type
    options: list of options for the user to choose from
    hitlimit: max number of hits to show
    limit_action: One of "nothing", "warn", "scrollbar"
    func: one of "startswith", "contains" or a function to use to determine if an option matches
    kwargs: passed on to the underlying Entry
    """
    def __init__(self, master, options=None, hitlimit=10, limit_action="warn", func="startswith", **kwargs):
        self.colors = {key:kwargs.pop(key, COLORS[key]) for key in COLORS}
        super().__init__(master, **kwargs)
        vcmd = self.register(self._on_change), '%P'
        self.config(validate="key", validatecommand=vcmd)
        self.options = options or []
        self.hitlimit = hitlimit
        self.limit_action = limit_action
        if limit_action not in ("warn", "nothing", "scrollbar"):
            raise TypeError(f'limit_action must be one of "warn", "nothing", "scrollbar", got {limit_action!r}')
        self.func = functions.get(func,func)
        self.optionbox = None

        self.bind('<Down>', self.move_down)
        self.bind('<Up>', self.move_up)
        self.bind('<Return>', self.on_return)
        self.bind('<FocusOut>', self._close_popup)

    def demo(self=None):
        demo()

    def on_return(self, event=None):
        if self.optionbox and self.optionbox.selected:
            self.optionbox.selected.choose()

    def move_down(self, event=None):
        if self.optionbox:
            self.optionbox.move_down()

    def move_up(self, event=None):
        if self.optionbox:
            self.optionbox.move_up()

    def set(self, value):
        self.delete(0, tk.END)
        self.insert(0, value)
        self._close_popup()
        self.icursor(len(value))

    def _on_change(self, P, *args):
        if P: # something was typed
            self._update_popup(P)
        else:
            self._close_popup()
        return True

    def _update_popup(self, P):
        if self.optionbox:
            self.optionbox.lowlight()

        matches = []
        for option in self.options:
            match = self.func(option, P)
            if match:
                matches.append((option, match))

        if len(matches) == 0:
            self._close_popup()
        elif len(matches) > self.hitlimit:
            if self.limit_action == 'nothing':
                self._close_popup()
            elif self.limit_action == 'warn':
                self._open_popup(OptionBoxWarn)
            elif self.limit_action == 'scrollbar':
                self._open_popup(OptionBoxScroll)
            else:
                raise TypeError(f"unknown limit action: {self.limit_action!r}")
        else:
            self._open_popup(OptionBox)

        if self.optionbox:
            self.optionbox.remake(matches)

    def _close_popup(self, event=None):
        if self.optionbox:
            self.optionbox.master.destroy()
            self.optionbox = None

    def _open_popup(self, popup_type):
        if self.optionbox and type(self.optionbox) == popup_type:
            return # already open
        else:
            self._close_popup()

        popup = tk.Toplevel(self, width=200)
        popup.wm_overrideredirect(1)
        try:
            # This command is only needed and available on Tk >= 8.4.0 for OSX.
            # Without it, call tips intrude on the typing process by grabbing the focus.
            popup.tk.call("::tk::unsupported::MacWindowStyle",
                "style", popup._w, "help", "noActivates")
        except tk.TclError:
            pass

        # position_window
        x, y = 0, self.winfo_height() + 1
        root_x = self.winfo_rootx() + x
        root_y = self.winfo_rooty() + y
        popup.wm_geometry("+%d+%d" % (root_x, root_y))

        self.optionbox = popup_type(popup, command=self.set, colors=self.colors)
        self.optionbox.pack(fill=tk.BOTH, expand=True)
        popup.lift()  # work around bug in Tk 8.5.18+ (issue #24570)

def demo():
    # test / demo
    from tkinter import ttk
    data = ['Abiu', 'Açaí', 'Ackee', 'Apple', 'Apricot', 'Avocado', 'Banana', 'Bilberry', 'Blackberry', 'Blackcurrant', 'Black sapote', 'Blueberry', 'Boysenberry', 'Breadfruit', "Buddha's hand", 'Cactus pear', 'Cempedak', 'Crab apple', 'Currant', 'Cherry', 'Cherimoya', 'Chico fruit', 'Cloudberry', 'Coco De Mer', 'Coconut', 'Cranberry', 'Damson', 'Date', 'Dragonfruit', 'Durian', 'Egg Fruit', 'Elderberry', 'Feijoa', 'Fig', 'Goji berry', 'Gooseberry', 'Grape', 'Grewia asiatica', 'Raisin', 'Grapefruit', 'Guava', 'Hala Fruit', 'Honeyberry', 'Huckleberry', 'Jabuticaba', 'Jackfruit', 'Jambul', 'Japanese plum', 'Jostaberry', 'Jujube', 'Juniper berry', 'Kiwano', 'Kiwifruit', 'Kumquat', 'Lemon', 'Lime', 'Loganberry', 'Loquat', 'Longan', 'Lulo', 'Lychee', 'Mamey Apple', 'Mamey Sapote', 'Mango', 'Mangosteen', 'Marionberry', 'Melon', 'Cantaloupe', 'Galia melon', 'Honeydew', 'Watermelon', 'Miracle fruit', 'Monstera deliciosa', 'Mulberry', 'Nance', 'Nectarine', 'Orange', 'Blood orange', 'Clementine', 'Mandarine', 'Tangerine', 'Papaya', 'Passionfruit', 'Peach', 'Pear', 'Persimmon', 'Plantain', 'Plum', 'Prune', 'Pineapple', 'Pineberry', 'Plumcot', 'Pluot', 'Pomegranate', 'Pomelo', 'Purple mangosteen', 'Quince', 'Raspberry', 'Salmonberry', 'Rambutan', 'Redcurrant', 'Salal berry', 'Salak', 'Satsuma', 'Soursop', 'Star apple', 'Star fruit', 'Strawberry', 'Surinam cherry', 'Tamarillo', 'Tamarind', 'Tangelo', 'Tayberry', 'Tomato', 'Ugli fruit', 'White currant', 'White sapote', 'Yuzu', 'Bell pepper', 'Chile pepper', 'Corn kernel', 'Cucumber', 'Eggplant', 'Jalapeño', 'Olive', 'Pea', 'Pumpkin', 'Squash', 'Tomato', 'Zucchini']

    root = tk.Tk()
    tk.Label(root, text='Demo of the Autocomplete widget', font=('', 18)).pack()
    tk.Label(root, text='Demo data is a list of fruits. Type a fruit name!').pack()

    f = ttk.Labelframe(root, text="Standard")
    f.pack(expand=True, fill=tk.X, ipady=2, ipadx=2, pady=2, padx=2)
    tk.Label(f, text='Autocomplete(f, options=data)').grid(sticky=tk.W)
    box = Autocomplete(f, options=data)
    box.focus()
    box.grid(sticky=tk.W)

    f = ttk.Labelframe(root, text="Contains check with variable")
    f.pack(expand=True, fill=tk.X, ipady=2, ipadx=2, pady=2, padx=2)
    tk.Label(f, text='var = tk.StringVar()\nAutocomplete(f, options=data, textvariable=var, func="contains")\nvar.set("test")', justify='left').grid(sticky=tk.W)
    var = tk.StringVar()
    box = Autocomplete(f, options=data, textvariable=var, func="contains")
    var.set('test')
    box.grid(sticky=tk.W)

    f = ttk.Labelframe(root, text="Different colors")
    f.pack(expand=True, fill=tk.X, ipady=2, ipadx=2, pady=2, padx=2)
    tk.Label(f, text="Autocomplete(f, options=data, hover_color='red', selected_color='green')", justify='left').grid(sticky=tk.W)
    box = Autocomplete(f, options=data, hover_color='red', selected_color='green')
    box.grid(sticky=tk.W)

    f = ttk.Labelframe(root, text="Scrollbar")
    f.pack(expand=True, fill=tk.X, ipady=2, ipadx=2, pady=2, padx=2)
    tk.Label(f, text="Autocomplete(f, options=data, func='contains', limit_action='scrollbar')", justify='left').grid(sticky=tk.W)
    box = Autocomplete(f, options=data, func='contains', limit_action='scrollbar'   )
    box.grid(sticky=tk.W)

    root.mainloop()

if __name__ == "__main__":
    Autocomplete.demo()
