from datetime import date, datetime
import customtkinter as ctk
from user.validators import FormValidator
from user.user_db import UserDatabase
from services.date_picker import attach_calendar_picker

class FormDeposit(ctk.CTkFrame):
    def __init__(self, master, user_info=None, notify_callback=None):
        super().__init__(master, fg_color="transparent")
        self.user_info = user_info or {}
        self.notify = notify_callback
        self.db = UserDatabase()
        self._build_ui()

    def _build_ui(self):
        # Card height ko adjust karke 310 kar diya gaya hai taaki Date input smoothly fit ho sake
        card = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=12, width=440, height=310)
        card.pack(pady=20, padx=20)
        card.pack_propagate(False)

        ctk.CTkLabel(
            card, text="➕ Deposit Cash Balance",
            font=("Segoe UI", 15, "bold"), text_color="#22c55e"
        ).pack(pady=(16, 10))

        # 1. Date Input Field (Default: Current Date YYYY-MM-DD)
        today_str = date.today().strftime("%Y-%m-%d")
        self.ent_date = ctk.CTkEntry(
            card, placeholder_text="Date (YYYY-MM-DD)", width=300, height=34
        )
        self.ent_date.insert(0, today_str)
        self.ent_date.pack(pady=5)
        attach_calendar_picker(self.ent_date)

        # 2. Amount Field
        self.ent_amt = ctk.CTkEntry(
            card, placeholder_text="Amount (₹)", width=300, height=34
        )
        self.ent_amt.pack(pady=5)

        # 3. Narration Field
        self.ent_narr = ctk.CTkEntry(
            card, placeholder_text="Narration (e.g. UPI Transfer, Bank Deposit)", width=300, height=34
        )
        self.ent_narr.pack(pady=5)

        # Submit Button
        ctk.CTkButton(
            card, text="✅ Deposit Now", width=300, height=36,
            fg_color="#059669", hover_color="#047857", font=("Segoe UI", 12, "bold"),
            command=self._submit_deposit
        ).pack(pady=(12, 10))

    def _submit_deposit(self):
        uid = self.user_info.get("id")
        if not uid:
            if self.notify:
                self.notify("User session invalid ya expired hai!", "error")
            return

        # 1. Date validate karein (Format: YYYY-MM-DD)
        date_str = self.ent_date.get().strip()
        try:
            valid_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            if self.notify:
                self.notify("Galat Date format! Kripya YYYY-MM-DD format mein daalein (e.g. 2026-10-28)", "error")
            return

        # 2. Amount validate karein
        ok_amt, amt = FormValidator.is_positive_number(self.ent_amt.get(), "Deposit Amount")
        if not ok_amt:
            if self.notify:
                self.notify(amt, "error")
            return

        # 3. Narration
        narration = self.ent_narr.get().strip() or "Cash Deposit"

        # 4. Database mein execute karein (Date ke sath)
        success, msg = self.db.execute_deposit(uid, amt, narration, tran_date=valid_date)
        if self.notify:
            self.notify(msg, "success" if success else "error")

        if success:
            # Entry clear karein aur date wapas reset karein
            self.ent_amt.delete(0, "end")
            self.ent_narr.delete(0, "end")
            self.ent_date.delete(0, "end")
            self.ent_date.insert(0, date.today().strftime("%Y-%m-%d"))
