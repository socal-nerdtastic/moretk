#!/usr/bin/env python3

# TODO: message when exceeding max hits
# TODO: popup width should match entry width
# TODO: optional scrollbar when exceeding max hits
# TODO: optional dropdown trigger
# TODO: move color selection to be kwargs in Autocomplete

import tkinter as tk

class SelectLabel(tk.Frame):
    SELECTED_COLOR = 'light blue'
    HOVER_COLOR = 'teal'
    NORMAL_COLOR = 'white'
    """this widget is a single row item in the result list
    turn color when hovered, allow for selection"""
    def __init__(self, master, **kwargs):
        self.text = kwargs.pop('text','')
        self.command = kwargs.pop('command', None)
        super().__init__(master, relief=tk.SUNKEN, bd=1, **kwargs)
        self.prefix = tk.Label(self, bd=0, padx=0, bg=self.NORMAL_COLOR)
        self.prefix.pack(side=tk.LEFT)
        self.select_core = tk.Label(self, bd=0, padx=0, bg=self.SELECTED_COLOR)
        self.select_core.pack(side=tk.LEFT)
        self.rest = tk.Label(self, text=self.text, bd=0, padx=0, anchor=tk.W, bg=self.NORMAL_COLOR)
        self.rest.pack(fill=tk.X, expand=True)
        self.rest.bind('<Button>', self.choose)
        self.select_core.bind('<Button>', self.choose)
        self.prefix.bind('<Button>', self.choose)
        self.bind('<Enter>', self.highlight)
        self.bind('<Leave>', self.lowlight)

        self.next = None
        self.previous = None

    def choose(self, event=None):
        if self.command:
            self.command(self.text)

    def highlight(self, event=None):
        if self.master.selected is not None:
            self.master.selected.lowlight()
        self.master.selected = self

        self.prefix.config(bg=self.HOVER_COLOR)
        self.select_core.config(bg=self.HOVER_COLOR)
        self.rest.config(bg=self.HOVER_COLOR)

    def lowlight(self, event=None):
        # will be called twice
        # by the mouse leave AND other.mouse enter ... i'm ok with this (for now)
        self.prefix.config(bg=self.NORMAL_COLOR)
        if self.select_core['text']:
            self.select_core.config(bg=self.SELECTED_COLOR)
        else:
            # this case should never happen, zero matches should delete the label.
            self.select_core.config(bg=self.NORMAL_COLOR)
        self.rest.config(bg=self.NORMAL_COLOR)

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
        return 0, len(search_phrase)

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
    def __init__(self, master, options=[], command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.items = [] # a list of SelectLabel objects
        self.command = command
        self.selected = None

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

    def remake(self, options, hitlimit=None, limit_action=None):
        if hitlimit and len(options) > hitlimit:
            if limit_action == 'warn':
                self.make_warn(options)
            elif limit_action == 'scrollbar':
                self.make_scroll(options, hitlimit)
            else:
                raise NotImplementedError("WTF? this should never happen")
        else:
            self.make_normal(options)

    def make_warn(self, options):
        while self.items:
            self.items.pop().destroy()
        lbl = tk.Label(self, text=f"<{len(options)} items match>")
        lbl.text = None
        lbl.pack()
        self.items.append(lbl)

    def make_scroll(self, options):
        pass

    def make_normal(self, options):
        current = {lbl.text:lbl for lbl in self.items}
        self.items = []
        for text, match in options:
            if text in current:
                lbl = current.pop(text)
                lbl.pack_forget()
            else:
                lbl = SelectLabel(self, command=self.command, text=text)
            lbl.pack(expand=True, fill=tk.X)
            lbl.select(match)
            self.items.append(lbl)

        # delete all remaining labels
        for child in current.values():
            child.destroy()

        # set up linked list
        if self.items:
            for a, b, c in zip(self.items, self.items[1:] + [self.items[0]], [self.items[-1]] + self.items[:-1]):
                a.next = b
                a.previous = c

        self.master.update_idletasks()  # Needed on MacOS -- see #34275.

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
        super().__init__(master, **kwargs)
        vcmd = self.register(self._on_change), '%P'
        self.config(validate="key", validatecommand=vcmd)
        self.options = options or []
        self.hitlimit = hitlimit
        self.limit_action = limit_action
        if self.limit_action == "scrollbar":
            raise NotImplementedError('Scrollbar not yet implemented')
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
        if P:
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
        elif len(matches) > self.hitlimit and self.limit_action == 'nothing':
            self._close_popup()
        else:
            self._open_popup()
            self.optionbox.remake(matches, self.hitlimit, self.limit_action)

    def _close_popup(self, event=None):
        if self.optionbox:
            self.optionbox.master.destroy()
            self.optionbox = None

    def _open_popup(self):
        if self.optionbox:
            return # already open

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

        self.optionbox = OptionBox(popup, command=self.set)
        self.optionbox.pack(fill=tk.BOTH, expand=True)
        popup.lift()  # work around bug in Tk 8.5.18+ (issue #24570)

def demo():
    # test / demo
    data = ['Abiu', 'Açaí', 'Ackee', 'Apple', 'Apricot', 'Avocado', 'Banana', 'Bilberry', 'Blackberry', 'Blackcurrant', 'Black sapote', 'Blueberry', 'Boysenberry', 'Breadfruit', "Buddha's hand", 'Cactus pear', 'Cempedak', 'Crab apple', 'Currant', 'Cherry', 'Cherimoya', 'Chico fruit', 'Cloudberry', 'Coco De Mer', 'Coconut', 'Cranberry', 'Damson', 'Date', 'Dragonfruit', 'Durian', 'Egg Fruit', 'Elderberry', 'Feijoa', 'Fig', 'Goji berry', 'Gooseberry', 'Grape', 'Grewia asiatica', 'Raisin', 'Grapefruit', 'Guava', 'Hala Fruit', 'Honeyberry', 'Huckleberry', 'Jabuticaba', 'Jackfruit', 'Jambul', 'Japanese plum', 'Jostaberry', 'Jujube', 'Juniper berry', 'Kiwano', 'Kiwifruit', 'Kumquat', 'Lemon', 'Lime', 'Loganberry', 'Loquat', 'Longan', 'Lulo', 'Lychee', 'Mamey Apple', 'Mamey Sapote', 'Mango', 'Mangosteen', 'Marionberry', 'Melon', 'Cantaloupe', 'Galia melon', 'Honeydew', 'Watermelon', 'Miracle fruit', 'Monstera deliciosa', 'Mulberry', 'Nance', 'Nectarine', 'Orange', 'Blood orange', 'Clementine', 'Mandarine', 'Tangerine', 'Papaya', 'Passionfruit', 'Peach', 'Pear', 'Persimmon', 'Plantain', 'Plum', 'Prune', 'Pineapple', 'Pineberry', 'Plumcot', 'Pluot', 'Pomegranate', 'Pomelo', 'Purple mangosteen', 'Quince', 'Raspberry', 'Salmonberry', 'Rambutan', 'Redcurrant', 'Salal berry', 'Salak', 'Satsuma', 'Soursop', 'Star apple', 'Star fruit', 'Strawberry', 'Surinam cherry', 'Tamarillo', 'Tamarind', 'Tangelo', 'Tayberry', 'Tomato', 'Ugli fruit', 'White currant', 'White sapote', 'Yuzu', 'Bell pepper', 'Chile pepper', 'Corn kernel', 'Cucumber', 'Eggplant', 'Jalapeño', 'Olive', 'Pea', 'Pumpkin', 'Squash', 'Tomato', 'Zucchini']

    root = tk.Tk()
    tk.Label(root, text='Type a fruit').pack()
    box = Autocomplete(root, options=data)
    box.focus()
    box.pack()

    tk.Label(root, text='Type another fruit\n(case sensitive)').pack()
    var = tk.StringVar()
    box = Autocomplete(root, options=data, textvariable=var, func="startswith_keepcase")
    var.set('test')
    box.pack()

    tk.Label(root, text='Contains check, try "am"').pack()
    box = Autocomplete(root, options=data, func="contains")
    var.set('test')
    box.pack()

    root.mainloop()

if __name__ == "__main__":
    Autocomplete.demo()

