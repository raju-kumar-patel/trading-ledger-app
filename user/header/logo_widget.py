import customtkinter as ctk


class LogoWidget(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build_ui()

    def _build_ui(self):
        self.lbl_logo = ctk.CTkLabel(
            self, text="📈", font=("Segoe UI", 24)
        )
        self.lbl_logo.pack(side="left", padx=(0, 10))

        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left")

        self.lbl_title = ctk.CTkLabel(
            text_frame, text="RAAS Market Terminal",
            font=("Segoe UI", 16, "bold"), text_color="#f8fafc", anchor="w"
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_subtitle = ctk.CTkLabel(
            text_frame, text="Equity & ETF Wilder RSI Analytics",
            font=("Segoe UI", 10), text_color="#94a3b8", anchor="w"
        )
        self.lbl_subtitle.pack(anchor="w")
