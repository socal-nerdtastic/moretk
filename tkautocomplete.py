#!/usr/bin/env python3

# TODO: SelectLabel add flag is_highlighted to avoid duplicate lowlight calls
# TODO: figure out popup stay-on-top
# TODO: popup needs to move with window, or disappear
# TODO: popup width should match entry width

import tkinter as tk
from collections import deque

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

def startswith(whole_phrase, search_phrase):
    if whole_phrase.startswith(search_phrase):
        return 0, len(search_phrase)

def startswith_ignorecase(whole_phrase, search_phrase):
    if whole_phrase.casefold().startswith(search_phrase.casefold()):
        return 0, len(search_phrase)

class OptionBox(tk.Frame):
    """the popup widget"""
    def __init__(self, master, options=[], command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.sublabels = {}
        self.first = None
        self.command = command
        self.remake(options)
        self.selected = None

    def move_down(self):
        if self.selected is None and self.first is not None:
            self.first.highlight()
        elif self.selected is not None:
            self.selected.next.highlight()

    def move_up(self):
        if self.selected is None and self.first is not None:
            self.first.previous.highlight()
        elif self.selected is not None:
            self.selected.previous.highlight()

    def lowlight(self):
        if self.selected is not None:
            self.selected.lowlight()
        self.selected = None

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

        # set up LL
        labels = list(sublabels.values())
        if labels:
            self.first = labels[0]
            for a, b in zip(labels, labels[1:] + [labels[0]]):
                a.next = b
            for a, b in zip(labels, [labels[-1]] + labels[:-1]):
                a.previous = b
        else:
            self.first = None

        # delete all remaining labels
        for child in self.sublabels.values():
            child.destroy()

        self.sublabels = sublabels


class AutoComplete(tk.Entry):
    def __init__(self, master, options=None, hitlimit=50, func=startswith_ignorecase, **kwargs):
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
        self.bind('<Return>', self.on_return)

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
        self.var.set(value)
        self._close_popup()
        self.icursor(len(value))

    def _on_change(self, *args):
        P = self.var.get()

        if self.optionbox:
            self.optionbox.lowlight()

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

def main():
    # test / demo
    with open('fruit.txt') as f:
        data = f.read().splitlines()
    root = tk.Tk()
    tk.Label(root, text='Type a fruit').pack()
    box = AutoComplete(root, options=data)
    box.focus()
    box.pack()
    root.mainloop()

main()
