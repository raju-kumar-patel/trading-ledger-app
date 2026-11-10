import threading
from tkinter import ttk
import customtkinter as ctk


class StocksView(ctk.CTkFrame):
    _cached_records = None

    def __init__(self, master, admin_db):
        super().__init__(master, fg_color="transparent")
        self.admin_db = admin_db
        self.is_online = True

        self._build_ui()
        self.refresh_data(force_db_fetch=False)

    def _setup_treeview_styles(self):
        """CustomTkinter Dark Theme ke sath match karne ke liye TTK Style"""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Stocks.Treeview",
            background="#111827",
            foreground="#f3f4f6",
            fieldbackground="#111827",
            rowheight=34,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        style.map(
            "Stocks.Treeview",
            background=[("selected", "#1e3a8a")],
            foreground=[("selected", "#ffffff")]
        )

        style.configure(
            "Stocks.Treeview.Heading",
            background="#1e293b",
            foreground="#94a3b8",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=6
        )
        style.map(
            "Stocks.Treeview.Heading",
            background=[("active", "#334155")]
        )

    def _build_ui(self):
        self._setup_treeview_styles()

        # 1. Action Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))

        self.lbl_title = ctk.CTkLabel(
            toolbar, text="📊 Active Stocks Registry (Equity Shares)", 
            font=("Segoe UI", 16, "bold"), text_color="#f8fafc"
        )
        self.lbl_title.pack(side="left")

        self.btn_refresh = ctk.CTkButton(
            toolbar, text="🔄 Refresh", width=90, height=32,
            fg_color="#334155", hover_color="#475569", 
            command=lambda: self.refresh_data(force_db_fetch=True)
        )
        self.btn_refresh.pack(side="right")

        # 2. Main Container
        self.table_container = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        self.table_container.pack(fill="both", expand=True)

        # 🌟 Native Fast Treeview
        columns = ("sno", "symbol", "table", "type", "status")
        self.tree = ttk.Treeview(
            self.table_container, 
            columns=columns, 
            show="headings", 
            style="Stocks.Treeview",
            selectmode="browse"
        )

        self.tree.heading("sno", text="S.No.", anchor="w")
        self.tree.heading("symbol", text="Equity Stock", anchor="w")
        self.tree.heading("table", text="PostgreSQL Table Name", anchor="w")
        self.tree.heading("type", text="Type", anchor="w")
        self.tree.heading("status", text="Status", anchor="w")

        self.tree.column("sno", width=60, anchor="w", stretch=False)
        self.tree.column("symbol", width=180, anchor="w")
        self.tree.column("table", width=260, anchor="w")
        self.tree.column("type", width=130, anchor="w", stretch=False)
        self.tree.column("status", width=120, anchor="w", stretch=False)

        scrollbar = ttk.Scrollbar(self.table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=4)
        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)

        self.tree.tag_configure("ACTIVE", foreground="#22c55e")
        self.tree.tag_configure("SUSPENDED", foreground="#f59e0b")
        self.tree.tag_configure("DELISTED", foreground="#ef4444")

    # =========================================================================
    # Non-blocking Background Fetch & Render
    # =========================================================================
    def refresh_data(self, force_db_fetch=False):
        if not hasattr(self, "tree") or not self.winfo_exists():
            return

        # Cache check (Instant Render)
        cached = getattr(StocksView, "_cached_records", None)
        if cached is not None and not force_db_fetch:
            self._render_tree_data(cached)
            return

        self.lbl_title.configure(text="📊 Active Stocks Registry (Loading...)")
        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="disabled")

        threading.Thread(target=self._fetch_records_worker, daemon=True).start()

    def _fetch_records_worker(self):
        try:
            records = self.admin_db.get_stock_tables_list()
            StocksView._cached_records = records if records else []
            if self.winfo_exists():
                self.after(0, self._render_tree_data, StocksView._cached_records)
        except Exception as e:
            if self.winfo_exists():
                self.after(0, self._on_fetch_error, str(e))

    def _render_tree_data(self, records):
        if not self.winfo_exists() or not hasattr(self, "tree"):
            return

        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal" if self.is_online else "disabled")

        for item in self.tree.get_children():
            self.tree.delete(item)

        records = records if records else []
        self.lbl_title.configure(text=f"📊 Active Stocks Registry ({len(records)} Equity Shares)")

        for idx, item in enumerate(records, start=1):
            symbol = item[1]
            tbl_name = item[2]
            status = item[3].upper() if len(item) > 3 and item[3] else "ACTIVE"

            self.tree.insert(
                "", 
                "end", 
                values=(str(idx), symbol, tbl_name, "Equity Share", status),
                tags=(status,)
            )

    def _on_fetch_error(self, err_msg):
        if not self.winfo_exists():
            return
        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal")
        self.lbl_title.configure(text="📊 Active Stocks Registry (Error)")
        print(f"❌ DB Error (Stocks): {err_msg}")

    def set_connection_state(self, is_online: bool):
        self.is_online = is_online
        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal" if is_online else "disabled")
