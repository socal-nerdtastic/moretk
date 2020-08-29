#!/usr/bin/env python3

import tkinter as tk

class SelectLabel(tk.Frame):
    SELECTED_COLOR = 'light blue'
    HOVER_COLOR = 'teal'
    NORMAL_COLOR = 'white'
    """turn color when hovered, allow for selection"""
    def __init__(self, master, **kwargs):
        self.text = kwargs.pop('text','')
        self.command = kwargs.pop('command', None)
        super().__init__(master, relief=tk.SUNKEN, bd=1, **kwargs)
        self.prefix = tk.Label(self, bd=0, padx=0, bg=self.NORMAL_COLOR)
        self.prefix.pack(side=tk.LEFT)
        self.selected = tk.Label(self, bd=0, padx=0, bg=self.SELECTED_COLOR)
        self.selected.pack(side=tk.LEFT)
        self.rest = tk.Label(self, text=self.text, bd=0, padx=0, anchor=tk.W, bg=self.NORMAL_COLOR)
        self.rest.pack(fill=tk.X, expand=True)
        self.rest.bind('<Button>', self._mouse_click)
        self.selected.bind('<Button>', self._mouse_click)
        self.prefix.bind('<Button>', self._mouse_click)
        self.bind('<Enter>', self._mouse_enter)
        self.bind('<Leave>', self._mouse_leave)

    def _mouse_click(self, event=None):
        if self.command:
            self.command(self.text)

    def _mouse_enter(self, event=None):
        if self.master.selected is not None:
            self.master.move_none()
        self.prefix.config(bg=self.HOVER_COLOR)
        self.selected.config(bg=self.HOVER_COLOR)
        self.rest.config(bg=self.HOVER_COLOR)

    def _mouse_leave(self, event=None):
        self.prefix.config(bg=self.NORMAL_COLOR)
        if self.selected['text']:
            self.selected.config(bg=self.SELECTED_COLOR)
        else:
            # this case should never happen, zero matches should delete the label.
            self.selected.config(bg=self.NORMAL_COLOR)
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
        self.selected.config(text=self.text[start:end])
        self.rest.config(text=self.text[end:])

def startswith(whole_phrase, search_phrase):
    if whole_phrase.startswith(search_phrase):
        return 0, len(search_phrase)

class OptionBox(tk.Frame):
    def __init__(self, master, options=[], command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.sublabels = {}
        self.command = command
        self.remake(options)
        self.selected = None

    def move_down(self):
        if self.selected is None:
            self.selected = 0
        else:
            self.selected += 1
        self.highlight()
    def move_up(self):
        if self.selected is None:
            self.selected = -1
        else:
            self.selected -= 1
        self.highlight()
    def move_none(self):
        self.selected = None
        self.highlight()
    def highlight(self):
        if self.selected is not None:
            self.selected %= len(self.sublabels)
        for i, child in enumerate(self.sublabels.values()):
            if self.selected == i:
                child._mouse_enter()
            else:
                child._mouse_leave()

    def remake(self, options=[]):
        sublabels = {}
        for text, match in options:
            if text in self.sublabels:
                lbl = self.sublabels.pop(text)
                lbl.pack_forget()
            else:
                lbl = SelectLabel(self, command=self.command, text=text)
            lbl.pack(expand=True, fill=tk.X)
            lbl.select(match)
            sublabels[text] = lbl
        for text, child in list(self.sublabels.items()):
            child.destroy()
        self.sublabels = sublabels

class SearchEntry(tk.Entry):
    def __init__(self, master, options=None, hitlimit=50, func=startswith, **kwargs):
        self.var = kwargs.pop('textvariable', tk.StringVar(master))
        super().__init__(master, textvariable=self.var, **kwargs)
        self.var.trace('w', self._on_change)
        self.options = options or []
        self.hitlimit = hitlimit
        self.func = func
        self.popup = None
        self.optionbox = None

        self.bind('<Down>', self.move_down)
        self.bind('<Up>', self.move_up)

    def move_down(self, event=None):
        if self.optionbox:
            self.optionbox.move_down()

    def move_up(self, event=None):
        if self.optionbox:
            self.optionbox.move_up()

    def set(self, value):
        self.var.set(value)
        self._close_popup()
        self.icursor(len(value))

    def _on_change(self, *args):
        P = self.var.get()

        if self.optionbox:
            self.optionbox.move_none()

        if not P:
            return self._close_popup()

        matches = []
        for option in self.options:
            match = self.func(option, P)
            if match:
                matches.append((option, match))

        if not 1 <= len(matches) < self.hitlimit:
            return self._close_popup()

        self._open_popup()
        self.optionbox.remake(matches)
        self.popup.update_idletasks()  # Needed on MacOS -- see #34275.

    def _close_popup(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None
            self.optionbox = None

    def _open_popup(self):
        if self.popup:
            return # already open

        self.popup = tk.Toplevel(self, width=200)
        self.popup.wm_overrideredirect(1)
        try:
            # This command is only needed and available on Tk >= 8.4.0 for OSX.
            # Without it, call tips intrude on the typing process by grabbing the focus.
            self.popup.tk.call("::tk::unsupported::MacWindowStyle",
                "style", self.popup._w, "help", "noActivates")
        except tk.TclError:
            pass

        self.position_window()
        self.optionbox = OptionBox(self.popup, command=self.set)
        self.optionbox.pack(fill=tk.BOTH, expand=True)
        self.popup.lift()  # work around bug in Tk 8.5.18+ (issue #24570)

    def position_window(self):
        x, y = 0, self.winfo_height() + 1
        root_x = self.winfo_rootx() + x
        root_y = self.winfo_rooty() + y
        self.popup.wm_geometry("+%d+%d" % (root_x, root_y))

data = '''\
Documentation is like sex.
When it's good,
it's very good.
When it's bad,
it's better than nothing.
When it lies to you,
it may be a while before you realize something's wrong'''.lower().splitlines()

def main():
    root = tk.Tk()
    tk.Label(root, text='Type "when" or "it"').pack()
    box = SearchEntry(root, options=data)
    box.pack()
    root.mainloop()

main()
