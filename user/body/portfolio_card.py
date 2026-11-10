import threading
import customtkinter as ctk
from database.DBCore import DBCore
from theme.theme import Theme
try:
    from user.body.user_portfolio_db import UserPortfolioDatabase
except ModuleNotFoundError:
    from user.user_portfolio_db import UserPortfolioDatabase


class MetricSection(ctk.CTkFrame):
    def __init__(self, master, title: str, initial_value: str = "Rs. 0.00", value_color: str = "#f8fafc"):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(
            self, text=title,
            font=("Segoe UI", 12), text_color="#94a3b8", anchor="w"
        ).pack(anchor="w")

        self.lbl_value = ctk.CTkLabel(
            self, text=initial_value,
            font=("Segoe UI", 15, "bold"), text_color=value_color, anchor="w"
        )
        self.lbl_value.pack(anchor="w", pady=(2, 0))

    def set_value(self, text: str, color: str = None):
        if self.winfo_exists():
            self.lbl_value.configure(text=text)
            if color:
                self.lbl_value.configure(text_color=color)


class PortfolioCard(ctk.CTkFrame):
    def __init__(self, master, user_info=None, db_core=None, notify_callback=None):
        super().__init__(
            master,
            fg_color="#1e293b",
            corner_radius=18,
            border_width=1,
            border_color="#334155"
        )
        self.user_info = user_info or {}
        self.db_core = db_core or DBCore
        self.notify = notify_callback
        self.user_db = UserPortfolioDatabase(self.db_core)
        self.is_fetching = False

        self._build_card()

    def _build_card(self):
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=24, pady=(14, 10))

        ctk.CTkLabel(
            top_row, text="My Portfolio",
            font=("Segoe UI", 16, "bold"), text_color="#f8fafc"
        ).pack(side="left", anchor="n")

        right_box = ctk.CTkFrame(top_row, fg_color="transparent")
        right_box.pack(side="right")

        self.lbl_total_val = ctk.CTkLabel(
            right_box, text="Rs. 0.00",
            font=("Segoe UI", 16, "bold"), text_color="#f8fafc", anchor="e"
        )
        self.lbl_total_val.pack(anchor="e")

        self.lbl_pct_change = ctk.CTkLabel(
            right_box, text="— (0.00%)",
            font=("Segoe UI", 12, "bold"), text_color="#94a3b8", anchor="e"
        )
        self.lbl_pct_change.pack(anchor="e")

        divider = ctk.CTkFrame(self, height=2, fg_color="#334155")
        divider.pack(fill="x", padx=20, pady=2)

        bottom_row = ctk.CTkFrame(self, fg_color="transparent")
        bottom_row.pack(fill="x", padx=24, pady=(10, 14))

        bottom_row.grid_columnconfigure(0, weight=1)
        bottom_row.grid_columnconfigure(1, weight=1)
        bottom_row.grid_columnconfigure(2, weight=1)

        self.sec_invested = MetricSection(bottom_row, title="EQ Invested", initial_value="Rs. 0.00")
        self.sec_invested.grid(row=0, column=0, sticky="w")

        self.sec_market_val = MetricSection(bottom_row, title="Market Value", initial_value="Rs. 0.00", value_color="#38bdf8")
        self.sec_market_val.grid(row=0, column=1, sticky="n")

        self.sec_gain_loss = MetricSection(bottom_row, title="Gain/Loss", initial_value="Rs. 0.00", value_color="#94a3b8")
        self.sec_gain_loss.grid(row=0, column=2, sticky="e")

    def refresh_portfolio(self, force_refresh: bool = False):
        """Background thread par live portfolio calculate karta hai"""
        uid = self.user_info.get("id") or self.user_info.get("user_id")
        if not uid or self.is_fetching:
            return

        self.is_fetching = True
        threading.Thread(target=self._fetch_worker, args=(uid, force_refresh), daemon=True).start()

    def _fetch_worker(self, uid: str, force_refresh: bool):
        try:
            # 1. Offline Quick Update (Zero-delay investment display)
            local_summary = self.user_db.get_portfolio_summary(uid, fetch_live_cmp=False)
            if self.winfo_exists():
                self.after(
                    0,
                    self.update_portfolio,
                    local_summary["invested"],
                    local_summary["market_value"],
                    local_summary["gain_loss"],
                    local_summary["pct_change"]
                )

            # 2. Live Market Fetch (Sirf 1 baar NSE call hoga)
            live_summary = self.user_db.get_portfolio_summary(uid, fetch_live_cmp=True, force_refresh=force_refresh)
            if self.winfo_exists():
                self.after(
                    0,
                    self.update_portfolio,
                    live_summary["invested"],
                    live_summary["market_value"],
                    live_summary["gain_loss"],
                    live_summary["pct_change"]
                )
        except Exception as e:
            print(f"⚠️ [PortfolioCard Fetch Worker Error]: {e}")
        finally:
            self.is_fetching = False

    def update_portfolio(self, invested: float, market_val: float, gain_loss: float = None, pct_change: float = None):
        if gain_loss is None:
            gain_loss = market_val - invested
        if pct_change is None:
            pct_change = ((gain_loss / invested) * 100.0) if invested > 0 else 0.0

        is_positive = gain_loss >= 0
        gl_sign = "+" if is_positive else ""
        gl_color = "#22c55e" if is_positive else "#ef4444"
        arrow = "▲" if is_positive else "▼"

        if invested == 0 and market_val == 0:
            gl_color = "#94a3b8"
            arrow = "—"
            gl_sign = ""

        self.lbl_total_val.configure(text=f"Rs. {market_val:,.2f}")
        self.lbl_pct_change.configure(text=f"{arrow} ({gl_sign}{pct_change:.2f}%)", text_color=gl_color)

        self.sec_invested.set_value(f"Rs. {invested:,.2f}")
        self.sec_market_val.set_value(f"Rs. {market_val:,.2f}")
        self.sec_gain_loss.set_value(f"Rs. {gl_sign}{gain_loss:,.2f}", color=gl_color)
