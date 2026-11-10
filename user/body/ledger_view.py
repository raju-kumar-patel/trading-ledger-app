import threading
from tkinter import ttk
import customtkinter as ctk
from database.DBCore import DBCore
from user.user_db import UserDatabase


class LedgerView(ctk.CTkFrame):
    def __init__(self, master, db_core=None, user_info=None, notify_callback=None, tree_style="UserBody.Treeview"):
        super().__init__(master, fg_color="transparent")
        self.db = db_core or DBCore
        self.user_info = user_info or {}
        self.notify = notify_callback
        self.tree_style = tree_style

        self.user_db = UserDatabase(self.db)
        self._all_records = []

        self._build_ui()
        self.load_data()

    def _get_user_id(self):
        return self.user_info.get("id") or self.user_info.get("user_id")

    def _build_ui(self):
        # 1. Top Action Toolbar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=6, pady=(4, 8))

        ctk.CTkLabel(
            top_bar, text="📒 Account Financial Ledger",
            font=("Segoe UI", 15, "bold"), text_color="#38bdf8"
        ).pack(side="left")

        # Right Action Buttons & Search
        self.btn_refresh = ctk.CTkButton(
            top_bar, text="🔄 Reload", width=90, height=32,
            fg_color="#334155", hover_color="#475569",
            command=self.load_data
        )
        self.btn_refresh.pack(side="right", padx=(8, 0))

        self.ent_search = ctk.CTkEntry(
            top_bar, placeholder_text="🔍 Search Particulars...", width=200, height=32
        )
        self.ent_search.pack(side="right")
        self.ent_search.bind("<KeyRelease>", self._on_filter)

        # 2. Summary Mini-Cards (Total Credits, Debits, Closing Balance)
        summary_bar = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=8, height=42)
        summary_bar.pack(fill="x", padx=6, pady=(0, 8))
        summary_bar.pack_propagate(False)

        self.lbl_total_credit = ctk.CTkLabel(
            summary_bar, text="Total Credit: ₹ 0.00",
            font=("Segoe UI", 11, "bold"), text_color="#22c55e"
        )
        self.lbl_total_credit.pack(side="left", padx=14)

        self.lbl_total_debit = ctk.CTkLabel(
            summary_bar, text="Total Debit: ₹ 0.00",
            font=("Segoe UI", 11, "bold"), text_color="#ef4444"
        )
        self.lbl_total_debit.pack(side="left", padx=14)

        self.lbl_net_bal = ctk.CTkLabel(
            summary_bar, text="Closing Balance: ₹ 0.00",
            font=("Segoe UI", 11, "bold"), text_color="#38bdf8"
        )
        self.lbl_net_bal.pack(side="right", padx=14)

        # 3. Main Ledger Table Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)

        cols = ("sno", "date", "particulars", "type", "debit", "credit", "balance")
        self.tree = ttk.Treeview(
            container, columns=cols, show="headings",
            style=self.tree_style, selectmode="browse"
        )
        
        headings = [
            ("sno", "S.No.", 55),
            ("date", "Tran Date", 110),
            ("particulars", "Particulars", 260),
            ("type", "Type", 95),
            ("debit", "Debit (₹)", 125),
            ("credit", "Credit (₹)", 125),
            ("balance", "Net Balance (₹)", 140)
        ]
        for col_id, title, width in headings:
            self.tree.heading(col_id, text=title, anchor="w")
            self.tree.column(col_id, width=width, anchor="w")

        # Color Tags: Credit ke liye Green, Debit ke liye Red
        self.tree.tag_configure("CREDIT_ROW", foreground="#22c55e")
        self.tree.tag_configure("DEBIT_ROW", foreground="#f87171")
        self.tree.tag_configure("NORMAL_ROW", foreground="#f3f4f6")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)

    # =========================================================================
    # Data Loading & Rendering
    # =========================================================================
    def load_data(self):
        uid = self._get_user_id()
        if not uid:
            return

        self.btn_refresh.configure(state="disabled")
        if self.notify:
            self.notify("Ledger records fetch ho rahe hain...", "info")

        threading.Thread(target=self._fetch_worker, args=(uid,), daemon=True).start()

    def _fetch_worker(self, uid: str):
        records = self.user_db.get_user_ledger(uid)
        if self.winfo_exists():
            self.after(0, self._on_data_loaded, records)

    def _on_data_loaded(self, records: list[dict]):
        if not self.winfo_exists():
            return

        self.btn_refresh.configure(state="normal")
        self._all_records = records
        self._render_rows(records)

        if self.notify:
            self.notify(f"Ledger loaded ({len(records)} transactions).", "success")

    def _render_rows(self, records: list[dict]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        tot_debit = 0.0
        tot_credit = 0.0
        latest_bal = 0.0

        if records:
            latest_bal = records[0]["balance"]

        search_q = self.ent_search.get().strip().lower()

        idx = 1
        for r in records:
            tot_debit += r["debit"]
            tot_credit += r["credit"]

            # Filter check
            if search_q and (search_q not in r["particulars"].lower() and search_q not in r["type"].lower()):
                continue

            deb_str = f"₹ {r['debit']:,.2f}" if r["debit"] > 0 else "—"
            crd_str = f"₹ {r['credit']:,.2f}" if r["credit"] > 0 else "—"
            bal_str = f"₹ {r['balance']:,.2f}"

            # Tag determination
            if r["credit"] > 0 and r["debit"] == 0:
                tag = "CREDIT_ROW"
            elif r["debit"] > 0 and r["credit"] == 0:
                tag = "DEBIT_ROW"
            else:
                tag = "NORMAL_ROW"

            self.tree.insert(
                "", "end",
                values=(
                    idx,
                    r["date"],
                    r["particulars"],
                    r["type"],
                    deb_str,
                    crd_str,
                    bal_str
                ),
                tags=(tag,)
            )
            idx += 1

        # Summary figures update
        self.lbl_total_credit.configure(text=f"Total Credit: ₹ {tot_credit:,.2f}")
        self.lbl_total_debit.configure(text=f"Total Debit: ₹ {tot_debit:,.2f}")
        self.lbl_net_bal.configure(text=f"Closing Balance: ₹ {latest_bal:,.2f}")

    def _on_filter(self, event=None):
        if hasattr(self, "_all_records"):
            self._render_rows(self._all_records)
