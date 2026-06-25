"""Komponenty pomocnicze UI: color picker, date picker, rysowanie zaokrąglonych prostokątów."""

import tkinter as tk
import calendar
from datetime import date

FONT_FAMILY = "Segoe UI"


def draw_rounded_rect(canvas: tk.Canvas, x1, y1, x2, y2, radius, **kwargs):
    """Rysuje zaokrąglony prostokąt na Canvas jako wygładzony polygon."""
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=12, **kwargs)


class PriorityBadge(tk.Canvas):
    """Plakietka ważności w stylu znaku ostrzegawczego: żółte/czerwone tło, czarna ramka, !/!!"""

    COLORS = {
        1: ("#FFD43B", "#3A2E00"),   # żółte tło, ciemny tekst - "ważne"
        2: ("#FF6B6B", "#3A0000"),   # czerwone tło - "bardzo ważne"
    }

    def __init__(self, master, priority: int, size=22, bg=None, **kwargs):
        resolved_bg = bg if bg else (master["bg"] if isinstance(master, (tk.Frame, tk.Label, tk.Canvas)) else "white")
        super().__init__(master, width=size, height=size, highlightthickness=0, bg=resolved_bg)
        if priority not in (1, 2):
            return
        bg_color, fg_color = self.COLORS[priority]
        text = "!" if priority == 1 else "!!"
        cx, cy = size / 2, size / 2
        pts_radius = size * 0.46
        # Mała plakietka w kształcie zaokrąglonego kwadratu obróconego o 45° (jak "diamond")
        self.create_polygon(
            cx, cy - pts_radius, cx + pts_radius, cy, cx, cy + pts_radius, cx - pts_radius, cy,
            fill=bg_color, outline="#1A1A1A", width=1.5, smooth=True, splinesteps=4
        )
        self.create_text(cx, cy, text=text, font=(FONT_FAMILY, 8 if priority == 1 else 7, "bold"),
                          fill=fg_color)


class RoundedButton(tk.Canvas):
    """Zwykły przycisk z zaokrąglonymi rogami, do użycia np. w palecie kolorów lub CTA."""

    def __init__(self, master, text="", width=90, height=34, radius=10,
                 bg_color="#4285F4", fg_color="white", font=None, command=None, **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0,
                          bg=master["bg"] if hasattr(master, "__getitem__") else "white")
        self.command = command
        self.bg_color = bg_color
        self._draw(width, height, radius, bg_color, text, fg_color, font)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self.config(cursor="hand2"))

    def _draw(self, width, height, radius, bg_color, text, fg_color, font):
        self.delete("all")
        draw_rounded_rect(self, 1, 1, width - 1, height - 1, radius, fill=bg_color, outline=bg_color)
        self.create_text(width / 2, height / 2, text=text,
                          font=font or (FONT_FAMILY, 10, "bold"), fill=fg_color)

    def _on_click(self, event):
        if self.command:
            self.command()


