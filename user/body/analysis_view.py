import threading
from tkinter import ttk
import customtkinter as ctk
from database.DBCore import DBCore


class AnalysisView(ctk.CTkFrame):
    def __init__(self, master, db_core=None, notify_callback=None, tree_style="UserBody.Treeview"):
        super().__init__(master, fg_color="transparent")
        self.db = db_core or DBCore
        self.notify = notify_callback
        self.tree_style = tree_style
        self._analysis_cache = None

        self._build_ui()

    def _build_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=6, pady=(4, 8))

        ctk.CTkLabel(
            top_bar, text="📊 Wilder 14-Day RSI Technical Analysis",
            font=("Segoe UI", 14, "bold"), text_color="#38bdf8"
        ).pack(side="left")

        ctk.CTkButton(
            top_bar, text="🔄 Refresh Analysis", width=130, height=28,
            fg_color="#334155", hover_color="#475569",
            command=lambda: self.load_data(force_refresh=True)
        ).pack(side="right")

        cols = ("sno", "symbol", "type", "date", "close", "rsi", "zone")
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            container, columns=cols, show="headings",
            style=self.tree_style, selectmode="browse"
        )
        
        headings = [
            ("sno", "S.No.", 55), ("symbol", "Symbol", 160),
            ("type", "Instrument", 100), ("date", "Trade Date", 120),
            ("close", "Close Price (Rs.)", 140), ("rsi", "14-Day RSI", 120),
            ("zone", "Signal Zone", 150)
        ]
        for col_id, title, width in headings:
            self.tree.heading(col_id, text=title, anchor="w")
            self.tree.column(col_id, width=width, anchor="w")

        self.tree.tag_configure("OVERSOLD", foreground="#22c55e")
        self.tree.tag_configure("OVERBOUGHT", foreground="#ef4444")
        self.tree.tag_configure("NEUTRAL", foreground="#e2e8f0")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)

    def load_data(self, force_refresh=False):
        if self._analysis_cache is not None and not force_refresh:
            self._render_tree(self._analysis_cache)
            return

        if self.notify:
            self.notify("Loading RSI Analysis data from database...", "info")
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        rows = []
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT symbol, instrument_type, table_name 
                        FROM admin_symbol_registry 
                        WHERE COALESCE(status, 'ACTIVE') = 'ACTIVE'
                        ORDER BY symbol ASC;
                    """)
                    registry = cur.fetchall()

                    for sym, inst_type, tbl in registry:
                        try:
                            cur.execute(f"""
                                SELECT "date", close_price, rsi 
                                FROM {tbl} 
                                ORDER BY "date" DESC 
                                LIMIT 1;
                            """)
                            r = cur.fetchone()
                            if r:
                                rows.append((sym, inst_type, str(r[0]), float(r[1] or 0), float(r[2] or 0)))
                        except Exception:
                            conn.rollback()
                            continue

            self._analysis_cache = rows
            if self.winfo_exists():
                self.after(0, self._render_tree, rows)
        except Exception as e:
            if self.winfo_exists() and self.notify:
                self.after(0, lambda: self.notify(f"Analysis load error: {e}", "error"))

    def _render_tree(self, rows: list):
        if not self.winfo_exists():
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, (sym, inst_type, dt_str, close_val, rsi_val) in enumerate(rows, start=1):
            if rsi_val <= 0:
                zone, tag = "⏳ Pending", "NEUTRAL"
            elif rsi_val < 30:
                zone, tag = "🟢 Oversold (<30)", "OVERSOLD"
            elif rsi_val > 70:
                zone, tag = "🔴 Overbought (>70)", "OVERBOUGHT"
            else:
                zone, tag = "⚪ Neutral", "NEUTRAL"

            self.tree.insert(
                "", "end",
                values=(idx, sym, inst_type, dt_str, f"Rs. {close_val:.2f}", f"{rsi_val:.2f}", zone),
                tags=(tag,)
            )

        if self.notify:
            self.notify(f"Analysis updated ({len(rows)} active symbols).", "success")
