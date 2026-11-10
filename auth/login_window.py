import customtkinter as ctk
import threading
from services.connection_checker import ConnectionChecker

class LoginWindow(ctk.CTkFrame):
    def __init__(self, master, auth_manager, on_login_success, on_open_register=None):
        super().__init__(master, fg_color="#1e293b")  # Uniform background
        
        self.auth_manager = auth_manager
        self.on_login_success = on_login_success
        self.on_open_register = on_open_register  # 👈 Yahan properly define kiya gaya hai
        
        # ConnectionChecker ko initialize karein
        self.checker = ConnectionChecker(getattr(auth_manager, "db", None))
        self.is_connected = False

        self._build_ui()
        self._check_connection()  # Startup par connection check karein

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        # Header Section
        ctk.CTkLabel(container, text="👥", font=("Segoe UI", 32)).pack(pady=(10, 5))
        ctk.CTkLabel(container, text="Trading Ledger Login", font=("Segoe UI", 20, "bold"), text_color="#38bdf8").pack(pady=(0, 5))
        
        # Status / Instruction Label
        self.lbl_subtitle = ctk.CTkLabel(container, text="Connection check ho raha hai...", font=("Segoe UI", 12), text_color="#94a3b8")
        self.lbl_subtitle.pack(pady=(0, 20))

        # 1. Username Input
        ctk.CTkLabel(container, text="User ID:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10)
        self.ent_user = ctk.CTkEntry(container, height=38, width=300, placeholder_text="e.g. username")
        self.ent_user.pack(pady=(3, 15))

        # 2. Password Input
        ctk.CTkLabel(container, text="Password / PIN:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10)
        self.ent_pin = ctk.CTkEntry(container, height=38, width=300, justify="center", font=("Segoe UI", 14), show="*")
        self.ent_pin.pack(pady=(3, 10))

        # Feedback/Error message
        self.lbl_msg = ctk.CTkLabel(container, text="", font=("Segoe UI", 11))
        self.lbl_msg.pack(pady=5)

        # 3. Dynamic Action Container (Buttons ke liye)
        self.action_container = ctk.CTkFrame(container, fg_color="transparent")
        self.action_container.pack(pady=15)

        # A. Online Buttons Box (Sign In & Register)
        self.online_box = ctk.CTkFrame(self.action_container, fg_color="transparent")
        
        self.btn_login = ctk.CTkButton(
            self.online_box, text="Sign In", width=140, height=38, 
            fg_color="#2563eb", hover_color="#1d4ed8", font=("Segoe UI", 12, "bold"),
            command=self._handle_login
        )
        self.btn_login.grid(row=0, column=0, padx=6)

        # 🌟 Register button click par alag form khulne ke liye method call hoga
        self.btn_register = ctk.CTkButton(
            self.online_box, text="Register New", width=140, height=38, 
            fg_color="#059669", hover_color="#047857", font=("Segoe UI", 12, "bold"),
            command=self._handle_register_click
        )
        self.btn_register.grid(row=0, column=1, padx=6)

        # B. Offline / Reconnect Button
        self.btn_reconnect = ctk.CTkButton(
            self.action_container, text="⚡ Retry Connection", width=290, height=38,
            fg_color="#dc2626", hover_color="#b91c1c", font=("Segoe UI", 12, "bold"),
            command=self._retry_connection
        )

    def _check_connection(self):
        """Background thread mein ConnectionChecker se internet aur database check karta hai"""
        self.lbl_subtitle.configure(text="Checking Internet & Database...", text_color="#38bdf8")
        self.online_box.pack_forget()
        self.btn_reconnect.pack_forget()

        def background_task():
            is_ok, msg = self.checker.check_all()
            self.after(0, lambda: self._apply_connection_state(is_ok, msg))

        threading.Thread(target=background_task, daemon=True).start()

    def _apply_connection_state(self, is_ok, msg):
        self.is_connected = is_ok
        if is_ok:
            # Dono check pass hone par login/register buttons dikhayein
            self.btn_reconnect.pack_forget()
            self.online_box.pack()
            self.lbl_subtitle.configure(text="User ID aur Password enter karein", text_color="#94a3b8")
            self.lbl_msg.configure(text="")
        else:
            # Agar net ya DB fail ho toh retry button aur exact error message show ho
            self.online_box.pack_forget()
            self.btn_reconnect.pack()
            self.btn_reconnect.configure(state="normal", text="⚡ Retry Connection")
            self.lbl_subtitle.configure(text=msg, text_color="#ef4444")
            self.lbl_msg.configure(text="Kripya connection check karke retry karein.", text_color="#ef4444")

    def _retry_connection(self):
        self.btn_reconnect.configure(state="disabled", text="Connecting...")
        self._check_connection()

    def _handle_login(self):
        if not self.is_connected:
            self.lbl_msg.configure(text="Pehle internet aur database connect karein!", text_color="#ef4444")
            return

        uid = self.ent_user.get().strip().lower()
        password = self.ent_pin.get().strip()
        
        # 🔍 DEBUG: Console par user input check karne ke liye
        print(f"DEBUG LOGIN INPUT -> User ID: '{uid}', Password/PIN: '{password}'")
        
        if not uid or not password:
            self.lbl_msg.configure(text="Sahi User ID aur Password dalein", text_color="#ef4444")
            return

        success, user_info = self.auth_manager.authenticate(uid, password)
        
        # 🔍 DEBUG: Auth result check karne ke liye
        print(f"DEBUG AUTH RESULT -> Success: {success}, UserInfo: {user_info}")
        
        if success and user_info:
            self.lbl_msg.configure(text="Login Successful!", text_color="#22c55e")
            if self.on_login_success:
                self.on_login_success(user_info)
        else:
            self.lbl_msg.configure(text="Invalid Username or Password!", text_color="#ef4444")

    def _handle_register_click(self):
        """Register button dabane par alag registration form open hoga"""
        if not self.is_connected:
            self.lbl_msg.configure(text="Pehle internet aur database connect karein!", text_color="#ef4444")
            return
            
        if self.on_open_register:
            self.on_open_register()
