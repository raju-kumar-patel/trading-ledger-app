import calendar
from datetime import date, datetime
import tkinter as tk
import customtkinter as ctk


class CTkCalendarOverlay(ctk.CTkFrame):
    """
    Fixed-Size Native CustomTkinter Calendar Overlay.
    - CustomTkinter place() ValueError permanently resolved.
    - Fixed 310x320 compact dimensions with strict propagation lock.
    - 7-Column uniform grid (Sunday aur sabhi dates perfectly visible).
    - Multi-view Month & Year selectors.
    """
    MONTHS_FULL = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    MONTHS_SHORT = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    def __init__(self, master_entry, on_date_selected=None):
        self.entry = master_entry
        self.callback = on_date_selected
        self.root = self.entry.winfo_toplevel()

        # Parse existing date
        cur_text = self.entry.get().strip()
        try:
            parsed = datetime.strptime(cur_text, "%Y-%m-%d").date()
        except Exception:
            parsed = date.today()

        self.view_year = parsed.year
        self.view_month = parsed.month
        self.selected_date = parsed

        self.mode = "DAYS"
        self.decade_start = (self.view_year // 12) * 12

        # Geometry calculation
        self.root.update_idletasks()
        self.entry.update_idletasks()

        win_w = self.root.winfo_width()
        win_h = self.root.winfo_height()

        # Compact & Proportional Dimensions
        cal_w = 310
        cal_h = 320

        rx = self.entry.winfo_rootx() - self.root.winfo_rootx()
        ry = self.entry.winfo_rooty() - self.root.winfo_rooty() + self.entry.winfo_height() + 4

        # Right-edge safe boundary check
        if rx + cal_w > win_w - 15:
            rx = win_w - cal_w - 15

        # Bottom-edge safe flip
        if ry + cal_h > win_h - 15:
            ry = (self.entry.winfo_rooty() - self.root.winfo_rooty()) - cal_h - 4

        # 🌟 width aur height sirf constructor mein pass honge:
        super().__init__(
            self.root,
            width=cal_w,
            height=cal_h,
            fg_color="#0f172a",
            corner_radius=10,
            border_width=1,
            border_color="#334155"
        )
        
        # Frame ko stretch hone se rokne ke liye strict propagation lock
        self.pack_propagate(False)
        self.grid_propagate(False)

        # 🌟 Fix: place() ke andar width aur height pass nahi karenge
        self.place(x=rx, y=ry)
        self.lift()

        # Header Frame
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=38)
        self.header.pack(fill="x", padx=8, pady=(6, 2))
        self.header.pack_propagate(False)

        # Body Frame
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=8, pady=2)

        # Footer Frame
        self._build_footer()

        # Initial Render
        self._render_view()

        # Bindings
        self._bind_esc = self.root.bind("<Escape>", lambda e: self.close())
        self._bind_click = self.root.bind("<Button-1>", self._check_outside_click, add="+")

    def _render_view(self):
        for w in self.header.winfo_children():
            w.destroy()
        for w in self.body.winfo_children():
            w.destroy()

        if self.mode == "DAYS":
            self._render_days_header()
            self._render_days_body()
        elif self.mode == "MONTHS":
            self._render_months_header()
            self._render_months_body()
        elif self.mode == "YEARS":
            self._render_years_header()
            self._render_years_body()

    # =========================================================================
    # VIEW 1: DAYS (7 COLUMNS)
    # =========================================================================
    def _render_days_header(self):
        ctk.CTkButton(
            self.header, text="<", width=28, height=26, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155", text_color="#38bdf8",
            font=("Segoe UI", 11, "bold"), command=self._prev_month
        ).pack(side="left")

        ctk.CTkButton(
            self.header, text=f"{self.MONTHS_FULL[self.view_month]} ▾",
            height=26, corner_radius=6, fg_color="transparent",
            hover_color="#1e293b", text_color="#f8fafc",
            font=("Segoe UI", 12, "bold"), command=self._switch_to_months
        ).pack(side="left", expand=True, padx=2)

        ctk.CTkButton(
            self.header, text=f"{self.view_year} ▾",
            height=26, corner_radius=6, fg_color="transparent",
            hover_color="#1e293b", text_color="#38bdf8",
            font=("Segoe UI", 12, "bold"), command=self._switch_to_years
        ).pack(side="left", expand=True, padx=2)

        ctk.CTkButton(
            self.header, text=">", width=28, height=26, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155", text_color="#38bdf8",
            font=("Segoe UI", 11, "bold"), command=self._next_month
        ).pack(side="right")

    def _render_days_body(self):
        for c in range(7):
            self.body.grid_columnconfigure(c, weight=1, uniform="day_col")

        weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for c, day in enumerate(weekdays):
            col_color = "#f87171" if day == "Su" else "#94a3b8"
            ctk.CTkLabel(
                self.body, text=day, font=("Segoe UI", 10, "bold"),
                text_color=col_color
            ).grid(row=0, column=c, pady=(1, 4), sticky="nsew")

        cal_matrix = calendar.monthcalendar(self.view_year, self.view_month)
        today = date.today()

        for r_idx, week in enumerate(cal_matrix, start=1):
            for c_idx, day in enumerate(week):
                if day != 0:
                    cur_date = date(self.view_year, self.view_month, day)
                    is_selected = (cur_date == self.selected_date)
                    is_today = (cur_date == today)
                    is_sunday = (c_idx == 6)

                    if is_selected:
                        fg, text_c, hover_c = "#0284c7", "#ffffff", "#0369a1"
                    elif is_today:
                        fg, text_c, hover_c = "#1e293b", "#38bdf8", "#334155"
                    else:
                        fg = "transparent"
                        text_c = "#f87171" if is_sunday else "#e2e8f0"
                        hover_c = "#1e293b"

                    ctk.CTkButton(
                        self.body,
                        text=str(day),
                        height=24,
                        corner_radius=5,
                        fg_color=fg,
                        hover_color=hover_c,
                        text_color=text_c,
                        font=("Segoe UI", 10, "bold" if (is_selected or is_today) else "normal"),
                        command=lambda d=cur_date: self._select_date(d)
                    ).grid(row=r_idx, column=c_idx, padx=1, pady=1, sticky="nsew")

    # =========================================================================
    # VIEW 2: MONTHS (4x3 GRID)
    # =========================================================================
    def _render_months_header(self):
        ctk.CTkButton(
            self.header, text="<", width=28, height=26, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155", text_color="#38bdf8",
            font=("Segoe UI", 11, "bold"), command=lambda: self._shift_year_in_month(-1)
        ).pack(side="left")

        ctk.CTkLabel(
            self.header, text=f"Select Month ({self.view_year})",
            font=("Segoe UI", 12, "bold"), text_color="#f8fafc"
        ).pack(side="left", expand=True)

        ctk.CTkButton(
            self.header, text=">", width=28, height=26, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155", text_color="#38bdf8",
            font=("Segoe UI", 11, "bold"), command=lambda: self._shift_year_in_month(1)
        ).pack(side="right")

    def _render_months_body(self):
        for c in range(3):
            self.body.grid_columnconfigure(c, weight=1, uniform="m_col")

        months_list = [
            (1, "Jan"), (2, "Feb"), (3, "Mar"),
            (4, "Apr"), (5, "May"), (6, "Jun"),
            (7, "Jul"), (8, "Aug"), (9, "Sep"),
            (10, "Oct"), (11, "Nov"), (12, "Dec")
        ]

        for idx, (m_num, m_name) in enumerate(months_list):
            r = idx // 3
            c = idx % 3
            is_cur = (m_num == self.view_month)
            fg = "#0284c7" if is_cur else "#1e293b"
            text_c = "#ffffff" if is_cur else "#e2e8f0"

            ctk.CTkButton(
                self.body,
                text=m_name,
                height=34,
                corner_radius=6,
                fg_color=fg,
                hover_color="#0369a1" if is_cur else "#334155",
                text_color=text_c,
                font=("Segoe UI", 11, "bold" if is_cur else "normal"),
                command=lambda m=m_num: self._pick_month(m)
            ).grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

    # =========================================================================
    # VIEW 3: YEARS (4x3 GRID)
    # =========================================================================
    def _render_years_header(self):
        end_decade = self.decade_start + 11
        ctk.CTkButton(
            self.header, text="<", width=28, height=26, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155", text_color="#38bdf8",
            font=("Segoe UI", 11, "bold"), command=lambda: self._shift_decade(-12)
        ).pack(side="left")

        ctk.CTkLabel(
            self.header, text=f"{self.decade_start} – {end_decade}",
            font=("Segoe UI", 12, "bold"), text_color="#f8fafc"
        ).pack(side="left", expand=True)

        ctk.CTkButton(
            self.header, text=">", width=28, height=26, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155", text_color="#38bdf8",
            font=("Segoe UI", 11, "bold"), command=lambda: self._shift_decade(12)
        ).pack(side="right")

    def _render_years_body(self):
        for c in range(3):
            self.body.grid_columnconfigure(c, weight=1, uniform="y_col")

        years = [self.decade_start + i for i in range(12)]
        for idx, y in enumerate(years):
            r = idx // 3
            c = idx % 3
            is_cur = (y == self.view_year)
            fg = "#0284c7" if is_cur else "#1e293b"
            text_c = "#ffffff" if is_cur else "#e2e8f0"

            ctk.CTkButton(
                self.body,
                text=str(y),
                height=34,
                corner_radius=6,
                fg_color=fg,
                hover_color="#0369a1" if is_cur else "#334155",
                text_color=text_c,
                font=("Segoe UI", 11, "bold" if is_cur else "normal"),
                command=lambda yr=y: self._pick_year(yr)
            ).grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

    # =========================================================================
    # FOOTER
    # =========================================================================
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent", height=30)
        footer.pack(fill="x", padx=8, pady=(2, 6))
        footer.pack_propagate(False)

        ctk.CTkButton(
            footer, text="Today", height=24, width=55, corner_radius=5,
            fg_color="#1e293b", hover_color="#334155", text_color="#38bdf8",
            font=("Segoe UI", 10, "bold"),
            command=lambda: self._select_date(date.today())
        ).pack(side="left")

        ctk.CTkButton(
            footer, text="Close", height=24, width=50, corner_radius=5,
            fg_color="transparent", hover_color="#ef4444", text_color="#94a3b8",
            font=("Segoe UI", 10),
            command=self.close
        ).pack(side="right")

    # =========================================================================
    # CONTROLS
    # =========================================================================
    def _switch_to_months(self):
        self.mode = "MONTHS"
        self._render_view()

    def _switch_to_years(self):
        self.mode = "YEARS"
        self.decade_start = (self.view_year // 12) * 12
        self._render_view()

    def _pick_month(self, m_idx: int):
        self.view_month = m_idx
        self.mode = "DAYS"
        self._render_view()

    def _pick_year(self, yr: int):
        self.view_year = yr
        self.mode = "DAYS"
        self._render_view()

    def _shift_year_in_month(self, delta: int):
        self.view_year += delta
        self._render_view()

    def _shift_decade(self, delta: int):
        self.decade_start += delta
        self._render_view()

    def _prev_month(self):
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self._render_view()

    def _next_month(self):
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else:
            self.view_month += 1
        self._render_view()

    def _select_date(self, selected: date):
        date_str = selected.strftime("%Y-%m-%d")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, date_str)
        if self.callback:
            self.callback(date_str)
        self.close()

    def _check_outside_click(self, event):
        if not self.winfo_exists():
            return
        w_name = str(event.widget)
        if w_name.startswith(str(self)) or event.widget == self.entry:
            return
        self.close()

    def close(self):
        try:
            self.root.unbind("<Button-1>", self._bind_click)
            self.root.unbind("<Escape>", self._bind_esc)
        except Exception:
            pass
        if hasattr(self.entry, "_calendar_overlay"):
            self.entry._calendar_overlay = None
        self.destroy()


def attach_calendar_picker(entry_widget, callback=None):
    def _toggle_picker(event=None):
        existing = getattr(entry_widget, "_calendar_overlay", None)
        if existing and existing.winfo_exists():
            existing.close()
            return "break"

        entry_widget._calendar_overlay = CTkCalendarOverlay(entry_widget, on_date_selected=callback)
        return "break"

    entry_widget.bind("<Button-1>", _toggle_picker)
    return entry_widget
