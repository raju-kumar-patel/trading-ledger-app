import customtkinter as ctk
from tkinter import messagebox

class UserManagementView(ctk.CTkFrame):
    # Sabhi columns ke proportional weights yahan define karein (Total = 100)
    TABLE_COLUMNS = [
        {"name": "User ID", "weight": 12},
        {"name": "Name", "weight": 18},
        {"name": "Role", "weight": 11},
        {"name": "Account Status", "weight": 12},
        {"name": "Live Session", "weight": 11},
        {"name": "Client IP / Machine", "weight": 20},
        {"name": "Last Activity", "weight": 16}
    ]

    def __init__(self, master, admin_db, on_metrics_update=None):
        super().__init__(master, fg_color="transparent")
        self.admin_db = admin_db
        self.on_metrics_update = on_metrics_update
        self.selected_user = None
        self.is_online = True

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. TOP STATS BAR
        self.stats_bar = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10, height=60)
        self.stats_bar.pack(fill="x", pady=(0, 12))
        self.stats_bar.pack_propagate(False)

        self.lbl_total_users = ctk.CTkLabel(
            self.stats_bar, text="👥 Total Users: 0", 
            font=("Segoe UI", 13, "bold"), text_color="#94a3b8"
        )
        self.lbl_total_users.pack(side="left", padx=20)

        self.lbl_online_users = ctk.CTkLabel(
            self.stats_bar, text="🟢 Currently Logged-in: 0", 
            font=("Segoe UI", 13, "bold"), text_color="#22c55e"
        )
        self.lbl_online_users.pack(side="left", padx=20)

        self.lbl_active_accounts = ctk.CTkLabel(
            self.stats_bar, text="✅ Active Accounts: 0", 
            font=("Segoe UI", 13, "bold"), text_color="#38bdf8"
        )
        self.lbl_active_accounts.pack(side="left", padx=20)

        # 2. ACTION TOOLBAR
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar.pack(fill="x", pady=(0, 10))

        title_lbl = ctk.CTkLabel(
            self.toolbar, text="User Registry & Live Session Control", 
            font=("Segoe UI", 16, "bold"), text_color="#f8fafc"
        )
        title_lbl.pack(side="left")

        self.btn_refresh = ctk.CTkButton(
            self.toolbar, text="🔄 Refresh", width=90, height=32,
            fg_color="#334155", hover_color="#475569", command=self.refresh_data
        )
        self.btn_refresh.pack(side="right", padx=(8, 0))

        self.btn_kill_session = ctk.CTkButton(
            self.toolbar, text="🚨 Kill Session", width=120, height=32,
            fg_color="#7f1d1d", hover_color="#991b1b", text_color="#fca5a5",
            state="disabled", command=self._handle_kill_session
        )
        self.btn_kill_session.pack(side="right", padx=(8, 0))

        self.btn_toggle_status = ctk.CTkButton(
            self.toolbar, text="⚡ Toggle Status", width=130, height=32,
            fg_color="#1e3a8a", hover_color="#1d4ed8", text_color="#93c5fd",
            state="disabled", command=self._handle_toggle_status
        )
        self.btn_toggle_status.pack(side="right", padx=(8, 0))

        # 3. TABLE CONTAINER
        self.table_container = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        self.table_container.pack(fill="both", expand=True)

        self._create_table_headers()

        # Scrollable rows area
        self.rows_scroll = ctk.CTkScrollableFrame(self.table_container, fg_color="transparent")
        self.rows_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _create_table_headers(self):
        header_frame = ctk.CTkFrame(self.table_container, fg_color="#0f172a", height=38, corner_radius=6)
        # 🌟 Right side mein 26px padding taaki niche ke scrollbar se match ho jaye
        header_frame.pack(fill="x", padx=(10, 26), pady=(8, 4))
        header_frame.pack_propagate(False)

        for idx, col in enumerate(self.TABLE_COLUMNS):
            # 🌟 uniform="table_grid" lagane se text length se farq nahi padega
            header_frame.grid_columnconfigure(idx, weight=col["weight"], uniform="table_grid")
            lbl = ctk.CTkLabel(
                header_frame, 
                text=col["name"], 
                font=("Segoe UI", 11, "bold"),
                text_color="#94a3b8", 
                anchor="w"
            )
            # 🌟 sticky="ew" poori cell cover karega
            lbl.grid(row=0, column=idx, padx=8, sticky="ew")

    def refresh_data(self):
        for widget in self.rows_scroll.winfo_children():
            widget.destroy()

        self.selected_user = None
        self.btn_toggle_status.configure(state="disabled")
        self.btn_kill_session.configure(state="disabled")

        metrics = self.admin_db.get_user_management_metrics()
        self.lbl_total_users.configure(text=f"👥 Total Users: {metrics['total_users']}")
        self.lbl_online_users.configure(text=f"🟢 Currently Logged-in: {metrics['online_users']}")
        self.lbl_active_accounts.configure(text=f"✅ Active Accounts: {metrics['active_accounts']}")

        if self.on_metrics_update:
            self.on_metrics_update()

        users_data = self.admin_db.get_users_with_sessions()
        if not users_data:
            empty_lbl = ctk.CTkLabel(self.rows_scroll, text="No users found.", text_color="#64748b")
            empty_lbl.pack(pady=40)
            return

        for user in users_data:
            self._render_user_row(user)

    def _render_user_row(self, user):
        (u_id, u_name, role, acc_status, sess_id, ip, machine, login_time, last_act, sess_status) = user

        row = ctk.CTkFrame(self.rows_scroll, fg_color="#182234", height=42, corner_radius=6)
        row.pack(fill="x", pady=2, padx=2)
        row.pack_propagate(False)

        # 🌟 Header ke exact barabar columns configure karein
        for i, col in enumerate(self.TABLE_COLUMNS):
            row.grid_columnconfigure(i, weight=col["weight"], uniform="table_grid")

        # Column 0: User ID
        lbl_id = ctk.CTkLabel(row, text=str(u_id), font=("Segoe UI", 11, "bold"), text_color="#f8fafc", anchor="w")
        lbl_id.grid(row=0, column=0, padx=8, sticky="ew")

        # Column 1: Name
        lbl_name = ctk.CTkLabel(row, text=str(u_name or "—"), font=("Segoe UI", 11), text_color="#cbd5e1", anchor="w")
        lbl_name.grid(row=0, column=1, padx=8, sticky="ew")

        # Column 2: Role
        lbl_role = ctk.CTkLabel(row, text=str(role or "user"), font=("Segoe UI", 11), text_color="#94a3b8", anchor="w")
        lbl_role.grid(row=0, column=2, padx=8, sticky="ew")

        # Column 3: Account Status
        is_acc_active = str(acc_status).lower() == "active"
        badge_color = "#10b981" if is_acc_active else "#ef4444"
        lbl_acc = ctk.CTkLabel(
            row, text=f"● {acc_status.capitalize()}", font=("Segoe UI", 11, "bold"), 
            text_color=badge_color, anchor="w"
        )
        lbl_acc.grid(row=0, column=3, padx=8, sticky="ew")

        # Column 4: Live Session Status
        is_online = sess_status == "Online"
        sess_color = "#22c55e" if is_online else "#64748b"
        lbl_sess = ctk.CTkLabel(
            row, text=f"● {sess_status}", font=("Segoe UI", 11, "bold"), 
            text_color=sess_color, anchor="w"
        )
        lbl_sess.grid(row=0, column=4, padx=8, sticky="ew")

        # Column 5: Client IP / Machine
        client_info = f"{ip} ({machine})" if ip and machine else (ip or "—")
        lbl_ip = ctk.CTkLabel(row, text=client_info, font=("Segoe UI", 10), text_color="#94a3b8", anchor="w")
        lbl_ip.grid(row=0, column=5, padx=8, sticky="ew")

        # Column 6: Last Activity
        last_act_str = last_act.strftime("%d %b, %H:%M:%S") if last_act else "Never"
        lbl_time = ctk.CTkLabel(row, text=last_act_str, font=("Segoe UI", 10), text_color="#64748b", anchor="w")
        lbl_time.grid(row=0, column=6, padx=8, sticky="ew")

        # Row Click Handler
        def select_row(e=None):
            for child in self.rows_scroll.winfo_children():
                child.configure(fg_color="#182234")
            row.configure(fg_color="#283954")
            self.selected_user = {
                "id": u_id,
                "name": u_name,
                "status": acc_status,
                "is_online": is_online
            }
            if self.is_online:
                self.btn_toggle_status.configure(state="normal")
                self.btn_kill_session.configure(state="normal" if is_online else "disabled")

        for w in (row, lbl_id, lbl_name, lbl_role, lbl_acc, lbl_sess, lbl_ip, lbl_time):
            w.bind("<Button-1>", select_row)

    def _handle_toggle_status(self):
        if not self.selected_user:
            return
        u_id = self.selected_user["id"]
        curr_status = self.selected_user["status"]
        action = "Deactivate" if curr_status.lower() == "active" else "Activate"

        if messagebox.askyesno("Confirm Action", f"Kya aap user '{u_id}' ko {action} karna chahte hain?"):
            success, res = self.admin_db.toggle_user_account_status(u_id, curr_status)
            if success:
                messagebox.showinfo("Success", f"User status successfully updated to: {res}")
                self.refresh_data()
            else:
                messagebox.showerror("Error", f"Failed to update status: {res}")

    def _handle_kill_session(self):
        if not self.selected_user:
            return
        u_id = self.selected_user["id"]

        if messagebox.askyesno("Kill Session", f"Kya aap user '{u_id}' ka live session terminate karna chahte hain?"):
            success, res = self.admin_db.kill_user_session(u_id)
            if success:
                messagebox.showinfo("Session Terminated", f"User '{u_id}' ka live session successfully kill kar diya gaya hai.")
                self.refresh_data()
            else:
                messagebox.showerror("Error", f"Failed to kill session: {res}")

    def set_connection_state(self, is_online: bool):
        self.is_online = is_online
        self.btn_refresh.configure(state="normal" if is_online else "disabled")
        if not is_online:
            self.btn_toggle_status.configure(state="disabled")
            self.btn_kill_session.configure(state="disabled")
        elif self.selected_user:
            self.btn_toggle_status.configure(state="normal")
            if self.selected_user.get("is_online"):
                self.btn_kill_session.configure(state="normal")
