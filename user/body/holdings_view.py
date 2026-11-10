import os
import sys
from datetime import datetime
import threading
import tkinter.ttk as ttk
import customtkinter as ctk
from theme.theme import Theme

# Root path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database.DBCore import DBCore
from user.user_db import UserDatabase

try:
    from user.body.user_portfolio_db import UserPortfolioDatabase
except ModuleNotFoundError:
    from user.user_portfolio_db import UserPortfolioDatabase

try:
    from user.body.logic.holdings_engine import HoldingsEngine
except ModuleNotFoundError:
    try:
        from user.logic.holdings_engine import HoldingsEngine
    except ModuleNotFoundError:
        from holdings_engine import HoldingsEngine


class HoldingsView(ctk.CTkFrame):
    def __init__(self, master, db_core=None, user_info=None, notify_callback=None, on_back=None, tree_style="UserBody.Treeview"):
        super().__init__(master, fg_color="transparent")
        self.db_core = db_core or DBCore
        self.user_info = user_info or {}
        self.notify = notify_callback
        self.on_back = on_back
        self.tree_style = tree_style
        self.db = UserDatabase(self.db_core)
        self.portfolio_db = UserPortfolioDatabase(self.db_core)

        self.cached_result = None
        self.is_fetching = False

        self._build_ui()
        # 🌟 Clean Startup: __init__ ke andar ab koi duplicate thread start nahi hoga!

    def set_user_info(self, user_info: dict):
        self.user_info = user_info or {}

    def _get_user_id(self):
        return self.user_info.get("id") or self.user_info.get("user_id")

    def _build_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent", height=38)
        top_bar.pack(fill="x", padx=4, pady=(2, 6))
        top_bar.pack_propagate(False)

        self.btn_back = ctk.CTkButton(
            top_bar,
            text="⬅",
            width=36,
            height=32,
            corner_radius=6,
            border_width=0,
            fg_color="transparent",
            hover_color="#1e293b",
            text_color="#38bdf8",
            font=("Segoe UI", 18, "bold"),
            command=self.on_back if self.on_back else lambda: None
        )
        self.btn_back.pack(side="left")

        self.btn_refresh = ctk.CTkButton(
            top_bar,
            text="🔄 Fetch NSE Live CMP",
            width=170,
            height=32,
            corner_radius=6,
            border_width=0,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#f8fafc",
            font=("Segoe UI", 11, "bold"),
            command=lambda: self.load_data(force_refresh=True)
        )
        self.btn_refresh.pack(side="right")

        summary_strip = ctk.CTkFrame(self, fg_color=Theme.BG_CARD, corner_radius=Theme.RADIUS_CARD, height=72, border_width=1, border_color=Theme.BORDER_SUBTLE)
        summary_strip.pack(fill="x", padx=2, pady=(0, 10))
        summary_strip.pack_propagate(False)

        metrics_center = ctk.CTkFrame(summary_strip, fg_color="transparent")
        metrics_center.pack(anchor="center", pady=10)

        # Invested
        m1 = ctk.CTkFrame(metrics_center, fg_color="transparent")
        m1.pack(side="left", padx=14)
        ctk.CTkLabel(m1, text="INVESTED", font=(Theme.FONT_FAMILY, 10, "bold"), text_color=Theme.TEXT_MUTED).pack()
        self.lbl_total_invested = ctk.CTkLabel(m1, text="₹ 0.00", font=(Theme.FONT_FAMILY, 15, "bold"), text_color=Theme.TEXT_PRIMARY)
        self.lbl_total_invested.pack()

        ctk.CTkFrame(metrics_center, width=1, height=30, fg_color=Theme.BORDER_SUBTLE).pack(side="left")

        # Current
        m2 = ctk.CTkFrame(metrics_center, fg_color="transparent")
        m2.pack(side="left", padx=14)
        ctk.CTkLabel(m2, text="CURRENT", font=(Theme.FONT_FAMILY, 10, "bold"), text_color=Theme.TEXT_MUTED).pack()
        self.lbl_total_mkt_val = ctk.CTkLabel(m2, text="₹ 0.00", font=(Theme.FONT_FAMILY, 15, "bold"), text_color=Theme.ACCENT_SKY)
        self.lbl_total_mkt_val.pack()

        ctk.CTkFrame(metrics_center, width=1, height=30, fg_color=Theme.BORDER_SUBTLE).pack(side="left")

        # P&L
        m3 = ctk.CTkFrame(metrics_center, fg_color="transparent")
        m3.pack(side="left", padx=14)
        ctk.CTkLabel(m3, text="P&L RETURN", font=(Theme.FONT_FAMILY, 10, "bold"), text_color=Theme.TEXT_MUTED).pack()
        self.lbl_total_gain_loss = ctk.CTkLabel(m3, text="₹ 0.00", font=(Theme.FONT_FAMILY, 15, "bold"), text_color=Theme.GREEN_BUY)
        self.lbl_total_gain_loss.pack()

        table_container = ctk.CTkFrame(self, fg_color="transparent")
        table_container.pack(fill="both", expand=True, padx=4, pady=0)

        cols = ("sno", "name", "quantity", "inv_per_share", "total_invested", "cmp", "market_value", "gain_loss")
        self.tree = ttk.Treeview(
            table_container,
            columns=cols,
            show="headings",
            style=self.tree_style,
            selectmode="browse"
        )

        headings = [
            ("sno", "S.No.", 50, "center"),
            ("name", "Shares / Symbol Name", 150, "w"),
            ("quantity", "Quantity", 80, "center"),
            ("inv_per_share", "Invested / Share (₹)", 130, "e"),
            ("total_invested", "Total Invested (₹)", 140, "e"),
            ("cmp", "Live CMP (₹)", 110, "e"),
            ("market_value", "Total CMP (₹)", 140, "e"),
            ("gain_loss", "Gain / Loss (₹ / %)", 165, "e")
        ]

        for col_id, title, width, align in headings:
            self.tree.heading(col_id, text=title, anchor=align)
            self.tree.column(col_id, width=width, anchor=align)

        self.tree.tag_configure("profit", foreground=Theme.GREEN_BUY)
        self.tree.tag_configure("loss", foreground=Theme.RED_SELL)
        self.tree.tag_configure("neutral", foreground=Theme.TEXT_MUTED)

        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

    def load_data(self, force_refresh: bool = False):
        uid = self._get_user_id()
        if not uid:
            return

        # 🌟 1. Shared Cache Check: Agar PortfolioCard ne pehle se data mangwaya hai,
        # toh bina network call kiye 0.01 second mein screen render karein!
        if not force_refresh:
            shared_res = UserPortfolioDatabase.get_cached_result(uid)
            if shared_res and shared_res.get("holdings"):
                self._render_ui(shared_res)
                return

        if self.is_fetching:
            return

        self.btn_refresh.configure(text="⏳ Fetching NSE...", state="disabled")
        self._trigger_fetch(force_refresh=force_refresh)

    def invalidate_cache(self):
        """Jab naya buy/sell transaction ho toh cache clear karein"""
        UserPortfolioDatabase.invalidate_cache()
        self.cached_result = None

    def _trigger_fetch(self, force_refresh: bool = False):
        uid = self._get_user_id()
        if not uid:
            return

        self.is_fetching = True

        def _worker():
            try:
                # Portfolio database ke zariye single synchronized fetch
                self.portfolio_db.get_portfolio_summary(uid, fetch_live_cmp=True, force_refresh=force_refresh)
                fresh_res = UserPortfolioDatabase.get_cached_result(uid)

                self.is_fetching = False
                if fresh_res:
                    self.after(0, lambda: self._on_fetch_success(fresh_res))
                else:
                    self.after(0, lambda: self.btn_refresh.configure(text="🔄 Fetch NSE Live CMP", state="normal"))
            except Exception as e:
                print(f"❌ [Holdings Fetch Error]: {e}")
                self.is_fetching = False
                self.after(0, lambda: self.btn_refresh.configure(text="🔄 Fetch NSE Live CMP", state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_fetch_success(self, result: dict):
        self.btn_refresh.configure(text="🔄 Fetch NSE Live CMP", state="normal")
        self._render_ui(result)
        if self.notify:
            now_time = datetime.now().strftime("%H:%M:%S")
            self.notify(f"[{now_time}] Live Holdings Updated ({len(result.get('holdings', []))} stocks).", "info")

    def _render_ui(self, result: dict):
        summary = result.get("summary", {})
        holdings = result.get("holdings", [])

        tot_inv = summary.get("total_invested", 0.0)
        tot_mkt = summary.get("total_market_val", 0.0)
        tot_pnl = summary.get("total_gain_loss", 0.0)
        tot_pct = summary.get("total_gain_loss_pct", 0.0)

        self.lbl_total_invested.configure(text=f"₹ {tot_inv:,.2f}")
        self.lbl_total_mkt_val.configure(text=f"₹ {tot_mkt:,.2f}")

        if tot_pnl > 0:
            self.lbl_total_gain_loss.configure(text=f"▲ +₹ {tot_pnl:,.2f} (+{tot_pct:.2f}%)", text_color="#22c55e")
        elif tot_pnl < 0:
            self.lbl_total_gain_loss.configure(text=f"▼ -₹ {abs(tot_pnl):,.2f} ({tot_pct:.2f}%)", text_color="#ef4444")
        else:
            self.lbl_total_gain_loss.configure(text="₹ 0.00 (0.00%)", text_color="#94a3b8")

        for item in self.tree.get_children():
            self.tree.delete(item)

        if not holdings:
            self.tree.insert("", "end", values=("—", "No Active Holdings Found", "0", "—", "—", "—", "—", "—"), tags=("neutral",))
            return

        for row in holdings:
            pnl_val = row["gain_loss"]
            pnl_pct = row["gain_loss_pct"]

            if pnl_val > 0:
                pnl_str = f"+₹ {pnl_val:,.2f} (+{pnl_pct:.2f}%)"
                tag = "profit"
            elif pnl_val < 0:
                pnl_str = f"-₹ {abs(pnl_val):,.2f} ({pnl_pct:.2f}%)"
                tag = "loss"
            else:
                pnl_str = "₹ 0.00 (0.00%)"
                tag = "neutral"

            values = (
                str(row["sno"]),
                str(row["name"]),
                str(row["quantity"]),
                f"₹ {row['inv_per_share']:,.2f}",
                f"₹ {row['total_invested']:,.2f}",
                f"₹ {row['cmp']:,.2f}",
                f"₹ {row['market_value']:,.2f}",
                pnl_str
            )
            self.tree.insert("", "end", values=values, tags=(tag,))
