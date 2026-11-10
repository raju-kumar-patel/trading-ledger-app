import customtkinter as ctk

class ProfileDropdownWidget(ctk.CTkFrame):
    def __init__(self, master, user_info, on_logout_func):
        super().__init__(master, fg_color="transparent")
        self.user_info = user_info
        self.on_logout_func = on_logout_func

        self._build_ui()

    def _build_ui(self):
        admin_name = self.user_info.get("name", "Admin")
        display_label = f"👤 {admin_name} (Admin)"

        # Dropdown Options
        self.menu_options = [display_label, "⚙️ Settings", "🚪 Logout"]

        self.dropdown = ctk.CTkOptionMenu(
            self,
            values=self.menu_options,
            command=self._on_option_selected,
            width=180,
            height=34,
            fg_color="#334155",
            button_color="#1e293b",
            button_hover_color="#0f172a",
            dropdown_fg_color="#1e293b",
            dropdown_hover_color="#334155",
            dropdown_text_color="#f8fafc",
            font=("Segoe UI", 11, "bold"),
            dynamic_resizing=False
        )
        self.dropdown.set(display_label)
        self.dropdown.pack(side="right")

    def _on_option_selected(self, choice):
        if "Logout" in choice:
            self.on_logout_func()
        else:
            # Menu label ko wapas username par reset rakhein
            admin_name = self.user_info.get("name", "Admin")
            self.dropdown.set(f"👤 {admin_name} (Admin)")
