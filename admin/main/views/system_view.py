import platform
import threading
import customtkinter as ctk


class SystemView(ctk.CTkFrame):
    def __init__(self, master, admin_db):
        super().__init__(master, fg_color="transparent")
        self.admin_db = admin_db
        self.is_online = True

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Action Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 12))

        self.lbl_title = ctk.CTkLabel(
            toolbar, text="⚙️ System Diagnostics & Environment",
            font=("Segoe UI", 16, "bold"), text_color="#f8fafc"
        )
        self.lbl_title.pack(side="left")

        self.btn_refresh = ctk.CTkButton(
            toolbar, text="🔄 Refresh", width=90, height=32,
            fg_color="#334155", hover_color="#475569", command=self.refresh_data
        )
        self.btn_refresh.pack(side="right")

        # 2. Info Cards Container
        self.cards_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        self.cards_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.lbl_db_status = ctk.CTkLabel(
            self.cards_frame, text="Database Pool Status: Checking...",
            font=("Segoe UI", 13, "bold"), text_color="#94a3b8", anchor="w"
        )
        self.lbl_db_status.pack(fill="x", padx=20, pady=(20, 8))

        self.lbl_os_info = ctk.CTkLabel(
            self.cards_frame,
            text=f"Operating System: {platform.system()} {platform.release()} ({platform.machine()})",
            font=("Segoe UI", 12), text_color="#cbd5e1", anchor="w"
        )
        self.lbl_os_info.pack(fill="x", padx=20, pady=6)

        self.lbl_python_info = ctk.CTkLabel(
            self.cards_frame,
            text=f"Python Runtime: v{platform.python_version()}",
            font=("Segoe UI", 12), text_color="#cbd5e1", anchor="w"
        )
        self.lbl_python_info.pack(fill="x", padx=20, pady=6)

        self.lbl_registry_stats = ctk.CTkLabel(
            self.cards_frame,
            text="Registry Tables: Loading...",
            font=("Segoe UI", 12), text_color="#38bdf8", anchor="w"
        )
        self.lbl_registry_stats.pack(fill="x", padx=20, pady=6)

    def refresh_data(self, force_db_fetch=False):
        if not self.winfo_exists():
            return

        # Background thread mein DB pool status check karein
        threading.Thread(target=self._check_system_worker, daemon=True).start()

    def _check_system_worker(self):
        is_connected = False
        total_stocks = 0
        total_etfs = 0

        try:
            db_obj = getattr(self.admin_db, "db", None)
            # Pool based safe check (No .conn attribute error)
            if db_obj and hasattr(db_obj, "get_connection"):
                with db_obj.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                        cur.fetchone()
                        is_connected = True
            elif db_obj and getattr(db_obj, "_pool", None) is not None:
                is_connected = True

            if hasattr(self.admin_db, "get_stock_tables_list"):
                stocks = self.admin_db.get_stock_tables_list()
                total_stocks = len(stocks) if stocks else 0

            if hasattr(self.admin_db, "get_etf_tables_list"):
                etfs = self.admin_db.get_etf_tables_list()
                total_etfs = len(etfs) if etfs else 0

        except Exception as e:
            print(f"SystemView check error: {e}")
            is_connected = False

        if self.winfo_exists():
            self.after(0, self._update_ui, is_connected, total_stocks, total_etfs)

    def _update_ui(self, is_connected: bool, total_stocks: int, total_etfs: int):
        if not self.winfo_exists():
            return

        if is_connected:
            self.lbl_db_status.configure(
                text="🟢 Database Pool Status: Connected & Healthy",
                text_color="#22c55e"
            )
        else:
            self.lbl_db_status.configure(
                text="🔴 Database Pool Status: Disconnected",
                text_color="#ef4444"
            )

        self.lbl_registry_stats.configure(
            text=f"📊 Registered Instruments: {total_stocks} Equity Shares | {total_etfs} ETFs"
        )

    def set_connection_state(self, is_online: bool):
        self.is_online = is_online
        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal" if is_online else "disabled")
