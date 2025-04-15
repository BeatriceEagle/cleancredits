try:
    import tkinter as tk
    from tkinter import ttk
except ModuleNotFoundError as exc:
    tk = None
    ttk = None


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
        self.label = ttk.Label(parent, text=label_text)
        self.variable = variable
        self.command = command
        self.scale = ttk.Scale(
            parent,
            orient=tk.HORIZONTAL,
            from_=from_,
            to=to,
            variable=variable,
            command=self.handle_change,
        )
        self.value = ttk.Label(parent, text=self.get_value())

    def grid(self, row: int, column: int):
        self.label.grid(row=row, column=column, sticky="e")
        self.scale.grid(row=row, column=column + 1)
        self.value.grid(row=row, column=column + 2, sticky="w")

    def state(self, *args, **kwargs):
        self.scale.state(*args, **kwargs)

    def get_value(self):
        # Workaround - Passing an intvar as the label's textvariable makes it get rendered as a float.
        # We also want to limit the number of decimal places for actual floats.
        if type(self.variable) == tk.DoubleVar:
            return "{:.2f}".format(self.variable.get())
        return self.variable.get()

    def handle_change(self, e=None):
        self.value["text"] = self.get_value()
        self.command(e)
