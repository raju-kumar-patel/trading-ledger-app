from datetime import datetime
import customtkinter as ctk


class UserFooter(ctk.CTkFrame):
    LEVEL_STYLES = {
        "info":    {"icon": "ℹ️", "color": "#38bdf8", "bg": "#0f172a"},
        "success": {"icon": "✅", "color": "#22c55e", "bg": "#0f172a"},
        "warning": {"icon": "⚠️", "color": "#f59e0b", "bg": "#1c1917"},
        "error":   {"icon": "❌", "color": "#ef4444", "bg": "#2a1215"},
    }

    def __init__(self, master):
        super().__init__(master, fg_color="#0f172a", height=38, corner_radius=8)
        self.pack_propagate(False)
        self._build_ui()

    def _build_ui(self):
        # Reserved Message / Error Label (Left)
        self.lbl_msg = ctk.CTkLabel(
            self,
            text="ℹ️ Ready. Welcome to RAAS Market Terminal.",
            font=("Segoe UI", 11, "bold"),
            text_color="#38bdf8",
            anchor="w"
        )
        self.lbl_msg.pack(side="left", padx=14, fill="x", expand=True)

        # Network/DB Status Indicator (Right)
        self.lbl_status = ctk.CTkLabel(
            self,
            text="🟢 Online",
            font=("Segoe UI", 11, "bold"),
            text_color="#22c55e"
        )
        self.lbl_status.pack(side="right", padx=14)

    def show_message(self, message: str, level: str = "info"):
        """Footer mein error, warning ya info message display karta hai"""
        if not self.winfo_exists():
            return
        style = self.LEVEL_STYLES.get(level.lower(), self.LEVEL_STYLES["info"])
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.configure(fg_color=style["bg"])
        self.lbl_msg.configure(
            text=f"{style['icon']} [{timestamp}]  {message}",
            text_color=style["color"]
        )

    def set_connection_state(self, is_online: bool):
        if not self.winfo_exists():
            return
        if is_online:
            self.lbl_status.configure(text="🟢 Online", text_color="#22c55e")
        else:
            self.lbl_status.configure(text="🔴 Offline", text_color="#ef4444")
