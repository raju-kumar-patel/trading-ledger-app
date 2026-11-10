import customtkinter as ctk
from tkinter import messagebox
from services.db_sync_service import SyncService

class SyncBalanceWidget(ctk.CTkFrame):
    def __init__(self, master, db_service, on_sync_complete_callback=None):
        super().__init__(master, fg_color="transparent")
        self.db = db_service
        self.sync_service = SyncService(db_service)
        self.on_sync_complete_callback = on_sync_complete_callback

        self._build_ui()

    def _build_ui(self):
        # 1. Total Liquid Balance Card
        bal_box = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=6, height=36)
        bal_box.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            bal_box,
            text="Balance:",
            font=("Segoe UI", 11),
            text_color="#94a3b8"
        ).pack(side="left", padx=(10, 5), pady=4)

        self.lbl_balance = ctk.CTkLabel(
            bal_box,
            text="₹ 0.00",
            font=("Segoe UI", 13, "bold"),
            text_color="#22c55e"
        )
        self.lbl_balance.pack(side="left", padx=(0, 10), pady=4)

        # 2. Database Sync / Update Button
        self.btn_sync = ctk.CTkButton(
            self,
            text="🔄 Sync DB",
            width=110,
            height=34,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 11, "bold"),
            command=self._start_sync
        )
        self.btn_sync.pack(side="left")

    def set_balance(self, amount):
        self.lbl_balance.configure(text=f"₹ {amount:,.2f}")

    def _start_sync(self):
        self.btn_sync.configure(state="disabled", text="⏳ Syncing...")
        self.sync_service.start_sync_thread(
            on_success_callback=self._on_success,
            on_error_callback=self._on_error)

    def _on_success(self, last_sync_time=None):
        self.btn_sync.configure(state="normal", text="🔄 Sync DB")
        messagebox.showinfo("Success", f"Database sync successful at {last_sync_time}!")
        if self.on_sync_complete_callback:
            self.on_sync_complete_callback(last_sync_time)

    def _on_error(self, err_msg=None):
        self.btn_sync.configure(state="normal", text="🔄 Sync DB")
        messagebox.showerror("Sync Error", f"Sync failed: {err_msg}")
