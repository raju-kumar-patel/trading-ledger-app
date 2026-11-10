import customtkinter as ctk
from tkinter import messagebox
from admin.main.views.user_management_view import UserManagementView
from admin.main.views.stocks_view import StocksView
from admin.main.views.etfs_view import ETFsView
from admin.main.views.system_view import SystemView

class AdminMain(ctk.CTkFrame):
    def __init__(self, master, admin_db, on_user_updated_callback=None):
        super().__init__(master, fg_color="transparent")
        # Direct DBCore ki jagah AdminDB layer use hogi
        self.admin_db = admin_db
        self.on_user_updated_callback = on_user_updated_callback
        self.selected_user = None

        # Content container jisme views switch honge
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True)
		
        self.views = {}
        self.current_tab = None
        
        # Saare dedicated views initialize karein
        self._init_views()
		
		# Default tab: Users
        self.switch_view("users")
		
    def _init_views(self):
        """Charo dedicated views ko instantiate karke dictionary mein rakhein"""
        self.views["users"] = UserManagementView(
            self.content_area, 
            admin_db=self.admin_db, 
            on_metrics_update=self.on_user_updated_callback
        )
        self.views["stocks"] = StocksView(self.content_area, admin_db=self.admin_db)
        self.views["etfs"] = ETFsView(self.content_area, admin_db=self.admin_db)
        self.views["system"] = SystemView(self.content_area, admin_db=self.admin_db)

    def switch_view(self, tab_key):
        """Header metrics cards par click aane par view switch karein"""
        if tab_key not in self.views:
            return

        # Purane view ko hide karein
        if self.current_tab and self.current_tab in self.views:
            self.views[self.current_tab].pack_forget()

        # Naye view ko show karein aur fresh data load karein
        self.current_tab = tab_key
        active_view = self.views[tab_key]
        active_view.pack(fill="both", expand=True)

        if hasattr(active_view, "refresh_data"):
            active_view.refresh_data()

    def set_connection_state(self, is_online: bool):
        """Network disconnect hone par sabhi views ke action buttons lock karein"""
        for view in self.views.values():
            if hasattr(view, "set_connection_state"):
                view.set_connection_state(is_online)

    def load_users(self):
        """Sync DB button ke liye callback"""
        if "users" in self.views and hasattr(self.views["users"], "refresh_data"):
            self.views["users"].refresh_data()
