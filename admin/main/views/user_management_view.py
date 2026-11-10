import threading
from tkinter import ttk, messagebox
import customtkinter as ctk


class UserManagementView(ctk.CTkFrame):
    _cached_data = None

    def __init__(self, master, admin_db, on_metrics_update=None):
        super().__init__(master, fg_color="transparent")
        self.admin_db = admin_db
        self.on_metrics_update = on_metrics_update
        self.selected_user = None
        self.is_online = True

        self._build_ui()
        self.refresh_data(force_db_fetch=False)

    def _setup_treeview_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Users.Treeview",
            background="#111827",
            foreground="#f3f4f6",
            fieldbackground="#111827",
            rowheight=36,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        style.map(
            "Users.Treeview",
            background=[("selected", "#1e3a8a")],
            foreground=[("selected", "#ffffff")]
        )

        style.configure(
            "Users.Treeview.Heading",
            background="#1e293b",
            foreground="#94a3b8",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=6
        )
        style.map(
            "Users.Treeview.Heading",
            background=[("active", "#334155")]
        )

    def _build_ui(self):
        self._setup_treeview_styles()

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
            fg_color="#334155", hover_color="#475569", 
            command=lambda: self.refresh_data(force_db_fetch=True)
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

        # 3. TABLE CONTAINER (Native Fast Treeview)
        self.table_container = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        self.table_container.pack(fill="both", expand=True)

        columns = ("uid", "name", "role", "acc_status", "sess_status", "client_ip", "last_act")
        self.tree = ttk.Treeview(
            self.table_container, 
            columns=columns, 
            show="headings", 
            style="Users.Treeview",
            selectmode="browse"
        )

        self.tree.heading("uid", text="User ID", anchor="w")
        self.tree.heading("name", text="Name", anchor="w")
        self.tree.heading("role", text="Role", anchor="w")
        self.tree.heading("acc_status", text="Account Status", anchor="w")
        self.tree.heading("sess_status", text="Live Session", anchor="w")
        self.tree.heading("client_ip", text="Client IP / Machine", anchor="w")
        self.tree.heading("last_act", text="Last Activity", anchor="w")

        self.tree.column("uid", width=110, anchor="w")
        self.tree.column("name", width=160, anchor="w")
        self.tree.column("role", width=100, anchor="w")
        self.tree.column("acc_status", width=120, anchor="w")
        self.tree.column("sess_status", width=110, anchor="w")
        self.tree.column("client_ip", width=180, anchor="w")
        self.tree.column("last_act", width=150, anchor="w")

        scrollbar = ttk.Scrollbar(self.table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=4)
        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)

        # Selection listener
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Row text colors
        self.tree.tag_configure("ONLINE", foreground="#22c55e")
        self.tree.tag_configure("OFFLINE", foreground="#94a3b8")

    # =========================================================================
    # Non-blocking Background Fetch & Cache
    # =========================================================================
    def refresh_data(self, force_db_fetch=False):
        if not hasattr(self, "tree") or not self.winfo_exists():
            return

        cached = getattr(UserManagementView, "_cached_data", None)
        if cached is not None and not force_db_fetch:
            self._render_ui_data(cached)
            return

        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="disabled")

        threading.Thread(target=self._fetch_records_worker, daemon=True).start()

    def _fetch_records_worker(self):
        try:
            metrics = self.admin_db.get_user_management_metrics()
            users_data = self.admin_db.get_users_with_sessions()
            payload = {"metrics": metrics, "users": users_data}
            
            UserManagementView._cached_data = payload
            if self.winfo_exists():
                self.after(0, self._render_ui_data, payload)
        except Exception as e:
            if self.winfo_exists():
                self.after(0, self._on_fetch_error, str(e))

    def _render_ui_data(self, payload):
        if not self.winfo_exists() or not hasattr(self, "tree"):
            return

        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal" if self.is_online else "disabled")

        # 1. Update Metrics
        metrics = payload.get("metrics", {})
        self.lbl_total_users.configure(text=f"👥 Total Users: {metrics.get('total_users', 0)}")
        self.lbl_online_users.configure(text=f"🟢 Currently Logged-in: {metrics.get('online_users', 0)}")
        self.lbl_active_accounts.configure(text=f"✅ Active Accounts: {metrics.get('active_accounts', 0)}")

        if self.on_metrics_update:
            self.on_metrics_update()

        # 2. Reset Selection & Buttons
        self.selected_user = None
        self.btn_toggle_status.configure(state="disabled")
        self.btn_kill_session.configure(state="disabled")

        # 3. Populate Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        users_data = payload.get("users", [])
        for user in users_data:
            (u_id, u_name, role, acc_status, sess_id, ip, machine, login_time, last_act, sess_status) = user

            acc_str = f"● {str(acc_status).capitalize()}"
            sess_str = f"● {sess_status}"
            client_info = f"{ip} ({machine})" if ip and machine else (ip or "—")
            last_act_str = last_act.strftime("%d %b, %H:%M:%S") if last_act else "Never"

            tag = "ONLINE" if sess_status == "Online" else "OFFLINE"

            self.tree.insert(
                "",
                "end",
                values=(u_id, u_name or "—", role or "user", acc_str, sess_str, client_info, last_act_str),
                tags=(tag,)
            )

    def _on_tree_select(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            self.selected_user = None
            self.btn_toggle_status.configure(state="disabled")
            self.btn_kill_session.configure(state="disabled")
            return

        item_id = selected_items[0]
        vals = self.tree.item(item_id, "values")
        
        u_id = vals[0]
        u_name = vals[1]
        acc_status = vals[3].replace("● ", "").strip()
        sess_status = vals[4].replace("● ", "").strip()
        is_online = (sess_status == "Online")

        self.selected_user = {
            "id": u_id,
            "name": u_name,
            "status": acc_status,
            "is_online": is_online
        }

        if self.is_online:
            self.btn_toggle_status.configure(state="normal")
            self.btn_kill_session.configure(state="normal" if is_online else "disabled")

    def _on_fetch_error(self, err_msg):
        if not self.winfo_exists():
            return
        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal")
        print(f"❌ DB Error (Users): {err_msg}")

    # =========================================================================
    # Action Handlers
    # =========================================================================
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
                self.refresh_data(force_db_fetch=True)
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
                self.refresh_data(force_db_fetch=True)
            else:
                messagebox.showerror("Error", f"Failed to kill session: {res}")

    def set_connection_state(self, is_online: bool):
        self.is_online = is_online
        if hasattr(self, "btn_refresh") and self.btn_refresh.winfo_exists():
            self.btn_refresh.configure(state="normal" if is_online else "disabled")
        if not is_online:
            self.btn_toggle_status.configure(state="disabled")
            self.btn_kill_session.configure(state="disabled")
        elif self.selected_user:
            self.btn_toggle_status.configure(state="normal")
            if self.selected_user.get("is_online"):
                self.btn_kill_session.configure(state="normal")
