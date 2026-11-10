import customtkinter as ctk
from database.DBCore import DBCore
from user.header.user_header import UserHeader
from user.body.user_body import UserBody
from user.footer.user_footer import UserFooter


class UserApp(ctk.CTkFrame):
    def __init__(self, master, user_info=None, db_core=None, on_logout=None, session_manager=None, **kwargs):
        super().__init__(master, fg_color="#0b1120")
        self.pack(fill="both", expand=True)

        self.user_info = user_info or {}
        self.db = db_core or DBCore
        self.on_logout = on_logout or kwargs.get("on_logout_callback")
        self.session_manager = session_manager

        self._assemble_dashboard()

    def _assemble_dashboard(self):
        # 1. BOTTOM: Reserved Error/Msg Footer (Pehle pack karein taaki bottom par fix rahe)
        self.footer = UserFooter(self)
        self.footer.pack(side="bottom", fill="x", padx=12, pady=(6, 10))

        # 2. TOP: Modular Header (Logo + Balance + User Dropdown)
        self.header = UserHeader(
            self,
            user_info=self.user_info,
            db_core=self.db,
            on_logout=self._handle_logout,
            notify_callback=self.notify
        )
        self.header.pack(side="top", fill="x", padx=12, pady=(10, 6))

        # 3. CENTER: Expandable Tools Body
        self.body = UserBody(
            self,
            user_info=self.user_info,
            db_core=self.db,
            notify_callback=self.notify
        )
        self.body.pack(fill="both", expand=True, padx=12, pady=4)

    def notify(self, message: str, level: str = "info"):
        """Header ya Body ke kisi bhi module ka message/error Footer mein dikhata hai"""
        if hasattr(self, "footer") and self.footer.winfo_exists():
            self.footer.show_message(message, level)

    def _handle_logout(self):
        """Session terminate karke main login screen par bhejta hai"""
        try:
            if self.session_manager:
                self.session_manager.terminate_session()
        except Exception as e:
            self.notify(f"Session close error: {e}", "error")

        if callable(self.on_logout):
            self.on_logout()


# Aliases for main.py compatibility
UserDashboard = UserApp
UserUIMain = UserApp
