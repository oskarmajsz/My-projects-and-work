"""
Planer 3.0 - poprawiona wersja: stabilny kalendarz, działająca wyszukiwarka z listą,
zaokrąglone belki planów (Canvas), własny date/color picker, plakietki ważności.
Wymaga tylko standardowej biblioteki Pythona (tkinter + sqlite3).
Uruchom: python planer.py
"""

import tkinter as tk
from tkinter import messagebox
import calendar
from datetime import date, timedelta

from database import Database, COLOR_PALETTE
from widgets import (
    draw_rounded_rect, PriorityBadge, ColorPickerPanel, DatePickerEntry, FONT_FAMILY
)

# ---------- Styl / kolory ----------
BG_APP = "#F4F6FA"
BG_CARD = "#FFFFFF"
BORDER = "#E3E7EE"
TEXT_DARK = "#1F2430"
TEXT_MUTED = "#7A8194"
ACCENT = "#4285F4"
ACCENT_SOFT = "#E8F0FE"
TODAY_RING = "#4285F4"
WEEKEND_BG = "#F8F9FC"
OTHER_MONTH_TEXT = "#C3C8D4"
DONE_MUTE = "#AEB4C2"

FONT_DAY_NUM = (FONT_FAMILY, 11)
FONT_HEADER = (FONT_FAMILY, 18, "bold")
FONT_SECTION = (FONT_FAMILY, 13, "bold")
FONT_MAIN = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_BAR = (FONT_FAMILY, 9, "bold")

COLS = 7
WEEKS_SHOWN = 6
DAY_NUM_HEIGHT = 26     # pikseli zarezerwowanych na numer dnia, ZANIM zaczynają się belki
BAR_HEIGHT = 22
BAR_GAP = 4
MAX_BARS_VISIBLE = 3
# Stała, przewidywalna wysokość każdego wiersza tygodnia - to jest klucz do tego,
# żeby kalendarz NIE rozjeżdżał się niezależnie od liczby/długości planów.
ROW_HEIGHT = DAY_NUM_HEIGHT + MAX_BARS_VISIBLE * (BAR_HEIGHT + BAR_GAP) + 18


def daterange(d1: date, d2: date):
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)


# ============================================================================
#  OKNO DODAWANIA / EDYCJI PLANU
# ============================================================================

