from datetime import date, datetime
import tkinter as tk
import customtkinter as ctk
from user.validators import FormValidator
from user.user_db import UserDatabase
from services.date_picker import attach_calendar_picker


class AutocompleteEntry(ctk.CTkEntry):
    """Character-wise instant autocomplete entry for active stock/ETF symbols"""
    def __init__(self, master, symbol_list=None, **kwargs):
        super().__init__(master, **kwargs)
        self.symbol_list = symbol_list or []
        self._listbox_window = None

        self.bind("<KeyRelease>", self._on_keyrelease)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Down>", self._on_down_key)

    def set_symbols(self, symbols: list[str]):
        self.symbol_list = symbols

    def _on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return

        typed = self.get().strip().upper()
        if not typed:
            self._close_listbox()
            return

        matches = [s for s in self.symbol_list if typed in s][:12]
        if not matches:
            self._close_listbox()
            return

        self._show_listbox(matches)

    def _show_listbox(self, matches):
        if not self._listbox_window:
            self._listbox_window = tk.Toplevel(self)
            self._listbox_window.wm_overrideredirect(True)
            self._listbox_window.attributes("-topmost", True)

            self._lb = tk.Listbox(
                self._listbox_window,
                bg="#1e293b",
                fg="#f8fafc",
                selectbackground="#0284c7",
                selectforeground="#ffffff",
                font=("Segoe UI", 10, "bold"),
                borderwidth=1,
                relief="solid"
            )
            self._lb.pack(fill="both", expand=True)
            self._lb.bind("<<ListboxSelect>>", self._on_select)
            self._lb.bind("<Return>", self._on_select)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        w = max(self.winfo_width(), 160)
        h = min(len(matches) * 24 + 6, 180)
        self._listbox_window.geometry(f"{w}x{h}+{x}+{y}")

        self._lb.delete(0, tk.END)
        for item in matches:
            self._lb.insert(tk.END, item)

    def _on_select(self, event=None):
        if self._listbox_window and self._lb.curselection():
            selected = self._lb.get(self._lb.curselection()[0])
            self.delete(0, tk.END)
            self.insert(0, selected)
            self._close_listbox()

    def _on_down_key(self, event):
        if self._listbox_window and hasattr(self, "_lb"):
            self._lb.focus_set()
            self._lb.selection_set(0)

    def _on_focus_out(self, event=None):
        self.after(200, self._close_listbox)

    def _close_listbox(self):
        if self._listbox_window:
            self._listbox_window.destroy()
            self._listbox_window = None


