#!/usr/bin/env python3

import tkinter as tk

class DrawCanvas(tk.Canvas):
    """
    A canvas that will let you draw a shape on it
    by clicking and dragging the mouse.
    The Canvas acts as a normal canvas in every other way.

    :shape='rectangle': Can be 'rectangle', 'oval', or 'line'
    :command=None: the function to call when the mouse is released.
      Will be passed the bounding box as an argument
    :multiple=False: Allow multiple shapes to be drawn.
    """
    def __init__(self, master=None, command=None, shape='rectangle', multiple=False, **kwargs):
        super().__init__(master, **kwargs)
        self.command = command
        self.shape_cmds = {
            'rectangle': self.create_rectangle,
            'square': self.create_rectangle,
            'oval': self.create_oval,
            'circle': self.create_oval,
            'line': self.create_line,
            }
        self.shape = shape
        self.multiple = multiple

        self.start = None
        self.current = None
        self.refs = [] # list of screen objects

        self.bind("<Button>", self.on_click)
        self.bind("<ButtonRelease>", self.on_release)
        self.bind("<Motion>", self.on_motion)

    def on_click(self, event):
        if not self.multiple: self.clear()
        self.start = event.x, event.y
        cmd = self.shape_cmds[self.shape]
        if self.shape == 'line':
            kwargs = dict(fill='red', width=2)
        else:
            kwargs = dict(outline='red', width=2)
        self.current = cmd(*self.start, *self.start, **kwargs)
        self.refs.append(self.current)

    def on_motion(self, event):
        if self.current:
            x, y = event.x, event.y
            if self.shape in ('circle', 'square'):
                deltas = [a-b for a,b in zip((x,y), self.start)]
                d_min = min(abs(x) for x in deltas)
                x, y = (a+d_min*(1,-1)[d<0] for a,d in zip(self.start, deltas))
            self.coords(self.current, *self.start, x, y)

    def on_release(self, event):
        self.on_motion(event)
        self.current = None
        if self.command:
            self.command(*self.start, event.x, event.y)

    def clear(self):
        while self.refs:
            self.delete(self.refs.pop())

### test / demo:
def main():
    root = tk.Tk()
    lbl = tk.Label(text="One rectangle:")
    lbl.grid(row=0, column=0)
    var = tk.StringVar()
    def disp(*b_box):
        var.set(str(b_box))
    cvs = DrawCanvas(root, width=150, height=150, bg='white', command=disp)
    cvs.grid(row=1, column=0)
    lbl = tk.Label(textvariable=var)
    lbl.grid(row=2, column=0)

    lbl = tk.Label(text="Multiple ovals:")
    lbl.grid(row=0, column=1)
    cvs = DrawCanvas(root, width=150, height=150, bg='white', shape="oval", multiple=True)
    cvs.grid(row=1, column=1)
    btn = tk.Button(text="Clear", command=cvs.clear)
    btn.grid(row=2, column=1)

    lbl = tk.Label(text="Shape chooser:")
    lbl.grid(row=0, column=2)
    cvs = DrawCanvas(root, width=150, height=150, bg='white')
    cvs.grid(row=1, column=2)
    def set_shape(shape):
        cvs.shape = shape
    btn = tk.OptionMenu(root, tk.StringVar(value='rectangle'), 'rectangle','square','oval','circle','line', command=set_shape)
    btn.grid(row=2, column=2, sticky='ew')

    root.mainloop()

if __name__ == '__main__':
    main()
