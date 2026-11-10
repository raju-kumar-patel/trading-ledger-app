import customtkinter as ctk
from user.body.user_forms.form_purchase import FormPurchase
from user.body.user_forms.form_sell import FormSell
from user.body.user_forms.form_deposit import FormDeposit
from user.body.user_forms.form_withdraw import FormWithdraw


class AddEntryContainer(ctk.CTkFrame):
    def __init__(self, master, user_info=None, notify_callback=None, on_back=None):
        super().__init__(master, fg_color="transparent")
        self.user_info = user_info or {}
        self.notify = notify_callback
        self.on_back = on_back
        
        self._build_ui()

    def _build_ui(self):
        # =====================================================================
        # 1. TOP ROW: Clean Back Button (No Border) + Sub-Navigation Tabs
        # =====================================================================
        top_row = ctk.CTkFrame(self, fg_color="transparent", height=42)
        top_row.pack(fill="x", pady=(0, 10))
        top_row.pack_propagate(False)

        # Clean Back Arrow Button (Border-less)
        btn_back = ctk.CTkButton(
            top_row,
            text="⬅",
            width=38,
            height=34,
            corner_radius=6,
            border_width=0,
            fg_color="transparent",
            hover_color="#1e293b",
            text_color="#38bdf8",
            font=("Segoe UI", 18, "bold"),
            command=self.on_back if self.on_back else lambda: None
        )
        btn_back.pack(side="left", padx=(0, 14))

        # Same Row: Purchase, Sell, Deposit, Withdraw Buttons
        self.sub_buttons = {}
        forms_config = [
            ("PURCHASE", "🛒 Purchase"),
            ("SELL", "📉 Sell"),
            ("DEPOSIT", "➕ Deposit"),
            ("WITHDRAW", "📤 Withdraw")
        ]

        for key, text in forms_config:
            btn = ctk.CTkButton(
                top_row,
                text=text,
                width=120,
                height=34,
                corner_radius=8,
                border_width=0,
                fg_color="#1e293b",
                hover_color="#334155",
                font=("Segoe UI", 12, "bold"),
                command=lambda k=key: self.switch_form(k)
            )
            btn.pack(side="left", padx=(0, 8))
            self.sub_buttons[key] = btn

        # Form Display Workspace
        self.form_workspace = ctk.CTkFrame(self, fg_color="transparent")
        self.form_workspace.pack(fill="both", expand=True)

        self.forms = {
            "PURCHASE": FormPurchase(self.form_workspace, user_info=self.user_info, notify_callback=self.notify),
            "SELL": FormSell(self.form_workspace, user_info=self.user_info, notify_callback=self.notify),
            "DEPOSIT": FormDeposit(self.form_workspace, user_info=self.user_info, notify_callback=self.notify),
            "WITHDRAW": FormWithdraw(self.form_workspace, user_info=self.user_info, notify_callback=self.notify)
        }

        self.switch_form("PURCHASE")

    def switch_form(self, form_key: str):
        for k, btn in self.sub_buttons.items():
            if k == form_key:
                active_color = "#0284c7" if form_key != "PURCHASE" else "#0284c7"
                btn.configure(fg_color=active_color, text_color="#ffffff")
            else:
                btn.configure(fg_color="#1e293b", text_color="#94a3b8")

        for f in self.forms.values():
            f.pack_forget()

        target = self.forms.get(form_key)
        if target:
            target.pack(fill="both", expand=True)
