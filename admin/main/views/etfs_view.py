import threading
from tkinter import ttk
import customtkinter as ctk
from admin.main.views.etf_reg.etf_registry_service import ETFRegistryService


class ETFsView(ctk.CTkFrame):
    _cached_records = None

    def __init__(self, master, admin_db):
        super().__init__(master, fg_color="transparent")
        self.admin_db = admin_db
        self.is_online = True
        self.is_syncing = False

        # 1. Pehle UI banega, fir data load hoga
        self._build_ui()
        self.refresh_data(force_db_fetch=False)

    def _setup_treeview_styles(self):
        """CustomTkinter Dark Theme ke sath match karne ke liye TTK Style"""
        style = ttk.Style()
        style.theme_use("clam")

        # Table rows styling
        style.configure(
            "Custom.Treeview",
            background="#111827",
            foreground="#f3f4f6",
            fieldbackground="#111827",
            rowheight=34,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", "#1e3a8a")],
            foreground=[("selected", "#ffffff")]
        )

        # Header columns styling
        style.configure(
            "Custom.Treeview.Heading",
            background="#1e293b",
            foreground="#94a3b8",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=6
        )
        style.map(
            "Custom.Treeview.Heading",
            background=[("active", "#334155")]
        )

    def _build_ui(self):
        self._setup_treeview_styles()

        # 1. Action Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))

        self.lbl_title = ctk.CTkLabel(
            toolbar, text="🪙 Active ETFs Registry", 
            font=("Segoe UI", 16, "bold"), text_color="#f8fafc"
        )
        self.lbl_title.pack(side="left")

        # Right side Action Buttons
        self.btn_refresh = ctk.CTkButton(
            toolbar, text="🔄 Refresh", width=90, height=32,
            fg_color="#334155", hover_color="#475569", 
            command=lambda: self.refresh_data(force_db_fetch=True)
        )
        self.btn_refresh.pack(side="right", padx=(6, 0))

        self.btn_sync_etf = ctk.CTkButton(
            toolbar, text="⚡ Sync ETFs", width=110, height=32,
            fg_color="#0284c7", hover_color="#0369a1", command=self.start_etf_sync
        )
        self.btn_sync_etf.pack(side="right")

        # 2. Main Table Container
        self.table_container = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        self.table_container.pack(fill="both", expand=True)

        # 🌟 Fast ttk.Treeview Table Setup
        columns = ("sno", "symbol", "table", "type", "status")
        self.tree = ttk.Treeview(
            self.table_container, 
            columns=columns, 
            show="headings", 
            style="Custom.Treeview",
            selectmode="browse"
        )

        # Columns Configuration
        self.tree.heading("sno", text="S.No.", anchor="w")
        self.tree.heading("symbol", text="ETFs Stock", anchor="w")
        self.tree.heading("table", text="PostgreSQL Table Name", anchor="w")
        self.tree.heading("type", text="Type", anchor="w")
        self.tree.heading("status", text="Status", anchor="w")

        self.tree.column("sno", width=60, anchor="w", stretch=False)
        self.tree.column("symbol", width=180, anchor="w")
        self.tree.column("table", width=260, anchor="w")
        self.tree.column("type", width=100, anchor="w", stretch=False)
        self.tree.column("status", width=120, anchor="w", stretch=False)

        # Native Smooth Scrollbar
        scrollbar = ttk.Scrollbar(self.table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack Treeview & Scrollbar
        scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=4)
        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)

        # Status Tag Color Config
        self.tree.tag_configure("ACTIVE", foreground="#22c55e")
        self.tree.tag_configure("SUSPENDED", foreground="#f59e0b")
        self.tree.tag_configure("DELISTED", foreground="#ef4444")

    # =========================================================================
    # Data Fetching & Rendering (Non-blocking Background Thread)
    # =========================================================================
    def refresh_data(self, force_db_fetch=False):
        """Cache check karega; agar fresh data chahiye toh background fetch karega"""
        if not hasattr(self, "tree") or not self.winfo_exists():
            return

        # Agar cache mein data pehle se hai aur force refresh nahi maanga
        cached = getattr(ETFsView, "_cached_records", None)
        if cached is not None and not force_db_fetch:
            self._render_tree_data(cached)
            return

        # UI feedback
        self.lbl_title.configure(text="🪙 Active ETFs Registry (Loading...)")
        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="disabled")

        # Background thread se fetch karein (Zero UI Freeze)
        threading.Thread(target=self._fetch_records_worker, daemon=True).start()

    def _fetch_records_worker(self):
        try:
            records = self.admin_db.get_etf_tables_list()
            ETFsView._cached_records = records if records else []
            if self.winfo_exists():
                self.after(0, self._render_tree_data, ETFsView._cached_records)
        except Exception as e:
            if self.winfo_exists():
                self.after(0, self._on_fetch_error, str(e))

    def _render_tree_data(self, records):
        """Treeview ke andar rows render karta hai"""
        if not self.winfo_exists() or not hasattr(self, "tree"):
            return

        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal" if self.is_online and not self.is_syncing else "disabled")

        # Purana data clear karein
        for item in self.tree.get_children():
            self.tree.delete(item)

        records = records if records else []
        self.lbl_title.configure(text=f"🪙 Active ETFs Registry ({len(records)} ETF)")

        # Fast Batch Insertion into Treeview
        for idx, item in enumerate(records, start=1):
            symbol = item[1]
            tbl_name = item[2]
            status = item[3].upper() if len(item) > 3 and item[3] else "ACTIVE"

            self.tree.insert(
                "", 
                "end", 
                values=(str(idx), symbol, tbl_name, "ETF", status),
                tags=(status,)
            )

    def _on_fetch_error(self, err_msg):
        if not self.winfo_exists():
            return
        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal")
        self.lbl_title.configure(text="🪙 Active ETFs Registry (Error)")
        print(f"❌ DB Error: {err_msg}")

    # =========================================================================
    # Background Sync Trigger
    # =========================================================================
    def start_etf_sync(self):
        if self.is_syncing or not self.is_online:
            return

        self.is_syncing = True
        self.btn_sync_etf.configure(state="disabled", text="⏳ Syncing...")
        self.btn_refresh.configure(state="disabled")

        threading.Thread(target=self._run_etf_sync_worker, daemon=True).start()

    def _run_etf_sync_worker(self):
        try:
            db_core = self.admin_db if hasattr(self.admin_db, "conn") else getattr(self.admin_db, "db", self.admin_db)
            service = ETFRegistryService(db_core=db_core)
            service.sync_etf_registry_and_tables()
        except Exception as e:
            print(f"❌ [ETFsView] Sync worker error: {e}")

        if self.winfo_exists():
            self.after(0, self._on_sync_complete)

    def _on_sync_complete(self):
        if not self.winfo_exists():
            return
        self.is_syncing = False
        self.btn_sync_etf.configure(state="normal" if self.is_online else "disabled", text="⚡ Sync ETFs")
        self.btn_refresh.configure(state="normal" if self.is_online else "disabled")
        # Sync pura hone par DB se fresh data fetch karein
        self.refresh_data(force_db_fetch=True)

    def set_connection_state(self, is_online: bool):
        self.is_online = is_online
        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal" if is_online and not self.is_syncing else "disabled")
        if hasattr(self, "btn_sync_etf") and self.btn_sync_etf.winfo_exists():
            self.btn_sync_etf.configure(state="normal" if is_online and not self.is_syncing else "disabled")
