import threading
import tkinter as tk
import customtkinter as ctk
from database.DBCore import DBCore
from user.user_db import UserDatabase
from theme.theme import Theme
from user.body.user_watchlist_db import UserWatchlistDB
try:
    from user.body.components.sparkline_graph import SparklineGraph
except ModuleNotFoundError:
    from sparkline_graph import SparklineGraph

try:
    from services.nse_fetcher_nseindia import NSEDataFetcher
except ModuleNotFoundError:
    from nse_fetcher_nseindia import NSEDataFetcher

class WatchlistSearchEntry(ctk.CTkEntry):
    """Auto-suggest search box component"""
    def __init__(self, master, symbol_list=None, on_select_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.symbol_list = symbol_list or []
        self.on_select = on_select_callback
        self._listbox_window = None

        self.bind("<KeyRelease>", self._on_keyrelease)
        self.bind("<FocusOut>", self._on_focus_out)

    def set_symbols(self, symbols: list[str]):
        self.symbol_list = symbols

    def _on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return

        typed = self.get().strip().upper()
        if not typed:
            self._close_listbox()
            return

        matches = [s for s in self.symbol_list if typed in s][:8]
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
                bg=Theme.BG_ELEVATED,
                fg=Theme.TEXT_PRIMARY,
                selectbackground=Theme.BRAND_BLUE,
                selectforeground="#ffffff",
                font=(Theme.FONT_FAMILY, 10, "bold"),
                borderwidth=1,
                relief="solid",
                highlightthickness=0
            )
            self._lb.pack(fill="both", expand=True)
            self._lb.bind("<<ListboxSelect>>", self._on_select_item)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        w = self.winfo_width()
        h = min(len(matches) * 26 + 6, 180)
        self._listbox_window.geometry(f"{w}x{h}+{x}+{y}")

        self._lb.delete(0, tk.END)
        for item in matches:
            self._lb.insert(tk.END, item)

    def _on_select_item(self, event=None):
        if self._listbox_window and self._lb.curselection():
            selected = self._lb.get(self._lb.curselection()[0])
            self.delete(0, tk.END)
            self._close_listbox()
            if self.on_select:
                self.on_select(selected)

    def _on_focus_out(self, event=None):
        self.after(200, self._close_listbox)

    def _close_listbox(self):
        if self._listbox_window:
            self._listbox_window.destroy()
            self._listbox_window = None


