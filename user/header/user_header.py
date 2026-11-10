import customtkinter as ctk
from user.header.logo_widget import LogoWidget
from user.header.balance_widget import BalanceWidget
from user.header.user_dropdown_widget import UserDropdownWidget


class UserHeader(ctk.CTkFrame):
    def __init__(self, master, user_info=None, db_core=None, on_logout=None, notify_callback=None):
        super().__init__(master, fg_color="#1e293b", height=64, corner_radius=10)
        self.pack_propagate(False)

        self.user_info = user_info or {}
        self.db = db_core
        self.on_logout = on_logout
        self.notify = notify_callback

        self._assemble_header()

    def _assemble_header(self):
        # 1. Left: Logo & App Title
        self.logo_section = LogoWidget(self)
        self.logo_section.pack(side="left", padx=16, pady=8)

        # 2. Right: User Profile & Logout Dropdown
        self.user_dropdown = UserDropdownWidget(
            self,
            user_info=self.user_info,
            on_logout_callback=self.on_logout,
            notify_callback=self.notify
        )
        self.user_dropdown.pack(side="right", padx=(8, 16), pady=12)

        # 3. Center-Right: User Balance Section
        self.balance_section = BalanceWidget(
            self,
            user_info=self.user_info,
            db_core=self.db,
            notify_callback=self.notify
        )
        self.balance_section.pack(side="right", padx=8, pady=12)
