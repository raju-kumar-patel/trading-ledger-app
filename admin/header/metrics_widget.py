import customtkinter as ctk

class HeaderMetricsWidget(ctk.CTkFrame):
    def __init__(self, master, on_navigate=None):
        super().__init__(master, fg_color="transparent")
        self.on_navigate = on_navigate
        self.cards = {}
        self.active_tab = "users"
        
        self.is_enabled = True  # 🌟 Connection state flag
        
        self._build_ui()

    def _build_ui(self):
        # 1. Users Card (Default Active)
        self.card_users = self._create_card("users", "👥 Users Overview", "0 Active", "Total Users: 0", "#38bdf8")
        self.card_users.grid(row=0, column=0, padx=6, sticky="ew")

        # 2. Stocks Tables Card
        self.card_stocks = self._create_card("stocks", "📊 Active Stocks", "0 Tables", "NSE Equities Tracked", "#22c55e")
        self.card_stocks.grid(row=0, column=1, padx=6, sticky="ew")

        # 3. ETFs Tables Card
        self.card_etfs = self._create_card("etfs", "🪙 Active ETFs", "0 Tables", "ETF Products Tracked", "#f59e0b")
        self.card_etfs.grid(row=0, column=2, padx=6, sticky="ew")

        # 4. System Status Card
        self.card_status = self._create_card("system", "⚡ System / Sync", "Healthy", "Last Sync: Never", "#a855f7")
        self.card_status.grid(row=0, column=3, padx=6, sticky="ew")

        self.columnconfigure((0, 1, 2, 3), weight=1)
        self.set_active_card("users")

    def _create_card(self, tab_key, title, main_val, sub_val, color):
        card = ctk.CTkFrame(
            self, 
            fg_color="#1e293b", 
            corner_radius=10, 
            height=85,
            border_width=2,
            border_color="#1e293b",
            cursor="hand2"
        )
        card.pack_propagate(False)

        top_lbl = ctk.CTkLabel(card, text=title, font=("Segoe UI", 11, "bold"), text_color="#94a3b8", cursor="hand2")
        top_lbl.pack(anchor="w", padx=14, pady=(8, 1))

        main_lbl = ctk.CTkLabel(card, text=main_val, font=("Segoe UI", 18, "bold"), text_color=color, cursor="hand2")
        main_lbl.pack(anchor="w", padx=14)

        sub_lbl = ctk.CTkLabel(card, text=sub_val, font=("Segoe UI", 10), text_color="#64748b", cursor="hand2")
        sub_lbl.pack(anchor="w", padx=14, pady=(0, 6))

        card.main_lbl = main_lbl
        card.sub_lbl = sub_lbl
        card.tab_key = tab_key
        card.theme_color = color

        # Click event handlers
        def on_click(event=None):
			# Offline hone par click block karega
            if not self.is_enabled:
                return
            self.set_active_card(tab_key)
            if self.on_navigate:
                self.on_navigate(tab_key)

        def on_enter(event=None):
            if self.is_enabled and self.active_tab != tab_key:
                card.configure(fg_color="#27354a")

        def on_leave(event=None):
            if self.active_tab != tab_key:
                card.configure(fg_color="#1e293b")

        # Bind clicks & hover to container and child labels
        for widget in (card, top_lbl, main_lbl, sub_lbl):
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        self.cards[tab_key] = card
        return card

    def set_active_card(self, tab_key):
        self.active_tab = tab_key
        for key, card in self.cards.items():
            if key == tab_key:
                card.configure(border_color=card.theme_color, fg_color="#243248")
            else:
                card.configure(border_color="#1e293b", fg_color="#1e293b")

    def update_metrics(self, active_users, total_users, stocks_count, etfs_count, last_sync=None):
        self.card_users.main_lbl.configure(text=f"{active_users} Active")
        self.card_users.sub_lbl.configure(text=f"Total Users: {total_users}")
        self.card_stocks.main_lbl.configure(text=f"{stocks_count} Tables")
        self.card_etfs.main_lbl.configure(text=f"{etfs_count} Tables")
        if last_sync:
            self.card_status.sub_lbl.configure(text=f"Last Sync: {last_sync}")
            
    def set_enabled(self, enabled: bool):
        self.is_enabled = enabled
        cursor_type = "hand2" if enabled else "arrow"
        for card in self.cards.values():
            card.configure(cursor=cursor_type)
            for child in card.winfo_children():
                try:
                    child.configure(cursor=cursor_type)
                except Exception:
                    pass

        if not enabled:
            card.configure(border_color="#334155")
        elif card.tab_key == self.active_tab:
            card.configure(border_color=card.theme_color)
        else:
            card.configure(border_color="#1e293b")
	