class WatchlistView(ctk.CTkFrame):
    """Pure Watchlist Presentation View (Clean UI Layer)"""
    def __init__(self, master, db_core=None, user_info=None, notify_callback=None, **kwargs):
        super().__init__(master, fg_color=Theme.BG_ROOT, **kwargs)
        self.user_info = user_info or {}
        self.notify = notify_callback
        
        # 🌟 Service DB & Logic Layer
        self.watchlist_service = UserWatchlistDB(db_core)

        self._build_ui()
        self.load_data()

    def _get_user_id(self):
        return self.user_info.get("id") or self.user_info.get("user_id")

    def _build_ui(self):
        # 1. Top Search Header Card
        top_card = ctk.CTkFrame(
            self,
            fg_color=Theme.BG_CARD,
            corner_radius=Theme.RADIUS_CARD,
            border_width=1,
            border_color=Theme.BORDER_SUBTLE
        )
        top_card.pack(fill="x", padx=4, pady=(4, 10))

        ctk.CTkLabel(
            top_card,
            text="⭐ WATCHLIST",
            font=(Theme.FONT_FAMILY, 11, "bold"),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor="w", padx=14, pady=(10, 2))

        # Search Auto-Complete Input
        active_symbols = self.watchlist_service.get_active_registry_symbols()
        self.search_entry = WatchlistSearchEntry(
            top_card,
            symbol_list=active_symbols,
            on_select_callback=self._handle_add_symbol,
            placeholder_text="🔍 Search stock or ETF to add (e.g. BEL, NIFTYBEES)...",
            height=38,
            corner_radius=8,
            fg_color=Theme.BG_INPUT,
            border_width=1,
            border_color=Theme.BORDER_LIGHT,
            text_color=Theme.TEXT_PRIMARY
        )
        self.search_entry.pack(fill="x", padx=12, pady=(0, 12))

        # 2. Watchlist Cards Container
        self.cards_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cards_container.pack(fill="both", expand=True, padx=2, pady=0)

    def load_data(self):
        """Background thread par service layer se structured market data fetch karna"""
        uid = self._get_user_id()
        if not uid:
            return

        threading.Thread(target=self._worker_fetch, args=(uid,), daemon=True).start()

    def _worker_fetch(self, uid: str):
        # Service call to fetch parsed data
        cards_data = self.watchlist_service.get_watchlist_market_data(uid)
        if self.winfo_exists():
            self.after(0, lambda: self._render_ui(cards_data))

    def _render_ui(self, cards_data: list[dict]):
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        if not cards_data:
            empty_box = ctk.CTkFrame(self.cards_container, fg_color=Theme.BG_CARD, corner_radius=12)
            empty_box.pack(fill="x", pady=20, padx=10)
            ctk.CTkLabel(
                empty_box,
                text="Aapki Watchlist khali hai.\nUpar search bar se share add karein.",
                font=(Theme.FONT_FAMILY, 12),
                text_color=Theme.TEXT_MUTED
            ).pack(pady=30)
            return

        for item in cards_data:
            sym = item["symbol"]
            ltp = item["ltp"]
            pct = item["change_pct"]
            spark_pts = item["spark_points"]

            is_green = pct >= 0
            pnl_col = Theme.GREEN_BUY if is_green else Theme.RED_SELL
            pnl_arrow = "▲" if is_green else "▼"

            # Mobile Tile Row
            row = ctk.CTkFrame(
                self.cards_container,
                fg_color=Theme.BG_CARD,
                corner_radius=10,
                height=56,
                border_width=1,
                border_color=Theme.BORDER_SUBTLE
            )
            row.pack(fill="x", pady=3, padx=2)
            row.pack_propagate(False)

            # Left: Symbol Title
            left_col = ctk.CTkFrame(row, fg_color="transparent")
            left_col.pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(
                left_col, text=sym,
                font=(Theme.FONT_FAMILY, 13, "bold"), text_color=Theme.TEXT_PRIMARY
            ).pack(anchor="w")
            ctk.CTkLabel(
                left_col, text="NSE EQ",
                font=(Theme.FONT_FAMILY, 9), text_color=Theme.TEXT_MUTED
            ).pack(anchor="w")

            # Center: 1-Week Graph Component
            graph = SparklineGraph(row, width=110, height=34)
            graph.pack(side="left", padx=10, pady=8)
            graph.draw_chart(spark_pts)

            # Right: Remove Button
            btn_del = ctk.CTkButton(
                row, text="❌", width=30, height=30,
                corner_radius=6,
                fg_color="transparent",
                hover_color=Theme.BG_HOVER,
                text_color=Theme.TEXT_MUTED,
                font=(Theme.FONT_FAMILY, 10),
                command=lambda s=sym: self._handle_remove_symbol(s)
            )
            btn_del.pack(side="right", padx=(4, 10), pady=12)

            # Center-Right: Price & 1-Day Return
            price_col = ctk.CTkFrame(row, fg_color="transparent")
            price_col.pack(side="right", padx=6, pady=8)
            ctk.CTkLabel(
                price_col, text=f"₹ {ltp:,.2f}",
                font=(Theme.FONT_FAMILY, 13, "bold"), text_color=Theme.TEXT_PRIMARY
            ).pack(anchor="e")
            ctk.CTkLabel(
                price_col, text=f"{pnl_arrow} {abs(pct):.2f}%",
                font=(Theme.FONT_FAMILY, 10, "bold"), text_color=pnl_col
            ).pack(anchor="e")

    def _handle_add_symbol(self, symbol: str):
        uid = self._get_user_id()
        ok, msg = self.watchlist_service.add_symbol(uid, symbol)
        if self.notify:
            self.notify(msg, "success" if ok else "error")
        if ok:
            self.load_data()

    def _handle_remove_symbol(self, symbol: str):
        uid = self._get_user_id()
        ok, msg = self.watchlist_service.remove_symbol(uid, symbol)
        if self.notify:
            self.notify(msg, "info" if ok else "error")
        if ok:
            self.load_data()
