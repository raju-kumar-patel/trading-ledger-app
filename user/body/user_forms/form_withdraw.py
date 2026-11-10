from datetime import date, datetime
import tkinter as tk
import customtkinter as ctk
from user.validators import FormValidator
from user.user_db import UserDatabase
from services.date_picker import attach_calendar_picker


class FormWithdraw(ctk.CTkFrame):
    def __init__(self, master, user_info=None, notify_callback=None):
        super().__init__(master, fg_color="transparent")
        self.user_info = user_info or {}
        self.notify = notify_callback
        self.db = UserDatabase()
        self._build_ui()

    def _get_user_id(self):
        return self.user_info.get("id") or self.user_info.get("user_id")

    def _build_ui(self):
        # Card Container (Height expanded to 390 to fit reason dropdown)
        card = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=12, width=460, height=390)
        card.pack(pady=20, padx=20)
        card.pack_propagate(False)

        # Title
        ctk.CTkLabel(
            card,
            text="📤 Withdraw / Settle Cash Balance",
            font=("Segoe UI", 16, "bold"),
            text_color="#f59e0b"
        ).pack(pady=(16, 10))

        # 1. Date Input Row
        date_frame = ctk.CTkFrame(card, fg_color="transparent")
        date_frame.pack(fill="x", padx=40, pady=5)

        ctk.CTkLabel(
            date_frame,
            text="Tran Date:",
            font=("Segoe UI", 12, "bold"),
            text_color="#94a3b8"
        ).pack(side="left")

        self.ent_date = ctk.CTkEntry(date_frame, width=160, height=32)
        self.ent_date.insert(0, date.today().strftime("%Y-%m-%d"))
        self.ent_date.pack(side="right")
        attach_calendar_picker(self.ent_date)

        # 🌟 POINT 2: Reason Dropdown Row
        reason_frame = ctk.CTkFrame(card, fg_color="transparent")
        reason_frame.pack(fill="x", padx=40, pady=5)

        ctk.CTkLabel(
            reason_frame,
            text="Reason / Type:",
            font=("Segoe UI", 12, "bold"),
            text_color="#94a3b8"
        ).pack(side="left")

        self.opt_reason = ctk.CTkOptionMenu(
            reason_frame,
            values=["Personal Withdrawal", "Quarterly Settlement"],
            width=190,
            height=32,
            fg_color="#1e293b",
            button_color="#334155",
            button_hover_color="#475569",
            text_color="#f8fafc",
            font=("Segoe UI", 11, "bold"),
            command=self._on_reason_change
        )
        self.opt_reason.set("Personal Withdrawal")
        self.opt_reason.pack(side="right")

        # 2. Withdraw Amount Input
        self.ent_amt = ctk.CTkEntry(
            card,
            placeholder_text="Withdraw Amount (₹)",
            width=380,
            height=34
        )
        self.ent_amt.pack(pady=8)

        # 3. Narration Input
        self.ent_narr = ctk.CTkEntry(
            card,
            placeholder_text="Narration (e.g. Bank Transfer / Self)",
            width=380,
            height=34
        )
        self.ent_narr.insert(0, "Bank Transfer / Self Withdrawal")
        self.ent_narr.pack(pady=8)

        # 4. Action Button
        ctk.CTkButton(
            card,
            text="⚠️ Confirm & Withdraw",
            width=380,
            height=38,
            corner_radius=6,
            fg_color="#b45309",
            hover_color="#92400e",
            font=("Segoe UI", 12, "bold"),
            command=self._submit_withdraw
        ).pack(pady=(14, 10))

    def _on_reason_change(self, choice):
        if choice == "Quarterly Settlement":
            self.ent_narr.delete(0, tk.END)
            self.ent_narr.insert(0, "Broker Balance Settlement - Payout to Bank")
        else:
            self.ent_narr.delete(0, tk.END)
            self.ent_narr.insert(0, "Bank Transfer / Self Withdrawal")

    def _submit_withdraw(self):
        uid = self._get_user_id()
        if not uid:
            if self.notify:
                self.notify("User session expired ya invalid hai!", "error")
            return

        date_str = self.ent_date.get().strip()
        try:
            valid_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            if self.notify:
                self.notify("Date format galat hai! Kripya YYYY-MM-DD enter karein.", "error")
            return

        ok_amt, amt = FormValidator.is_positive_number(self.ent_amt.get(), "Withdraw Amount")
        if not ok_amt:
            if self.notify:
                self.notify(amt, "error")
            return

        reason = self.opt_reason.get().strip()
        user_narr = self.ent_narr.get().strip()
        if not user_narr:
            final_narr = reason
        else:
            final_narr = user_narr if reason in user_narr else f"[{reason}] {user_narr}"

        # Database Execution Call (Debits user balance)
        success, msg = self.db.execute_withdraw(uid, amt, final_narr, tran_date=valid_date)
        if self.notify:
            self.notify(msg, "success" if success else "error")

        if success:
            self.ent_amt.delete(0, tk.END)
            self.opt_reason.set("Personal Withdrawal")
            self._on_reason_change("Personal Withdrawal")