class ColorPickerPanel(tk.Frame):
    """Estetyczny picker kolorów: siatka kolorowych kółek z zaznaczeniem + pasek odcieni (hue)."""

    PALETTE = [
        "#4285F4", "#0F9D58", "#F4511E", "#9C27B0", "#F6BF26",
        "#E91E63", "#16A2B8", "#5C6BC0", "#8D6E63", "#78909C",
    ]

    def __init__(self, master, bg, initial_color=None, on_change=None):
        super().__init__(master, bg=bg)
        self.bg = bg
        self.on_change = on_change
        self.selected_color = initial_color or self.PALETTE[0]
        self.swatch_canvases = []

        grid = tk.Frame(self, bg=bg)
        grid.pack()

        cols = 5
        for i, color in enumerate(self.PALETTE):
            r, c = divmod(i, cols)
            cv = tk.Canvas(grid, width=34, height=34, highlightthickness=0, bg=bg, cursor="hand2")
            cv.grid(row=r, column=c, padx=4, pady=4)
            self._draw_swatch(cv, color)
            cv.bind("<Button-1>", lambda e, col=color: self._select(col))
            self.swatch_canvases.append((cv, color))

        bottom = tk.Frame(self, bg=bg)
        bottom.pack(fill="x", pady=(10, 0))

        self.preview = tk.Canvas(bottom, width=28, height=28, highlightthickness=0, bg=bg)
        self.preview.pack(side="left")
        self._draw_preview()

        custom_btn = tk.Label(
            bottom, text="Własny kolor (RGB)…", font=(FONT_FAMILY, 9, "underline"),
            bg=bg, fg="#4285F4", cursor="hand2"
        )
        custom_btn.pack(side="left", padx=(10, 0))
        custom_btn.bind("<Button-1>", lambda e: self._open_custom_picker())

    def _draw_swatch(self, cv, color):
        cv.delete("all")
        is_selected = (color == self.selected_color)
        outline_w = 3 if is_selected else 0
        outline_color = "#1F2430" if is_selected else color
        pad = 3 if is_selected else 1
        cv.create_oval(pad, pad, 34 - pad, 34 - pad, fill=color, outline=outline_color,
                        width=outline_w if is_selected else 0)
        if is_selected:
            cv.create_text(17, 17, text="✓", fill="white", font=(FONT_FAMILY, 11, "bold"))

    def _draw_preview(self):
        self.preview.delete("all")
        self.preview.create_oval(2, 2, 26, 26, fill=self.selected_color, outline="#1F2430", width=1)

    def _select(self, color):
        self.selected_color = color
        for cv, c in self.swatch_canvases:
            self._draw_swatch(cv, c)
        self._draw_preview()
        if self.on_change:
            self.on_change(color)

    def _open_custom_picker(self):
        picker = HSVPickerDialog(self, initial=self.selected_color)
        self.wait_window(picker)
        if picker.result:
            self.selected_color = picker.result
            for cv, c in self.swatch_canvases:
                self._draw_swatch(cv, c)
            self._draw_preview()
            if self.on_change:
                self.on_change(picker.result)


class HSVPickerDialog(tk.Toplevel):
    """Prosty, czytelny picker RGB przez trzy slidery - własny, zamiast systemowego Windows."""

    def __init__(self, master, initial="#4285F4"):
        super().__init__(master)
        self.result = None
        self.title("Wybierz kolor")
        self.resizable(False, False)
        self.configure(bg="white")
        self.transient(master)
        self.grab_set()

        r, g, b = self._hex_to_rgb(initial)
        self.r_var = tk.IntVar(value=r)
        self.g_var = tk.IntVar(value=g)
        self.b_var = tk.IntVar(value=b)

        self.preview = tk.Canvas(self, width=220, height=60, highlightthickness=1,
                                  highlightbackground="#E3E7EE", bg="white")
        self.preview.pack(padx=16, pady=(16, 10))

        for label, var, color in [("R", self.r_var, "#D33B27"),
                                    ("G", self.g_var, "#0F9D58"),
                                    ("B", self.b_var, "#4285F4")]:
            row = tk.Frame(self, bg="white")
            row.pack(fill="x", padx=16, pady=4)
            tk.Label(row, text=label, font=(FONT_FAMILY, 10, "bold"), bg="white",
                     fg=color, width=2).pack(side="left")
            slider = tk.Scale(
                row, from_=0, to=255, orient="horizontal", variable=var,
                bg="white", troughcolor="#F1F3F8", highlightthickness=0,
                command=lambda v: self._update_preview(), length=180
            )
            slider.pack(side="left")

        btns = tk.Frame(self, bg="white")
        btns.pack(fill="x", padx=16, pady=(8, 16))
        tk.Button(btns, text="Anuluj", font=(FONT_FAMILY, 10), bg="white", fg="#7A8194",
                   relief="flat", bd=0, command=self.destroy).pack(side="left")
        tk.Button(btns, text="Wybierz", font=(FONT_FAMILY, 10, "bold"), bg="#4285F4",
                   fg="white", relief="flat", bd=0, padx=14, pady=5,
                   command=self._confirm).pack(side="right")

        self._update_preview()

    def _update_preview(self):
        hex_color = self._rgb_to_hex(self.r_var.get(), self.g_var.get(), self.b_var.get())
        self.preview.delete("all")
        self.preview.create_rectangle(0, 0, 220, 60, fill=hex_color, outline="")

    def _confirm(self):
        self.result = self._rgb_to_hex(self.r_var.get(), self.g_var.get(), self.b_var.get())
        self.destroy()

    @staticmethod
    def _hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(r, g, b):
        return f"#{r:02X}{g:02X}{b:02X}"


