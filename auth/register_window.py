import customtkinter as ctk

class RegisterWindow(ctk.CTkFrame):
    def __init__(self, master, auth_manager, on_back_to_login):
        super().__init__(master, fg_color="#1e293b")
        self.auth_manager = auth_manager
        self.on_back_to_login = on_back_to_login

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(container, text="📝", font=("Segoe UI", 28)).pack(pady=(5, 2))
        ctk.CTkLabel(container, text="Trading Ledger Registration", font=("Segoe UI", 18, "bold"), text_color="#38bdf8").pack(pady=(0, 10))

        # 1. Full Name
        ctk.CTkLabel(container, text="Full Name:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15)
        self.ent_name = ctk.CTkEntry(container, height=32, width=300, placeholder_text="Enter your name")
        self.ent_name.pack(pady=(2, 8), padx=15)

        # 2. Email
        ctk.CTkLabel(container, text="Email Address:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15)
        self.ent_email = ctk.CTkEntry(container, height=32, width=300, placeholder_text="e.g. user@email.com")
        self.ent_email.pack(pady=(2, 8), padx=15)

        # 3. PAN (User ID)
        ctk.CTkLabel(container, text="PAN Number (User ID):", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15)
        self.ent_pan = ctk.CTkEntry(container, height=32, width=300, placeholder_text="e.g. ABCDE1234F")
        self.ent_pan.pack(pady=(2, 8), padx=15)

        # 4. 4-Digit PIN
        ctk.CTkLabel(container, text="4-Digit PIN (For Login):", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15)
        self.ent_pin = ctk.CTkEntry(container, height=32, width=300, justify="center", font=("Segoe UI", 13), show="*", placeholder_text="4 digits")
        self.ent_pin.pack(pady=(2, 8), padx=15)

        # 5. Password
        ctk.CTkLabel(container, text="Password:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15)
        self.ent_pass = ctk.CTkEntry(container, height=32, width=300, justify="center", font=("Segoe UI", 13), show="*", placeholder_text="Secure password")
        self.ent_pass.pack(pady=(2, 8), padx=15)

        # Message Label
        self.lbl_msg = ctk.CTkLabel(container, text="", font=("Segoe UI", 11))
        self.lbl_msg.pack(pady=2, padx=15)

        # Buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(pady=10, padx=15)

        ctk.CTkButton(
            btn_frame, text="Register", width=140, height=36, 
            fg_color="#059669", hover_color="#047857", font=("Segoe UI", 12, "bold"),
            command=self._handle_register
        ).grid(row=0, column=0, padx=5)

        ctk.CTkButton(
            btn_frame, text="Back to Login", width=140, height=36, 
            fg_color="#475569", hover_color="#334155", font=("Segoe UI", 12, "bold"),
            command=self.on_back_to_login
        ).grid(row=0, column=1, padx=5)

    def _handle_register(self):
        name = self.ent_name.get().strip()
        email = self.ent_email.get().strip()
        pan = self.ent_pan.get().strip()
        pin = self.ent_pin.get().strip()
        password = self.ent_pass.get().strip()

        if not name or not email or not pan or not pin or not password:
            self.lbl_msg.configure(text="Sabhi fields bharna anivarya hai!", text_color="#ef4444")
            return

        # AuthManager ke zariye register karein
        ok, msg = self.auth_manager.register_user(name, email, pan, pin, password)
        if ok:
            self.lbl_msg.configure(text=msg, text_color="#22c55e")
        else:
            self.lbl_msg.configure(text=msg, text_color="#ef4444")