class PlanDialog(tk.Toplevel):
    def __init__(self, master, db: Database, on_saved, default_date: date, existing=None):
        super().__init__(master)
        self.db = db
        self.on_saved = on_saved
        self.existing = existing
        self.selected_color = existing[5] if existing else db.next_color()

        self.title("Edytuj plan" if existing else "Nowy plan")
        self.configure(bg=BG_CARD)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        outer = tk.Frame(self, bg=BG_CARD, padx=22, pady=20)
        outer.pack()

        tk.Label(outer, text="Tytuł planu", font=(FONT_FAMILY, 9), bg=BG_CARD,
                 fg=TEXT_MUTED).grid(row=0, column=0, columnspan=2, sticky="w")
        self.title_entry = tk.Entry(outer, font=(FONT_FAMILY, 12), width=32, relief="flat",
                                     bg="#F1F3F8", fg=TEXT_DARK)
        self.title_entry.grid(row=1, column=0, columnspan=2, sticky="we", pady=(4, 16), ipady=6)

        tk.Label(outer, text="Od", font=(FONT_FAMILY, 9), bg=BG_CARD,
                 fg=TEXT_MUTED).grid(row=2, column=0, sticky="w")
        tk.Label(outer, text="Do", font=(FONT_FAMILY, 9), bg=BG_CARD,
                 fg=TEXT_MUTED).grid(row=2, column=1, sticky="w", padx=(16, 0))

        start_d = date.fromisoformat(existing[2]) if existing else default_date
        end_d = date.fromisoformat(existing[3]) if existing else default_date

        self.start_picker = DatePickerEntry(outer, bg=BG_CARD, initial_date=start_d,
                                              on_change=self._on_start_change)
        self.start_picker.grid(row=3, column=0, sticky="w", pady=(4, 16))
        self.end_picker = DatePickerEntry(outer, bg=BG_CARD, initial_date=end_d)
        self.end_picker.grid(row=3, column=1, sticky="w", padx=(16, 0), pady=(4, 16))

        tk.Label(outer, text="Ważność", font=(FONT_FAMILY, 9), bg=BG_CARD,
                 fg=TEXT_MUTED).grid(row=4, column=0, columnspan=2, sticky="w")

        self.priority_var = tk.IntVar(value=existing[6] if existing else 0)
        prio_frame = tk.Frame(outer, bg=BG_CARD)
        prio_frame.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 16))

        for label, val in [("Normalna", 0), ("Ważne", 1), ("Bardzo ważne", 2)]:
            opt = tk.Frame(prio_frame, bg=BG_CARD, cursor="hand2")
            opt.pack(side="left", padx=(0, 14))
            if val > 0:
                badge = PriorityBadge(opt, priority=val, size=20, bg=BG_CARD)
                badge.pack(side="left", padx=(0, 4))
            rb = tk.Radiobutton(
                opt, text=label, variable=self.priority_var, value=val,
                font=(FONT_FAMILY, 9), bg=BG_CARD, fg=TEXT_DARK, selectcolor=BG_CARD,
                activebackground=BG_CARD, cursor="hand2"
            )
            rb.pack(side="left")

        tk.Label(outer, text="Kolor", font=(FONT_FAMILY, 9), bg=BG_CARD,
                 fg=TEXT_MUTED).grid(row=6, column=0, columnspan=2, sticky="w")

        self.color_picker = ColorPickerPanel(
            outer, bg=BG_CARD, initial_color=self.selected_color,
            on_change=self._on_color_change
        )
        self.color_picker.grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 18))

        btn_frame = tk.Frame(outer, bg=BG_CARD)
        btn_frame.grid(row=8, column=0, columnspan=2, sticky="we")

        if existing:
            tk.Button(
                btn_frame, text="Usuń plan", font=(FONT_FAMILY, 9), bg=BG_CARD, fg="#D33B27",
                relief="flat", bd=0, cursor="hand2", command=self._delete
            ).pack(side="left")

        tk.Button(
            btn_frame, text="Anuluj", font=(FONT_FAMILY, 10), bg=BG_CARD, fg=TEXT_MUTED,
            relief="flat", bd=0, cursor="hand2", command=self.destroy
        ).pack(side="right", padx=(0, 10))
        tk.Button(
            btn_frame, text="Zapisz plan", font=(FONT_FAMILY, 10, "bold"), bg=ACCENT, fg="white",
            relief="flat", bd=0, padx=18, pady=8, cursor="hand2", command=self._save
        ).pack(side="right")

        if existing:
            self.title_entry.insert(0, existing[1])

        self.title_entry.focus_set()

    def _on_start_change(self, d: date):
        # Jeśli koniec jest przed nowym początkiem, podciągamy koniec.
        if self.end_picker.get_date() < d:
            self.end_picker.set_date(d)

    def _on_color_change(self, color):
        self.selected_color = color

    def _save(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("Błąd", "Podaj tytuł planu.")
            return
        start_d = self.start_picker.get_date()
        end_d = self.end_picker.get_date()
        if end_d < start_d:
            messagebox.showerror("Błąd", "Data 'Do' nie może być wcześniejsza niż 'Od'.")
            return
        priority = self.priority_var.get()
        color = self.selected_color

        if self.existing:
            self.db.update_plan(self.existing[0], title, start_d.isoformat(),
                                 end_d.isoformat(), color, priority)
        else:
            self.db.add_plan(title, start_d.isoformat(), end_d.isoformat(), color, priority)

        self.on_saved()
        self.destroy()

    def _delete(self):
        if messagebox.askyesno("Usuń plan", "Na pewno usunąć ten plan?"):
            self.db.delete_plan(self.existing[0])
            self.on_saved()
            self.destroy()


# ============================================================================
#  WIDOK KALENDARZA (Canvas-based, stabilny layout)
# ============================================================================

class CalendarView(tk.Frame):
    """Kalendarz miesięczny rysowany na jednym Canvas - belki planów jako zaokrąglone
    prostokąty. Jeden canvas dla całej siatki eliminuje problem rozjeżdżania się
    wierszy, bo wysokość każdego wiersza jest ZAWSZE stała (ROW_HEIGHT) niezależnie
    od liczby/długości planów (nadmiar pokazujemy jako "+N więcej")."""

    def __init__(self, master, db: Database, on_day_selected, on_plan_click, on_add_plan):
        super().__init__(master, bg=BG_CARD)
        self.db = db
        self.on_day_selected = on_day_selected
        self.on_plan_click = on_plan_click
        self.on_add_plan = on_add_plan

        self.current_month = date.today().replace(day=1)
        self.selected_date = date.today()
        self._click_regions = []  # lista (x1,y1,x2,y2, callback) do hit-testu kliknięć

        self._build_header()
        self._build_weekday_row()

        self.canvas = tk.Canvas(self, bg=BG_CARD, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", lambda e: self.render())

        self.render()

    def _build_header(self):
        header = tk.Frame(self, bg=BG_CARD)
        header.pack(fill="x", padx=20, pady=(18, 8))

        nav = tk.Frame(header, bg=BG_CARD)
        nav.pack(side="left")
        tk.Button(nav, text="‹", font=(FONT_FAMILY, 14, "bold"), bg=BG_CARD, fg=TEXT_DARK,
                   bd=0, activebackground=ACCENT_SOFT, cursor="hand2", width=3,
                   command=self.prev_month).pack(side="left")
        self.month_label = tk.Label(nav, text="", font=FONT_HEADER, bg=BG_CARD, fg=TEXT_DARK)
        self.month_label.pack(side="left", padx=10)
        tk.Button(nav, text="›", font=(FONT_FAMILY, 14, "bold"), bg=BG_CARD, fg=TEXT_DARK,
                   bd=0, activebackground=ACCENT_SOFT, cursor="hand2", width=3,
                   command=self.next_month).pack(side="left")

        tk.Button(header, text="Dziś", font=FONT_MAIN, bg=ACCENT_SOFT, fg=ACCENT,
                   bd=0, padx=12, pady=4, cursor="hand2", activebackground=ACCENT_SOFT,
                   command=self.go_today).pack(side="left", padx=(16, 0))

        tk.Button(header, text="+ Nowy plan", font=(FONT_FAMILY, 10, "bold"), bg=ACCENT,
                   fg="white", bd=0, padx=14, pady=6, cursor="hand2", activebackground="#3367D6",
                   command=lambda: self.on_add_plan(self.selected_date)).pack(side="right")

    def _build_weekday_row(self):
        row = tk.Frame(self, bg=BG_CARD)
        row.pack(fill="x", padx=16)
        names = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
        for i, name in enumerate(names):
            row.grid_columnconfigure(i, weight=1, uniform="col")
            tk.Label(row, text=name, font=FONT_SMALL, bg=BG_CARD, fg=TEXT_MUTED).grid(
                row=0, column=i, pady=(2, 6), sticky="w", padx=(10, 0))

    def render(self):
        self.canvas.delete("all")
        self._click_regions = []

        width = self.canvas.winfo_width()
        if width < 50:
            self.after(50, self.render)
            return

        year, month = self.current_month.year, self.current_month.month
        self.month_label.config(text=self._month_name(month, year))

        cal = calendar.Calendar(firstweekday=0)
        month_days = list(cal.itermonthdates(year, month))
        weeks = [month_days[i:i + 7] for i in range(0, len(month_days), 7)]
        weeks = weeks[:WEEKS_SHOWN]

        plans = self.db.plans_in_month(year, month)
        today = date.today()
        col_w = width / COLS
        total_height = ROW_HEIGHT * len(weeks)
        self.canvas.config(height=total_height, scrollregion=(0, 0, width, total_height))

        for r, week in enumerate(weeks):
            week_start, week_end = week[0], week[-1]
            self._draw_week(r, week, today, month, col_w)
            self._draw_week_bars(r, week_start, week_end, plans, col_w)

    def _draw_week(self, r, week, today, current_month, col_w):
        y0 = r * ROW_HEIGHT
        for c, d in enumerate(week):
            x0 = c * col_w
            x1 = x0 + col_w
            y1 = y0 + ROW_HEIGHT
            in_month = d.month == current_month
            is_today = d == today
            is_selected = d == self.selected_date
            is_weekend = d.weekday() >= 5

            cell_bg = BG_CARD
            if is_weekend and in_month:
                cell_bg = WEEKEND_BG
            if is_selected:
                cell_bg = ACCENT_SOFT

            self.canvas.create_rectangle(x0, y0, x1, y1, fill=cell_bg, outline=BORDER, width=1)

            num_color = TEXT_DARK if in_month else OTHER_MONTH_TEXT
            if is_today:
                cx, cy = x1 - 18, y0 + 16
                self.canvas.create_oval(cx - 11, cy - 11, cx + 11, cy + 11, fill=TODAY_RING, outline="")
                self.canvas.create_text(cx, cy, text=str(d.day), fill="white",
                                         font=(FONT_FAMILY, 10, "bold"))
            else:
                self.canvas.create_text(x1 - 14, y0 + 16, text=str(d.day), fill=num_color,
                                         font=FONT_DAY_NUM, anchor="e")

            self._click_regions.append((x0, y0, x1, y1, lambda dd=d: self._select_day(dd)))

    def _draw_week_bars(self, r, week_start, week_end, plans, col_w):
        relevant = [p for p in plans
                    if date.fromisoformat(p[2]) <= week_end and date.fromisoformat(p[3]) >= week_start]
        relevant.sort(key=lambda p: (date.fromisoformat(p[2]), -p[6]))

        lanes_end = []
        plan_lane = {}
        for p in relevant:
            p_start = max(date.fromisoformat(p[2]), week_start)
            placed = False
            for lane_idx, lane_end in enumerate(lanes_end):
                if p_start > lane_end:
                    lanes_end[lane_idx] = min(date.fromisoformat(p[3]), week_end)
                    plan_lane[p[0]] = lane_idx
                    placed = True
                    break
            if not placed:
                lanes_end.append(min(date.fromisoformat(p[3]), week_end))
                plan_lane[p[0]] = len(lanes_end) - 1

        y_top = r * ROW_HEIGHT + DAY_NUM_HEIGHT
        overflow_counts = {}

        for p in relevant:
            plan_id, title, start_s, end_s, done, color, priority = p
            lane = plan_lane[plan_id]
            p_start = max(date.fromisoformat(start_s), week_start)
            p_end = min(date.fromisoformat(end_s), week_end)

            if lane >= MAX_BARS_VISIBLE:
                for d in daterange(p_start, p_end):
                    overflow_counts[d] = overflow_counts.get(d, 0) + 1
                continue

            col_start = (p_start - week_start).days
            col_span = (p_end - p_start).days + 1
            x0 = col_start * col_w + 4
            x1 = (col_start + col_span) * col_w - 4
            y0 = y_top + lane * (BAR_HEIGHT + BAR_GAP)
            y1 = y0 + BAR_HEIGHT

            bar_color = DONE_MUTE if done else color
            tag = f"plan{plan_id}_{r}_{lane}"
            draw_rounded_rect(self.canvas, x0, y0, x1, y1, radius=9,
                               fill=bar_color, outline="", tags=(tag,))

            label = title
            text_x = x0 + 10
            if priority > 0 and not done:
                badge_text = "!" if priority == 1 else "!!"
                badge_fill = "#FFD43B" if priority == 1 else "#FF6B6B"
                bx0, by0, bx1, by1 = x0 + 4, y0 + 3, x0 + 4 + (BAR_HEIGHT - 6), y1 - 3
                draw_rounded_rect(self.canvas, bx0, by0, bx1, by1, radius=4,
                                   fill=badge_fill, outline="#1A1A1A", width=1, tags=(tag,))
                self.canvas.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text=badge_text,
                                         font=(FONT_FAMILY, 7, "bold"), fill="#1A1A1A", tags=(tag,))
                text_x = bx1 + 6

            text_font = (FONT_FAMILY, 9, "overstrike") if done else FONT_BAR
            self.canvas.create_text(
                text_x, (y0 + y1) / 2, text=label, fill="white", font=text_font,
                anchor="w", tags=(tag,)
            )

            self.canvas.tag_bind(tag, "<Button-1>", lambda e, pid=plan_id: self.on_plan_click(pid))
            self.canvas.tag_bind(tag, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(tag, "<Leave>", lambda e: self.canvas.config(cursor=""))

        for d, count in overflow_counts.items():
            if not (week_start <= d <= week_end):
                continue
            col = (d - week_start).days
            x0 = col * col_w + 4
            y0 = y_top + MAX_BARS_VISIBLE * (BAR_HEIGHT + BAR_GAP)
            self.canvas.create_text(
                x0, y0 + BAR_HEIGHT / 2, text=f"+{count} więcej", fill=TEXT_MUTED,
                font=FONT_SMALL, anchor="w"
            )

    def _on_canvas_click(self, event):
        x, y = event.x, event.y
        for x0, y0, x1, y1, cb in reversed(self._click_regions):
            if x0 <= x <= x1 and y0 <= y <= y1:
                cb()
                return

    def _select_day(self, d: date):
        self.selected_date = d
        self.on_day_selected(d)
        self.render()

    def jump_to_date(self, d: date):
        self.current_month = d.replace(day=1)
        self.selected_date = d
        self.render()
        self.on_day_selected(d)

    def prev_month(self):
        y, m = self.current_month.year, self.current_month.month
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        self.current_month = date(y, m, 1)
        self.render()

    def next_month(self):
        y, m = self.current_month.year, self.current_month.month
        m += 1
        if m == 13:
            m, y = 1, y + 1
        self.current_month = date(y, m, 1)
        self.render()

    def go_today(self):
        self.jump_to_date(date.today())

    def refresh(self):
        self.render()

    @staticmethod
    def _month_name(month, year):
        names = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
                  "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"]
        return f"{names[month - 1]} {year}"


# ============================================================================
#  PANEL LISTY: wyszukiwarka + lista wszystkich planów (zawsze widoczna)
# ============================================================================

class ListPanel(tk.Frame):
    """Panel pod kalendarzem: wyszukiwarka z podpowiedziami na żywo + zawsze widoczna
    lista wszystkich planów, sortowalna od najnowszych/najstarszych. Klik na wpis
    otwiera dany dzień w kalendarzu i szczegóły planu - wpisywanie w polu NIE
    przeskakuje samo, tylko filtruje listę (zgodnie z życzeniem)."""

    SORT_NEWEST = "newest"
    SORT_OLDEST = "oldest"

    def __init__(self, master, db: Database, on_plan_click, on_jump_to_date):
        super().__init__(master, bg=BG_CARD)
        self.db = db
        self.on_plan_click = on_plan_click
        self.on_jump_to_date = on_jump_to_date
        self.sort_mode = self.SORT_NEWEST
        self.current_filter_date = None  # gdy klikamy dzień w kalendarzu, filtrujemy do niego

        self._build_top_bar()
        self.list_container = tk.Frame(self, bg=BG_CARD)
        self.list_container.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self.refresh()

    def _build_top_bar(self):
        bar = tk.Frame(self, bg=BG_CARD)
        bar.pack(fill="x", padx=20, pady=(16, 10))

        self.title_label = tk.Label(bar, text="Wszystkie plany", font=FONT_SECTION,
                                     bg=BG_CARD, fg=TEXT_DARK)
        self.title_label.pack(side="left")

        sort_frame = tk.Frame(bar, bg=BG_CARD)
        sort_frame.pack(side="right", padx=(10, 0))

        self.sort_btn_new = tk.Button(
            sort_frame, text="Najnowsze", font=FONT_SMALL, bg=ACCENT_SOFT, fg=ACCENT,
            bd=0, padx=10, pady=4, cursor="hand2", command=lambda: self._set_sort(self.SORT_NEWEST)
        )
        self.sort_btn_new.pack(side="left", padx=(0, 4))
        self.sort_btn_old = tk.Button(
            sort_frame, text="Najstarsze", font=FONT_SMALL, bg="#F1F3F8", fg=TEXT_MUTED,
            bd=0, padx=10, pady=4, cursor="hand2", command=lambda: self._set_sort(self.SORT_OLDEST)
        )
        self.sort_btn_old.pack(side="left")

        search_frame = tk.Frame(bar, bg="#F1F3F8")
        search_frame.pack(side="right", padx=(0, 16))

        self.search_entry = tk.Entry(
            search_frame, font=FONT_MAIN, width=24, relief="flat", bg="#F1F3F8",
            fg=TEXT_DARK, bd=0
        )
        self.search_entry.pack(side="left", padx=(10, 4), pady=6)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        tk.Label(search_frame, text="🔍", font=FONT_MAIN, bg="#F1F3F8").pack(side="left", padx=(0, 10))

    def _set_sort(self, mode):
        self.sort_mode = mode
        if mode == self.SORT_NEWEST:
            self.sort_btn_new.config(bg=ACCENT_SOFT, fg=ACCENT)
            self.sort_btn_old.config(bg="#F1F3F8", fg=TEXT_MUTED)
        else:
            self.sort_btn_old.config(bg=ACCENT_SOFT, fg=ACCENT)
            self.sort_btn_new.config(bg="#F1F3F8", fg=TEXT_MUTED)
        self.refresh()

    def filter_to_date(self, d: date):
        """Wywoływane przy kliknięciu dnia w kalendarzu - filtruje listę do tego dnia."""
        self.current_filter_date = d
        self.search_entry.delete(0, tk.END)
        self.refresh()

    def clear_date_filter(self):
        self.current_filter_date = None
        self.refresh()

    def refresh(self):
        query = self.search_entry.get().strip()

        if query:
            self.current_filter_date = None
            results = list(self.db.search(query))
            self.title_label.config(text=f"Wyniki wyszukiwania: „{query}” ({len(results)})")
        elif self.current_filter_date:
            results = list(self.db.plans_for_day(self.current_filter_date.isoformat()))
            self.title_label.config(text=f"Plany na {self._format_date(self.current_filter_date)}")
        else:
            results = list(self.db.search(""))
            self.title_label.config(text=f"Wszystkie plany ({len(results)})")

        results.sort(key=lambda p: p[0], reverse=(self.sort_mode == self.SORT_NEWEST))

        for w in self.list_container.winfo_children():
            w.destroy()

        if self.current_filter_date and not query:
            back_btn = tk.Button(
                self.list_container, text="← Pokaż wszystkie plany", font=FONT_SMALL,
                bg=BG_CARD, fg=ACCENT, bd=0, cursor="hand2", command=self.clear_date_filter
            )
            back_btn.pack(anchor="w", pady=(0, 8))

        if not results:
            tk.Label(
                self.list_container, text="Nic nie znaleziono. Kliknij „+ Nowy plan”, by dodać.",
                font=FONT_MAIN, bg=BG_CARD, fg=TEXT_MUTED
            ).pack(anchor="w", pady=12)
            return

        for p in results:
            self._build_row(p)

    def _build_row(self, p):
        plan_id, title, start_s, end_s, done, color, priority = p

        row = tk.Frame(self.list_container, bg=BG_CARD, cursor="hand2")
        row.pack(fill="x", pady=3)

        stripe = tk.Canvas(row, width=6, height=30, highlightthickness=0, bg=BG_CARD)
        stripe.pack(side="left", padx=(0, 8))
        draw_rounded_rect(stripe, 0, 0, 6, 30, radius=3, fill=color, outline="")

        var = tk.BooleanVar(value=bool(done))
        cb = tk.Checkbutton(
            row, variable=var, bg=BG_CARD, activebackground=BG_CARD, selectcolor=BG_CARD,
            bd=0, command=lambda: self._toggle_done(plan_id, var.get())
        )
        cb.pack(side="left", padx=(0, 4))

        if priority > 0 and not done:
            badge = PriorityBadge(row, priority=priority, size=20, bg=BG_CARD)
            badge.pack(side="left", padx=(0, 6))

        fg = DONE_MUTE if done else TEXT_DARK
        font = (FONT_FAMILY, 10, "overstrike" if done else "normal")
        date_str = self._short_range(start_s, end_s)
        lbl = tk.Label(row, text=f"{title}   •  {date_str}", font=font, bg=BG_CARD,
                       fg=fg, anchor="w")
        lbl.pack(side="left", fill="x", expand=True, pady=6)

        for widget in (row, lbl):
            widget.bind("<Button-1>", lambda e: self.on_plan_click(plan_id))

        jump_btn = tk.Button(
            row, text="W kalendarzu →", font=FONT_SMALL, bg=BG_CARD, fg=ACCENT,
            bd=0, cursor="hand2", activebackground=BG_CARD,
            command=lambda: self.on_jump_to_date(date.fromisoformat(start_s))
        )
        jump_btn.pack(side="right", padx=4)

    def _toggle_done(self, plan_id, done):
        self.db.set_done(plan_id, done)
        self.refresh()

    @staticmethod
    def _short_range(start_s, end_s):
        sd, ed = date.fromisoformat(start_s), date.fromisoformat(end_s)
        if sd == ed:
            return f"{sd.day:02d}.{sd.month:02d}.{sd.year}"
        return f"{sd.day:02d}.{sd.month:02d}.{sd.year} – {ed.day:02d}.{ed.month:02d}.{ed.year}"

    @staticmethod
    def _format_date(d: date):
        dni = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
        miesiace = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
                    "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]
        return f"{dni[d.weekday()].capitalize()}, {d.day} {miesiace[d.month - 1]} {d.year}"


# ============================================================================
#  GŁÓWNE OKNO
# ============================================================================

class PlanerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Planer")
        self.geometry("1180x920")
        self.minsize(940, 760)
        self.configure(bg=BG_APP)

        self.db = Database()

        outer = tk.Frame(self, bg=BG_APP)
        outer.pack(fill="both", expand=True, padx=18, pady=18)

        cal_card = tk.Frame(outer, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        cal_card.pack(fill="both", expand=True, pady=(0, 14))

        self.calendar_view = CalendarView(
            cal_card, self.db,
            on_day_selected=self._on_day_selected,
            on_plan_click=self._open_edit_plan,
            on_add_plan=self._open_new_plan,
        )
        self.calendar_view.pack(fill="both", expand=True)

        panel_card = tk.Frame(outer, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        panel_card.pack(fill="x")

        self.list_panel = ListPanel(
            panel_card, self.db,
            on_plan_click=self._open_edit_plan,
            on_jump_to_date=self._jump_to_date,
        )
        self.list_panel.pack(fill="both", expand=True)

    def _on_day_selected(self, d: date):
        self.list_panel.filter_to_date(d)

    def _jump_to_date(self, d: date):
        self.calendar_view.jump_to_date(d)

    def _open_new_plan(self, default_date: date):
        PlanDialog(self, self.db, on_saved=self._refresh_all, default_date=default_date)

    def _open_edit_plan(self, plan_id: int):
        existing = self.db.get_plan(plan_id)
        if not existing:
            return
        PlanDialog(self, self.db, on_saved=self._refresh_all,
                   default_date=date.today(), existing=existing)

    def _refresh_all(self):
        self.calendar_view.refresh()
        self.list_panel.refresh()


if __name__ == "__main__":
    app = PlanerApp()
    app.mainloop()
