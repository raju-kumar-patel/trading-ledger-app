import customtkinter as ctk
from database.DBCore import DBCore
from user.body.portfolio_card import PortfolioCard
from user.body.watchlist_view import WatchlistView
from user.body.holdings_view import HoldingsView
from user.body.analysis_view import AnalysisView
from user.body.ledger_view import LedgerView
from user.body.user_forms.add_entry_container import AddEntryContainer


class UserBody(ctk.CTkFrame):
    def __init__(self, master, db_core=None, notify_callback=None, user_info=None):
        super().__init__(master, fg_color="transparent")
        self.db = db_core or DBCore
        self.notify = notify_callback
        self.user_info = user_info or {}

        self._setup_treeview_styles()
        self._build_ui()

        # Default: Portfolio Home Dashboard display karein
        self.show_home_dashboard()

    def _setup_treeview_styles(self):
        import tkinter.ttk as ttk
        style = ttk.Style()
        if style.theme_use() != "clam":
            style.theme_use("clam")

        style.configure(
            "UserBody.Treeview",
            background="#111827",
            foreground="#f3f4f6",
            fieldbackground="#111827",
            rowheight=34,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        style.map(
            "UserBody.Treeview",
            background=[("selected", "#1e3a8a")],
            foreground=[("selected", "#ffffff")]
        )
        style.configure(
            "UserBody.Treeview.Heading",
            background="#1e293b",
            foreground="#94a3b8",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=6
        )

    def _build_ui(self):
        self.home_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.portfolio_card = PortfolioCard(
            self.home_frame,
            user_info=self.user_info,
            db_core=self.db,
            notify_callback=self.notify
        )
        self.portfolio_card.pack(fill="x", pady=(0, 20))

        nav_container = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        nav_container.pack(fill="x", pady=10)

        buttons_config = [
            ("WATCHLIST", "⭐ Watchlist", "#1e293b", "#334155"),
            ("HOLDINGS",  "💼 Holdings", "#1e293b", "#334155"),
            ("ANALYSIS",  "📊 Analysis", "#1e293b", "#334155"),
            ("LEDGER",    "📒 Ledger",   "#1e293b", "#334155"),
            ("ADD",       "➕ Add Entry", "#065f46", "#047857")
        ]

        for key, text, bg_col, hov_col in buttons_config:
            btn = ctk.CTkButton(
                nav_container,
                text=text,
                width=140,
                height=44,
                corner_radius=10,
                border_width=1,
                border_color="#475569",
                fg_color=bg_col,
                hover_color=hov_col,
                text_color="#f8fafc",
                font=("Segoe UI", 13, "bold"),
                command=lambda k=key: self.open_section_fullview(k)
            )
            btn.pack(side="left", padx=(0, 14))

        self.detail_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.top_back_bar = ctk.CTkFrame(self.detail_frame, fg_color="transparent", height=40)
        self.top_back_bar.pack(side="top", fill="x", pady=(0, 6))
        self.top_back_bar.pack_propagate(False)

        self.btn_back = ctk.CTkButton(
            self.top_back_bar,
            text="⬅",
            width=38,
            height=34,
            corner_radius=6,
            border_width=0,
            fg_color="transparent",
            hover_color="#1e293b",
            text_color="#38bdf8",
            font=("Segoe UI", 18, "bold"),
            command=self.show_home_dashboard
        )
        self.btn_back.pack(side="left", padx=(0, 10))

        self.lbl_section_title = ctk.CTkLabel(
            self.top_back_bar,
            text="Section View",
            font=("Segoe UI", 16, "bold"),
            text_color="#38bdf8"
        )
        self.lbl_section_title.pack(side="left")

        self.content_workspace = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        self.content_workspace.pack(side="top", fill="both", expand=True)

        self.watchlist_view = WatchlistView(
            self.content_workspace,
            db_core=self.db,
            user_info=self.user_info,
            notify_callback=self.notify
        )
        self.holdings_view = HoldingsView(
            self.content_workspace,
            db_core=self.db,
            user_info=self.user_info,
            notify_callback=self.notify,
            on_back=self.show_home_dashboard
        )
        self.analysis_view = AnalysisView(self.content_workspace, db_core=self.db, notify_callback=self.notify)
        self.ledger_view = LedgerView(self.content_workspace, db_core=self.db, user_info=self.user_info, notify_callback=self.notify)
        
        self.add_container_view = AddEntryContainer(
            self.content_workspace,
            user_info=self.user_info,
            notify_callback=self.notify,
            on_back=self.show_home_dashboard
        )

        self.section_views = {
            "WATCHLIST": (self.watchlist_view, "⭐ My Watchlist"),
            "HOLDINGS":  (self.holdings_view, "💼 Portfolio Holdings"),
            "ANALYSIS":  (self.analysis_view, "📊 14-Day Wilder RSI Market Analysis"),
            "LEDGER":    (self.ledger_view, "📒 Account Financial Ledger"),
            "ADD":       (self.add_container_view, "➕ Add New Entry / Trade Form")
        }

    def on_transaction_completed(self):
        """Transaction complete hone par cache clear karein aur card refresh karein"""
        if hasattr(self, "holdings_view") and self.holdings_view:
            self.holdings_view.invalidate_cache()
        if hasattr(self, "portfolio_card") and self.portfolio_card:
            self.portfolio_card.refresh_portfolio(force_refresh=True)

    def show_home_dashboard(self):
        """Home Dashboard par aane par values refresh karein"""
        self.detail_frame.pack_forget()
        self.home_frame.pack(fill="both", expand=True, padx=4, pady=4)

        if hasattr(self, "portfolio_card") and self.portfolio_card:
            self.portfolio_card.refresh_portfolio()

        if self.notify:
            self.notify("Portfolio dashboard ready.", "info")

    def open_section_fullview(self, section_key: str):
        self.home_frame.pack_forget()
        self.detail_frame.pack(fill="both", expand=True, padx=4, pady=4)

        if section_key in ("ADD", "HOLDINGS"):
            self.top_back_bar.pack_forget()
        else:
            self.top_back_bar.pack(side="top", fill="x", pady=(0, 6), before=self.content_workspace)

        for view, _ in self.section_views.values():
            view.pack_forget()

        target_view, title_text = self.section_views.get(section_key, (None, ""))
        if target_view:
            if section_key not in ("ADD", "HOLDINGS"):
                self.lbl_section_title.configure(text=title_text)
            target_view.pack(fill="both", expand=True, padx=4, pady=4)

        if section_key == "ANALYSIS":
            self.analysis_view.load_data(force_refresh=False)
        elif section_key == "LEDGER":
            self.ledger_view.load_data()
        elif section_key == "HOLDINGS":
            self.holdings_view.load_data(force_refresh=False)

        if self.notify and section_key != "ADD":
            self.notify(f"{title_text} opened.", "info")
