import customtkinter as ctk
from admin.header.profile_widget import ProfileDropdownWidget
from admin.header.sync_balance_widget import SyncBalanceWidget
from admin.header.metrics_widget import HeaderMetricsWidget

class AdminHeader(ctk.CTkFrame):
    def __init__(self, master, admin_db, user_info, on_logout, on_sync_callback=None, on_navigate_tab=None):
        super().__init__(master, fg_color="transparent")
        # Direct DBCore ki jagah AdminDB use hoga
        self.admin_db = admin_db
        self.user_info = user_info
        self.on_logout = on_logout
        self.on_sync_callback = on_sync_callback
        self.on_navigate_tab = on_navigate_tab

        self._build_header()

    def update_connection_ui(self, is_online, msg=""):
        """Connection status ke mutabiq badge aur sync button toggle karta hai"""
        if is_online:
            self.status_badge.configure(text="🟢 Online", text_color="#22c55e")
            if hasattr(self, "sync_balance_widget"):
                self.sync_balance_widget.btn_sync.configure(state="normal")
            if hasattr(self, "metrics_widget"):
                self.metrics_widget.set_enabled(True)
        else:
            short_msg = "🔴 No Internet" if "Internet" in msg else "🔴 Disconnected"
            self.status_badge.configure(text=short_msg, text_color="#ef4444")
            
            # Sync button disable karein
            if hasattr(self, "sync_balance_widget"):
                self.sync_balance_widget.btn_sync.configure(state="disabled")
            
            # Metric cards navigation disable karein
            if hasattr(self, "metrics_widget"):
                self.metrics_widget.set_enabled(False)

    def _build_header(self):
        # --- ROW 1 CONTAINER ---
        row1_frame = ctk.CTkFrame(self, height=65, fg_color="#1e293b", corner_radius=0)
        row1_frame.pack(fill="x", side="top")
        row1_frame.pack_propagate(False)

        # 1. Left: Branding Logo
        lbl_logo = ctk.CTkLabel(
            row1_frame, 
            text="📈 TRADING LEDGER", 
            font=("Segoe UI", 16, "bold"), 
            text_color="#38bdf8"
        )
        lbl_logo.pack(side="left", padx=20, pady=14)

        self.status_badge = ctk.CTkLabel(
            row1_frame,
            text="🟢 Online",
            font=("Segoe UI", 11, "bold"),
            text_color="#22c55e",
            fg_color="#0f172a",
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.status_badge.pack(side="left", padx=10, pady=14)
        
        # 2. Right: Profile Dropdown Menu
        self.profile_widget = ProfileDropdownWidget(row1_frame, self.user_info, self.on_logout)
        self.profile_widget.pack(side="right", padx=(10, 20), pady=14)

        # 3. Center-Right: Sync & Balance Widget
        self.sync_balance_widget = SyncBalanceWidget(
            row1_frame, 
            self.admin_db.db,  # DBCore instance pass karein sync service ke liye
            on_sync_complete_callback=self._handle_sync_complete
        )
        self.sync_balance_widget.pack(side="right", padx=15, pady=14)

        # --- ROW 2 CONTAINER: METRICS BUTTONS ---
        self.metrics_widget = HeaderMetricsWidget(
            self, 
            on_navigate=self.on_navigate_tab
        )
        self.metrics_widget.pack(fill="x", padx=20, pady=(15, 10))

    def _handle_sync_complete(self, sync_time):
        self.refresh_header_data(last_sync=sync_time)
        if self.on_sync_callback:
            self.on_sync_callback()

    def refresh_header_data(self, last_sync=None):
        """AdminDB se clean data lekar UI update karta hai (Zero Raw SQL)"""
        data = self.admin_db.get_header_metrics()

        self.metrics_widget.update_metrics(
            active_users=data["active_users"],
            total_users=data["total_users"],
            stocks_count=data["stocks_count"],
            etfs_count=data["etfs_count"],
            last_sync=last_sync
        )
        self.sync_balance_widget.set_balance(data["liquid_balance"])
