from tkinter import messagebox
import customtkinter as ctk


class ProfileDialog(ctk.CTkToplevel):
    """User Profile Details dikhane ke liye Modal Popup"""
    def __init__(self, master, user_info):
        super().__init__(master)
        self.title("User Profile")
        self.geometry("360x260")
        self.resizable(False, False)
        self.configure(fg_color="#0f172a")
        self.transient(master)
        self.grab_set()

        user_id = user_info.get("id", "N/A")
        user_name = user_info.get("name", "Trader")
        user_role = str(user_info.get("role", "user")).capitalize()

        card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            card, text="👤 Account Profile",
            font=("Segoe UI", 16, "bold"), text_color="#38bdf8"
        ).pack(pady=(16, 12))

        info_text = (
            f"User ID   :   {user_id}\n\n"
            f"Full Name :   {user_name}\n\n"
            f"Role      :   {user_role}"
        )
        ctk.CTkLabel(
            card, text=info_text,
            font=("Segoe UI", 12, "bold"), text_color="#f8fafc", justify="left"
        ).pack(pady=8, padx=20)

        ctk.CTkButton(
            card, text="Close", width=100, height=30,
            fg_color="#334155", hover_color="#475569",
            command=self.destroy
        ).pack(pady=(14, 10))


class UserDropdownWidget(ctk.CTkFrame):
    def __init__(self, master, user_info=None, on_logout_callback=None, notify_callback=None):
        super().__init__(master, fg_color="transparent")
        self.user_info = user_info or {}
        self.on_logout = on_logout_callback
        self.notify = notify_callback
        self.profile_window = None

        user_name = self.user_info.get("name", "User")
        user_id = self.user_info.get("id", "ID")
        self.default_label = f"👤 {user_name} ({user_id})"

        self._build_ui()

    def _build_ui(self):
        self.dropdown = ctk.CTkOptionMenu(
            self,
            values=[self.default_label, "👤 My Profile", "🚪 Logout"],
            fg_color="#1e3a8a",
            button_color="#1d4ed8",
            button_hover_color="#2563eb",
            dropdown_fg_color="#0f172a",
            dropdown_hover_color="#1e293b",
            dropdown_text_color="#f8fafc",
            font=("Segoe UI", 12, "bold"),
            height=34,
            corner_radius=8,
            command=self._on_menu_select
        )
        self.dropdown.set(self.default_label)
        self.dropdown.pack(side="right")

    def _on_menu_select(self, choice: str):
        # Selection ke turant baad top label ko wapas user ke naam par reset karein
        self.dropdown.set(self.default_label)

        if choice == "👤 My Profile":
            self._open_profile_modal()
        elif choice == "🚪 Logout":
            self._trigger_logout()

    def _open_profile_modal(self):
        if self.notify:
            self.notify("Viewing user profile details.", "info")
        if self.profile_window is None or not self.profile_window.winfo_exists():
            self.profile_window = ProfileDialog(self.winfo_toplevel(), self.user_info)
        else:
            self.profile_window.focus()

    def _trigger_logout(self):
        if messagebox.askyesno("Confirm Logout", "Kya aap apne account se logout karna chahte hain?"):
            if self.notify:
                self.notify("Logging out...", "warning")
            if callable(self.on_logout):
                self.on_logout()
