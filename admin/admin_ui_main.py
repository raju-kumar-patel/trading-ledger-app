import customtkinter as ctk
import threading
import time
from services.connection_checker import ConnectionChecker
from admin.header.admin_header import AdminHeader
from admin.main.admin_main import AdminMain
from admin.admin_db.admin_db import AdminDB

class AdminApp(ctk.CTkFrame):
    def __init__(self, master, db_service, user_info, on_logout):
        super().__init__(master, fg_color="#0f172a")
        
        # 0. Pehle AdminDB aur user properties ko initialize karein
        self.db = db_service
        self.admin_db = AdminDB(db_core=db_service)
        self.user_info = user_info
        self.on_logout = on_logout
        
        # 🌟 Pehle checker ka instance create karein
        self.checker = ConnectionChecker(db_service=self.db)
        
        self._assemble_dashboard()
        
        # 🌟 Connection polling start karein
        self.is_monitoring = True
        self._start_connection_monitor()
        
    def _start_connection_monitor(self):
        def monitor():
			# Initial queries complete hone ke liye 10 sec wait karein
            time.sleep(10)
            while self.is_monitoring:
                try:
                    # (DB aur Internet dono check karta hai)
                    is_ok, msg = self.checker.check_all()  
                except Exception as e:
                    print(f"Connection monitor error: {e}")
                    is_ok = False
                    msg = str(e)

                # 🔍 CMD Console mein live heartbeat print hoga
                print(f"[Heartbeat] Status: {'🟢 Online' if is_ok else '🔴 Disconnected'} | Msg: {msg}")
                # Thread-safe UI update  --  and hasattr(self, "header") and self.header.winfo_exists()
                if self.is_monitoring:
                    self.after(0, lambda status=is_ok, text_msg=msg: self._apply_connection_state(status, text_msg))
                # Tkinter thread-safe tareeqe se UI update karein      
                time.sleep(15)  # Har 15 second baad check karega

        threading.Thread(target=monitor, daemon=True).start()

    def destroy(self):
        """Dashboard close / logout hone par loop safely stop karein"""
        self.is_monitoring = False
        super().destroy()

    def _apply_connection_state(self, is_online, msg=""):
        """Header aur Main Content dono ko lock/unlock karta hai"""
        if hasattr(self, "header") and self.header.winfo_exists():
            self.header.update_connection_ui(is_online, msg)

        if hasattr(self, "main_content") and self.main_content.winfo_exists():
            if hasattr(self.main_content, "set_connection_state"):
                self.main_content.set_connection_state(is_online)        

    def _assemble_dashboard(self):
        # 1. Header (Navigation callback ke sath)
        self.header = AdminHeader(
            self,
            admin_db=self.admin_db,
            user_info=self.user_info,
            on_logout=self.on_logout,
            on_sync_callback=self._handle_sync_refresh,
            on_navigate_tab=self._handle_navigation
        )
        self.header.pack(fill="x", side="top")

        # 2. Main Content
        self.main_content = AdminMain(
            self,
            admin_db=self.admin_db,
            on_user_updated_callback=self._handle_user_state_change
        )
        self.main_content.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Initial metrics load
        self.header.refresh_header_data()

    def _handle_navigation(self, tab_key):
        """Header card click hone par main area switch hota hai"""
        self.main_content.switch_view(tab_key)

    def _handle_sync_refresh(self):
        self.main_content.load_users()

    def _handle_user_state_change(self):
        self.header.refresh_header_data()