class FormPurchase(ctk.CTkFrame):
    def __init__(self, master, user_info=None, notify_callback=None):
        super().__init__(master, fg_color="transparent")
        self.user_info = user_info or {}
        self.notify = notify_callback
        self.db = UserDatabase()
        self.share_rows = []

        self.active_symbols = self.db.get_active_symbols()

        self._build_ui()
        self._add_share_row()

    def _get_user_id(self):
        return self.user_info.get("id") or self.user_info.get("user_id")

    def _build_ui(self):
        # 1. Bottom Row: Brokerage & Purchase Action
        last_row = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=8, height=52)
        last_row.pack(side="bottom", fill="x", pady=(6, 4))
        last_row.pack_propagate(False)

        brok_box = ctk.CTkFrame(last_row, fg_color="transparent")
        brok_box.pack(side="left", padx=14, pady=8)
        ctk.CTkLabel(brok_box, text="Brokerage (₹):", font=("Segoe UI", 12, "bold"), text_color="#cbd5e1").pack(side="left", padx=(0, 8))
        self.ent_brokerage = ctk.CTkEntry(brok_box, placeholder_text="0.00", width=110, height=32)
        self.ent_brokerage.insert(0, "0.00")
        self.ent_brokerage.pack(side="left")
        self.ent_brokerage.bind("<KeyRelease>", lambda e: self._recalc_totals())

        action_box = ctk.CTkFrame(last_row, fg_color="transparent")
        action_box.pack(side="right", padx=14, pady=8)

        self.lbl_net_summary = ctk.CTkLabel(
            action_box, text="Total: ₹ 0.00",
            font=("Segoe UI", 13, "bold"), text_color="#38bdf8"
        )
        self.lbl_net_summary.pack(side="left", padx=(0, 16))

        ctk.CTkButton(
            action_box,
            text="🚀 Purchase",
            width=140,
            height=34,
            corner_radius=6,
            fg_color="#059669",
            hover_color="#047857",
            font=("Segoe UI", 12, "bold"),
            command=self._submit_purchase
        ).pack(side="left")

        # 2. Form Title
        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.pack(side="top", fill="x", pady=(2, 10))

        ctk.CTkLabel(
            title_row,
            text="Stock & ETF Purchase Order",
            font=("Segoe UI", 16, "bold"),
            text_color="#38bdf8"
        ).pack(side="left")

        # 3. Main Workspace
        row3_container = ctk.CTkFrame(self, fg_color="transparent")
        row3_container.pack(side="top", fill="both", expand=True, pady=(0, 6))

        row3_top = ctk.CTkFrame(row3_container, fg_color="transparent")
        row3_top.pack(fill="x", pady=(0, 8))

        date_box = ctk.CTkFrame(row3_top, fg_color="transparent")
        date_box.pack(side="left")
        ctk.CTkLabel(date_box, text="Date:", font=("Segoe UI", 12, "bold"), text_color="#94a3b8").pack(side="left", padx=(0, 6))
        self.ent_date = ctk.CTkEntry(date_box, width=130, height=32)
        self.ent_date.insert(0, date.today().strftime("%Y-%m-%d"))
        self.ent_date.pack(side="left")
        attach_calendar_picker(self.ent_date)
        
        ctk.CTkButton(
            row3_top,
            text="➕ Add Share",
            width=120,
            height=32,
            corner_radius=6,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 11, "bold"),
            command=self._add_share_row
        ).pack(side="right")

        # 🌟 Column Headers (Bonus Issue column added)
        tbl_hdr = ctk.CTkFrame(row3_container, fg_color="#1e293b", corner_radius=6, height=30)
        tbl_hdr.pack(fill="x", pady=(0, 4))
        tbl_hdr.pack_propagate(False)

        ctk.CTkLabel(tbl_hdr, text="Stock / ETF Symbol (Auto Search)", width=220, anchor="w", font=("Segoe UI", 11, "bold"), text_color="#94a3b8").pack(side="left", padx=(10, 4))
        ctk.CTkLabel(tbl_hdr, text="Bonus Issue", width=90, anchor="center", font=("Segoe UI", 11, "bold"), text_color="#38bdf8").pack(side="left", padx=4)
        ctk.CTkLabel(tbl_hdr, text="Quantity", width=95, anchor="w", font=("Segoe UI", 11, "bold"), text_color="#94a3b8").pack(side="left", padx=4)
        ctk.CTkLabel(tbl_hdr, text="Buy Price (₹)", width=105, anchor="w", font=("Segoe UI", 11, "bold"), text_color="#94a3b8").pack(side="left", padx=4)
        ctk.CTkLabel(tbl_hdr, text="Total Amount (₹)", width=115, anchor="w", font=("Segoe UI", 11, "bold"), text_color="#94a3b8").pack(side="left", padx=4)

        self.rows_container = ctk.CTkScrollableFrame(row3_container, fg_color="#0f172a", corner_radius=8)
        self.rows_container.pack(fill="both", expand=True)

    def _add_share_row(self):
        row_frame = ctk.CTkFrame(self.rows_container, fg_color="#1e293b", corner_radius=6)
        row_frame.pack(fill="x", pady=4, padx=4)

        # 1. Symbol Auto-Search Entry
        ent_sym = AutocompleteEntry(
            row_frame,
            symbol_list=self.active_symbols,
            placeholder_text="Symbol (e.g. BEL)",
            width=220,
            height=32
        )
        ent_sym.pack(side="left", padx=(8, 4), pady=6)

        # 🌟 2. Bonus Issue Checkbox
        chk_bonus = ctk.CTkCheckBox(
            row_frame,
            text="Bonus",
            width=90,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=4,
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#38bdf8",
            font=("Segoe UI", 11, "bold")
        )
        chk_bonus.pack(side="left", padx=4, pady=6)

        # 3. Quantity Input Box
        ent_qty = ctk.CTkEntry(row_frame, placeholder_text="Qty", width=95, height=32)
        ent_qty.pack(side="left", padx=4, pady=6)

        # 4. Price Input Box
        ent_price = ctk.CTkEntry(row_frame, placeholder_text="Price (₹)", width=105, height=32)
        ent_price.pack(side="left", padx=4, pady=6)

        # 5. Total Amount Display
        lbl_row_tot = ctk.CTkLabel(
            row_frame, text="₹ 0.00", width=115, anchor="w",
            font=("Segoe UI", 11, "bold"), text_color="#22c55e"
        )
        lbl_row_tot.pack(side="left", padx=4, pady=6)

        def on_toggle_bonus():
            if chk_bonus.get() == 1:
                ent_price.configure(state="normal")
                ent_price.delete(0, tk.END)
                ent_price.insert(0, "0.00")
                ent_price.configure(state="disabled")
            else:
                ent_price.configure(state="normal")
                ent_price.delete(0, tk.END)
                ent_price.insert(0, "")
            update_row_tot()

        chk_bonus.configure(command=on_toggle_bonus)

        def update_row_tot(event=None):
            try:
                q = int(ent_qty.get().strip() or "0")
                if chk_bonus.get() == 1:
                    p = 0.0
                else:
                    p = float(ent_price.get().strip() or "0")
                lbl_row_tot.configure(text=f"₹ {q * p:,.2f}")
            except Exception:
                lbl_row_tot.configure(text="₹ 0.00")
            self._recalc_totals()

        ent_qty.bind("<KeyRelease>", update_row_tot)
        ent_price.bind("<KeyRelease>", update_row_tot)

        # Remove Row Button
        def remove_row():
            if len(self.share_rows) <= 1:
                if self.notify:
                    self.notify("Kam se kam ek share row hona zaroori hai!", "warning")
                return
            row_frame.destroy()
            for item in self.share_rows:
                if item["frame"] == row_frame:
                    self.share_rows.remove(item)
                    break
            self._recalc_totals()

        btn_del = ctk.CTkButton(
            row_frame, text="❌", width=34, height=30,
            fg_color="#7f1d1d", hover_color="#991b1b", font=("Segoe UI", 11, "bold"),
            command=remove_row
        )
        btn_del.pack(side="right", padx=8, pady=6)

        self.share_rows.append({
            "frame": row_frame,
            "sym": ent_sym,
            "chk_bonus": chk_bonus,
            "qty": ent_qty,
            "price": ent_price,
            "row_tot": lbl_row_tot
        })

    def _recalc_totals(self):
        subtotal = 0.0
        for r in self.share_rows:
            try:
                q = int(r["qty"].get().strip() or "0")
                if r["chk_bonus"].get() == 1:
                    p = 0.0
                else:
                    p = float(r["price"].get().strip() or "0")
                subtotal += (q * p)
            except Exception:
                pass

        try:
            brok = float(self.ent_brokerage.get().strip() or "0")
        except Exception:
            brok = 0.0

        grand_total = subtotal + brok
        self.lbl_net_summary.configure(text=f"Total: ₹ {grand_total:,.2f}")

    def _submit_purchase(self):
        uid = self._get_user_id()
        if not uid:
            if self.notify:
                self.notify("User session invalid ya expired hai!", "error")
            return

        date_str = self.ent_date.get().strip()
        try:
            valid_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            if self.notify:
                self.notify("Date format galat hai! Kripya YYYY-MM-DD daalein.", "error")
            return

        ok_brok, brokerage = FormValidator.is_positive_number(self.ent_brokerage.get() or "0", "Total Brokerage")
        if not ok_brok:
            brokerage = 0.0

        items = []
        for idx, r in enumerate(self.share_rows, start=1):
            raw_sym = r["sym"].get().strip().upper()
            if not raw_sym:
                if self.notify: self.notify(f"Row {idx}: Symbol required!", "error"); return

            ok_qty, qty = FormValidator.is_positive_int(r["qty"].get(), f"Row {idx} Qty")
            if not ok_qty:
                if self.notify: self.notify(qty, "error"); return

            is_bonus = (r["chk_bonus"].get() == 1)

            # 🌟 POINT 1: Bonus hone par price 0.00 aur Particular mein "+ Bonus"
            if is_bonus:
                price = 0.0
                save_sym = f"{raw_sym} + Bonus"
                amount = 0.0
            else:
                ok_prc, price = FormValidator.is_positive_number(r["price"].get(), f"Row {idx} Price")
                if not ok_prc:
                    if self.notify: self.notify(price, "error"); return
                save_sym = raw_sym
                amount = round(qty * price, 2)

            items.append({
                "symbol": save_sym,
                "qty": qty,
                "price": price,
                "amount": amount
            })

        success, msg = self.db.execute_purchase(uid, items, brokerage, tran_date=valid_date)
        if self.notify:
            self.notify(msg, "success" if success else "error")

        if success:
            for r in self.share_rows[1:]:
                r["frame"].destroy()
            self.share_rows = self.share_rows[:1]
            first = self.share_rows[0]
            first["sym"].delete(0, tk.END)
            first["chk_bonus"].deselect()
            first["qty"].delete(0, tk.END)
            first["price"].configure(state="normal")
            first["price"].delete(0, tk.END)
            first["row_tot"].configure(text="₹ 0.00")
            self.ent_brokerage.delete(0, tk.END)
            self.ent_brokerage.insert(0, "0.00")
            self._recalc_totals()

            if hasattr(self.master, "holdings_view"):
                self.master.holdings_view.invalidate_cache()
            elif hasattr(self, "notify") and hasattr(self.master.master, "holdings_view"):
                self.master.master.holdings_view.invalidate_cache()