class DatePickerEntry(tk.Frame):
    """Pole daty z przyciskiem otwierającym mini-kalendarz do wyboru myszką."""

    def __init__(self, master, bg, initial_date: date = None, on_change=None):
        super().__init__(master, bg=bg)
        self.on_change = on_change
        self.selected_date = initial_date or date.today()

        self.display = tk.Label(
            self, text=self._fmt(self.selected_date), font=(FONT_FAMILY, 10),
            bg="#F1F3F8", fg="#1F2430", width=13, anchor="w", padx=8, pady=6,
            cursor="hand2"
        )
        self.display.pack(side="left")
        self.display.bind("<Button-1>", lambda e: self._open_picker())

        icon = tk.Label(self, text="📅", font=(FONT_FAMILY, 10), bg="#F1F3F8",
                         cursor="hand2", padx=6)
        icon.pack(side="left")
        icon.bind("<Button-1>", lambda e: self._open_picker())

    def _fmt(self, d: date):
        return d.strftime("%d.%m.%Y")

    def get_date(self):
        return self.selected_date

    def set_date(self, d: date):
        self.selected_date = d
        self.display.config(text=self._fmt(d))

    def _open_picker(self):
        popup = MiniCalendarPopup(self, initial=self.selected_date, on_pick=self._on_picked)

    def _on_picked(self, d: date):
        self.set_date(d)
        if self.on_change:
            self.on_change(d)


class MiniCalendarPopup(tk.Toplevel):
    """Małe okienko z kalendarzem miesięcznym do klikania konkretnej daty."""

    def __init__(self, master, initial: date, on_pick):
        super().__init__(master)
        self.on_pick = on_pick
        self.view_month = initial.replace(day=1)
        self.initial = initial

        self.overrideredirect(True)
        self.configure(bg="white", highlightthickness=1, highlightbackground="#D0D5DD")

        x = master.winfo_rootx()
        y = master.winfo_rooty() + master.winfo_height() + 4
        self.geometry(f"+{x}+{y}")

        self.bind("<FocusOut>", lambda e: self.destroy())

        header = tk.Frame(self, bg="white")
        header.pack(fill="x", padx=10, pady=(10, 4))
        tk.Button(header, text="‹", font=(FONT_FAMILY, 10, "bold"), bg="white", bd=0,
                   cursor="hand2", command=self._prev).pack(side="left")
        self.label = tk.Label(header, text="", font=(FONT_FAMILY, 10, "bold"), bg="white")
        self.label.pack(side="left", expand=True)
        tk.Button(header, text="›", font=(FONT_FAMILY, 10, "bold"), bg="white", bd=0,
                   cursor="hand2", command=self._next).pack(side="right")

        self.grid_frame = tk.Frame(self, bg="white")
        self.grid_frame.pack(padx=10, pady=(0, 10))

        self._render()
        self.focus_set()
        self.grab_set()

    def _render(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        names = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
        for i, n in enumerate(names):
            tk.Label(self.grid_frame, text=n, font=(FONT_FAMILY, 8), bg="white",
                     fg="#7A8194", width=3).grid(row=0, column=i)

        year, month = self.view_month.year, self.view_month.month
        self.label.config(text=self._month_name(month, year))

        cal = calendar.Calendar(firstweekday=0)
        for r, week in enumerate(cal.monthdayscalendar(year, month), start=1):
            for c, day in enumerate(week):
                if day == 0:
                    continue
                d = date(year, month, day)
                is_sel = d == self.initial
                btn = tk.Label(
                    self.grid_frame, text=str(day), font=(FONT_FAMILY, 9),
                    bg="#4285F4" if is_sel else "white",
                    fg="white" if is_sel else "#1F2430",
                    width=3, height=1, cursor="hand2"
                )
                btn.grid(row=r, column=c, pady=1)
                btn.bind("<Button-1>", lambda e, dd=d: self._pick(dd))

    def _pick(self, d):
        self.on_pick(d)
        self.destroy()

    def _prev(self):
        y, m = self.view_month.year, self.view_month.month
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        self.view_month = date(y, m, 1)
        self._render()

    def _next(self):
        y, m = self.view_month.year, self.view_month.month
        m += 1
        if m == 13:
            m, y = 1, y + 1
        self.view_month = date(y, m, 1)
        self._render()

    @staticmethod
    def _month_name(month, year):
        names = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
                  "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"]
        return f"{names[month - 1]} {year}"
