import threading
import customtkinter as ctk
from database.DBCore import DBCore
from user.user_db import UserDatabase

class BalanceWidget(ctk.CTkFrame):
    def __init__(self, master, user_info=None, db_core=None, notify_callback=None, poll_interval=2.0):
        super().__init__(master, fg_color="#0f172a", corner_radius=8)
        self.user_info = user_info or {}
        self.db = db_core or DBCore
        self.notify = notify_callback
        self.poll_interval = poll_interval

        # 🌟 Data Layer ko UI se alag kiya: UserDatabase service instance
        self.user_db = UserDatabase(db_core or DBCore)
        
        # State tracking: Sirf balance change hone par redraw hoga
        self._current_balance = None
        self._stop_event = threading.Event()

        self._build_ui()
        self._start_auto_sync()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="💰 Balance:",
            font=("Segoe UI", 11), text_color="#94a3b8"
        ).pack(side="left", padx=(14, 6), pady=6)

        self.lbl_amount = ctk.CTkLabel(
            self, text="₹ 0.00",
            font=("Segoe UI", 13, "bold"), text_color="#22c55e"
        )
        self.lbl_amount.pack(side="left", padx=(0, 14), pady=6)

    def _get_user_id(self):
        """'id' ya 'user_id' kisi bhi key se safe ID extract karta hai"""
        return self.user_info.get("id") or self.user_info.get("user_id")

    # =========================================================================
    # Automatic Background Balance Watcher (Zero UI Lag)
    # =========================================================================
    def _start_auto_sync(self):
        """Background daemon thread start karta hai jo balance change detect karega"""
        self._stop_event.clear()
        worker = threading.Thread(target=self._auto_sync_loop, daemon=True)
        worker.start()

    def _auto_sync_loop(self):
        uid = self._get_user_id()
        if not uid:
            return

        while not self._stop_event.is_set():
            try:
				# 🌟 Database operation sirf user_db service layer se hoga
                new_balance = self.user_db.get_user_balance(uid)

                # 🌟 Sirf tab UI update karein jab database mein balance sach mein badla ho
                if new_balance is not None and new_balance != self._current_balance:
                    is_first_load = (self._current_balance is None)
                    self._current_balance = new_balance

                    if self.winfo_exists():
                        self.after(0, self._apply_balance_to_ui, new_balance, is_first_load)

            except Exception as e:
                print(f"⚠️ [BalanceWidget AutoSync Error]: {e}")

            # Agle check se pehle wait karein (Logout hone par turant exit hoga)
            self._stop_event.wait(self.poll_interval)

    def _apply_balance_to_ui(self, balance: float, is_first_load: bool):
        if not self.winfo_exists():
            return

        self.lbl_amount.configure(text=f"₹ {balance:,.2f}")

        # Jab table mein balance update ho, tab footer mein message dikhayein
        if not is_first_load and self.notify:
            self.notify(f"Account balance auto-updated: ₹ {balance:,.2f}", "success")

    def refresh_now(self):
        """Agar app ke andar kisi trade/form se balance badle, toh instant update ke liye"""
        uid = self.user_info.get("id")
        if not uid:
            return

        def _instant_worker():
            try:
                new_bal = self._fetch_db_balance(uid)
                if new_bal is not None and new_bal != self._current_balance:
                    self._current_balance = new_bal
                    if self.winfo_exists():
                        self.after(0, self._apply_balance_to_ui, new_bal, False)
            except Exception:
                pass

        threading.Thread(target=_instant_worker, daemon=True).start()

    def destroy(self):
        """Logout ya window close hone par background watcher ko safely stop karta hai"""
        self._stop_event.set()
        super().destroy()
