import re

try:
    import tkinter as tk
    from tkinter import ttk
except ModuleNotFoundError as exc:
    tk = None
    ttk = None

import numpy as np

double_re = re.compile(r"^[0-9]+(\.[0-9]{,2})?$")


class Slider(object):
    def __init__(
        self,
        parent,
        label_text,
        from_=None,
        to=None,
        variable=None,
        command=None,
    ):
        self.parent = parent
        self.root = parent.winfo_toplevel()
        self.label = ttk.Label(parent, text=label_text)
        self.from_ = from_
        self.to = to
        self.variable = variable
        # Use a secret internal StringVar so that we can handle the
        # text parsing explicitly. (For example, handling an empty string
        # in the Entry is only possible with a StringVar.)
        self.textvariable = tk.StringVar()
        self.command = command
        self.scale = ttk.Scale(
            parent,
            orient=tk.HORIZONTAL,
            from_=from_,
            to=to,
            variable=variable,
        )

        self.value = ttk.Entry(
            parent,
            textvariable=self.textvariable,
            validate="key",
            validatecommand=(self.root.register(self.validate), "%P"),
            width=len(str(to)),
        )
        if type(self.variable) == tk.DoubleVar:
            self.value["width"] = len(str("{:.2f}".format(to)))
        self.textvariable.set(self.variable.get())
        self.textvariable.trace_add("write", self.handle_textvariable_change)
        self.variable.trace_add("write", self.handle_change)

        self.value.bind("<Up>", lambda e: self.increment(1))
        self.value.bind("<Shift-Up>", lambda e: self.increment(10))
        self.value.bind("<Down>", lambda e: self.increment(-1))
        self.value.bind("<Shift-Down>", lambda e: self.increment(-10))

    def grid(self, row: int, column: int):
        self.label.grid(row=row, column=column, sticky="e")
        self.scale.grid(row=row, column=column + 1)
        self.value.grid(row=row, column=column + 2, sticky="w")

    def state(self, *args, **kwargs):
        self.scale.state(*args, **kwargs)

    def validate(self, newval):
        if newval == "":
            return True
        if type(self.variable) == tk.DoubleVar:
            if not double_re.match(newval):
                return False
            parsed = float(newval)
        else:
            try:
                parsed = int(newval)
            except ValueError:
                return False

        if parsed < self.from_:
            return False
        if parsed > self.to:
            return False

        return True

    def increment(self, delta):
        old_value = self.variable.get()
        new_value = np.clip(old_value + delta, self.from_, self.to)
        if new_value != old_value:
            self.variable.set(new_value)
            self.handle_change()

    def handle_change(self, *args):
        val = self.variable.get()
        if type(self.variable) == tk.DoubleVar:
            val = "{:.2f}".format(float(val)).rstrip("0").rstrip(".")
        else:
            val = str(val)
        if self.textvariable.get() != val:
            self.textvariable.set(val)

    def handle_textvariable_change(self, *args):
        val = self.textvariable.get()
        if val == "" or not self.validate(val):
            return
        if type(self.variable) == tk.DoubleVar:
            val = float(val)
        else:
            val = int(val)
        if self.variable.get() != val:
            self.variable.set(val)
        if self.command is not None:
            self.command()
