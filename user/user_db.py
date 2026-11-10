from datetime import date, datetime
from database.DBCore import DBCore


class UserDatabase:
    def __init__(self, db_core=None):
        self.db = db_core or DBCore

    # =========================================================================
    # BALANCE
    # =========================================================================
    def get_user_balance(self, user_id: str) -> float:
        """User ke transactions table se latest balance_amount nikaalta hai"""
        if not user_id:
            return 0.0
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT balance_amount 
                        FROM transactions 
                        WHERE user_id = %s 
                        ORDER BY tran_date DESC, created_at DESC, id DESC 
                        LIMIT 1;
                    """, (user_id,))
                    row = cur.fetchone()
                    return float(row[0]) if (row and row[0] is not None) else 0.0
        except Exception as e:
            print(f"⚠️ [UserDatabase.get_user_balance Error]: {e}")
            return 0.0

    # =========================================================================
    # ACTIVE SYMBOLS
    # =========================================================================
    def get_active_symbols(self) -> list[str]:
        """Auto-complete ke liye admin_symbol_registry se sabhi active symbols lata hai"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT symbol 
                        FROM admin_symbol_registry 
                        WHERE COALESCE(status, 'ACTIVE') = 'ACTIVE' 
                        ORDER BY symbol ASC;
                    """)
                    rows = cur.fetchall()
                    return [r[0].strip().upper() for r in rows if r[0]]
        except Exception as e:
            print(f"⚠️ [UserDatabase.get_active_symbols Error]: {e}")
            return []

    # =========================================================================
    # 🌟 POINT 1: PURCHASE & BONUS SHARES
    # =========================================================================
    def execute_purchase(self, user_id: str, items: list[dict], total_brokerage: float = 0.0, tran_date=None) -> tuple[bool, str]:
        if not user_id or not items:
            return False, "User ID ya purchase items missing hain!"

        tx_date = tran_date if tran_date else date.today()

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    # Total purchase cost calculate karein (Bonus shares ka price 0.0 hoga)
                    total_purchase_val = sum(float(item.get("price", 0.0)) * int(item.get("qty", 0)) for item in items)
                    total_required_cost = total_purchase_val + float(total_brokerage)

                    # Latest balance lock ke sath fetch karein
                    cur.execute(
                        "SELECT balance_amount FROM transactions WHERE user_id = %s ORDER BY tran_date DESC, created_at DESC, id DESC LIMIT 1 FOR UPDATE;",
                        [user_id]
                    )
                    last_row = cur.fetchone()
                    current_balance = float(last_row[0]) if (last_row and last_row[0] is not None) else 0.0

                    # Agar paise kam hain (sirf tab jab required cost > 0 ho)
                    if total_required_cost > 0 and current_balance < total_required_cost:
                        return False, f"Insufficient balance! Required: ₹{total_required_cost:,.2f}, Available: ₹{current_balance:,.2f}"

                    running_balance = current_balance

                    for item in items:
                        sym = str(item["symbol"]).strip().upper()
                        qty = int(item["qty"])
                        price = float(item.get("price", 0.0))
                        is_bonus = ("+ BONUS" in sym or "+BONUS" in sym or price == 0.0)

                        if is_bonus:
                            item_val = 0.0
                            prop_brokerage = 0.0
                            total_item_debit = 0.0
                            p_type = 'P'  # 🌟 Bonus voucher type
                        else:
                            item_val = round(qty * price, 2)
                            prop_brokerage = round((item_val / total_purchase_val) * float(total_brokerage), 2) if total_purchase_val > 0 else 0.0
                            total_item_debit = item_val + prop_brokerage
                            p_type = 'P'

                        running_balance -= total_item_debit

                        insert_query = """
                            INSERT INTO transactions (
                                user_id, tran_date, particular, tran_type,
                                purchase_qty, purchase_value, sell_qty, sell_value,
                                brokerage, credit_amount, debit_amount, balance_amount,
                                created_at, total_value
                            ) VALUES (
                                %s, %s, %s, %s,
                                %s, %s, NULL, NULL,
                                %s, NULL, %s, %s,
                                CURRENT_TIMESTAMP, %s
                            );
                        """
                        # 🌟 Fix: purchase_value column mein item_val (Total Value) save hoga, single share price nahi!
                        cur.execute(insert_query, (
                            user_id,
                            tx_date,
                            sym,
                            p_type,
                            qty,
                            item_val,          # 🌟 Corrected: Total purchase value (e.g. 404.00, Bonus mein 0.00)
                            prop_brokerage,
                            total_item_debit if total_item_debit > 0 else None,
                            running_balance,
                            item_val
                        ))

                    conn.commit()

            return True, f"Success! {len(items)} items processed. Remaining Balance: ₹{running_balance:,.2f}"

        except Exception as e:
            return False, f"Purchase error: {e}"

    # =========================================================================
    # 🌟 POINT 3: SELL WITH SEQUENTIAL DP / CDSL ENTRY
    # =========================================================================
    def execute_sell(self, user_id: str, items: list[dict], total_brokerage: float = 0.0, dp_charges: float = 0.0, tran_date=None) -> tuple[bool, str]:
        """
        1. Har stock ke sell order ko Credit karta hai (Balance add hota hai).
        2. Agar dp_charges > 0 hai, toh theek agli line par CDSL charge Debit karta hai (Balance deduct hota hai).
        Dono entries ek hi atomic transaction mein execute hoti hain.
        """
        if not user_id or not items:
            return False, "User ID ya sell items missing hain!"

        tx_date = tran_date if tran_date else date.today()

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    total_sell_val = sum(int(item["qty"]) * float(item["price"]) for item in items)

                    # Latest balance check
                    cur.execute(
                        "SELECT balance_amount FROM transactions WHERE user_id = %s ORDER BY tran_date DESC, created_at DESC, id DESC LIMIT 1 FOR UPDATE;",
                        [user_id]
                    )
                    last_row = cur.fetchone()
                    current_balance = float(last_row[0]) if (last_row and last_row[0] is not None) else 0.0

                    running_balance = current_balance

                    # 1. Main Stock Sell Entries (Line 1)
                    for item in items:
                        sym = str(item["symbol"]).strip().upper()
                        qty = int(item["qty"])
                        price = float(item["price"])
                        item_val = round(qty * price, 2)

                        prop_brokerage = round((item_val / total_sell_val) * float(total_brokerage), 2) if total_sell_val > 0 else 0.0
                        total_item_credit = round(item_val - prop_brokerage, 2)
                        running_balance += total_item_credit

                        insert_sell = """
                            INSERT INTO transactions (
                                user_id, tran_date, particular, tran_type,
                                purchase_qty, purchase_value, sell_qty, sell_value,
                                brokerage, credit_amount, debit_amount, balance_amount,
                                created_at, total_value
                            ) VALUES (
                                %s, %s, %s, 'S',
                                NULL, NULL, %s, %s,
                                %s, %s, NULL, %s,
                                CURRENT_TIMESTAMP, %s
                            );
                        """
                        cur.execute(insert_sell, (
                            user_id,
                            tx_date,
                            sym,
                            qty,
                            item_val,
                            prop_brokerage,
                            total_item_credit,
                            running_balance,
                            item_val
                        ))

                    # 2. DP / CDSL Charges Next Line Entry (Line 2)
                    if float(dp_charges) > 0:
                        dp_val = round(float(dp_charges), 2)
                        running_balance -= dp_val
                        sym_list = ", ".join([str(it["symbol"]).strip().upper() for it in items])
                        dp_narr = f"CDSL / DP Charges - {sym_list}"

                        insert_dp = """
                            INSERT INTO transactions (
                                user_id, tran_date, particular, tran_type,
                                purchase_qty, purchase_value, sell_qty, sell_value,
                                brokerage, credit_amount, debit_amount, balance_amount,
                                created_at, total_value
                            ) VALUES (
                                %s, %s, %s, 'C',
                                NULL, NULL, NULL, NULL,
                                NULL, NULL, %s, %s,
                                CURRENT_TIMESTAMP, %s
                            );
                        """
                        cur.execute(insert_dp, (
                            user_id,
                            tx_date,
                            dp_narr,
                            dp_val,
                            running_balance,
                            dp_val
                        ))

                    conn.commit()

            msg = f"Success! Sell executed (+₹{total_sell_val:,.2f})"
            if float(dp_charges) > 0:
                msg += f" and DP Charges debited (-₹{float(dp_charges):,.2f})"
            return True, f"{msg}. Final Balance: ₹{running_balance:,.2f}"

        except Exception as e:
            return False, f"Sell error: {e}"

    # =========================================================================
    # DEPOSIT
    # =========================================================================
    def execute_deposit(self, user_id: str, amount: float, narration: str, tran_date=None) -> tuple[bool, str]:
        try:
            tx_date = tran_date if tran_date else date.today()
            dep_amt = float(amount)
            if dep_amt <= 0:
                return False, "Deposit amount 0 se zyada hona chahiye!"

            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT balance_amount 
                        FROM transactions 
                        WHERE user_id = %s 
                        ORDER BY tran_date DESC, created_at DESC, id DESC 
                        LIMIT 1 
                        FOR UPDATE;
                    """, (user_id,))
                    last_row = cur.fetchone()
                    prev_balance = float(last_row[0]) if (last_row and last_row[0] is not None) else 0.0

                    new_balance = prev_balance + dep_amt

                    cur.execute("""
                        INSERT INTO transactions (
                            user_id, tran_date, particular, tran_type,
                            purchase_value, sell_qty, sell_value, brokerage,
                            credit_amount, debit_amount, balance_amount,
                            created_at, total_value
                        ) VALUES (
                            %s, %s, %s, 'D',
                            NULL, NULL, NULL, NULL,
                            %s, NULL, %s,
                            CURRENT_TIMESTAMP, %s
                        );
                    """, (
                        user_id,
                        tx_date,
                        narration.strip(),
                        dep_amt,
                        new_balance,
                        dep_amt
                    ))

                    conn.commit()

            return True, f"Successfully deposited ₹{dep_amt:,.2f}"

        except Exception as e:
            return False, f"Deposit error: {e}"

    # =========================================================================
    # 🌟 POINT 2: WITHDRAW & BROKER SETTLEMENT
    # =========================================================================
    def execute_withdraw(self, user_id: str, amount: float, narration: str, tran_date=None) -> tuple[bool, str]:
        if not user_id:
            return False, "User ID missing hai!"

        try:
            withdraw_amt = float(amount)
            if withdraw_amt <= 0:
                return False, "Withdrawal amount 0 se zyada hona chahiye!"
        except (ValueError, TypeError):
            return False, "Valid amount daalein!"

        tx_date = tran_date if tran_date else date.today()

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT balance_amount FROM transactions WHERE user_id = %s ORDER BY tran_date DESC, created_at DESC, id DESC LIMIT 1 FOR UPDATE;",
                        [user_id]
                    )
                    last_row = cur.fetchone()
                    current_bal = float(last_row[0]) if (last_row and last_row[0] is not None) else 0.0

                    if current_bal < withdraw_amt:
                        return False, f"Insufficient balance! Required: ₹{withdraw_amt:,.2f}, Available: ₹{current_bal:,.2f}"

                    new_bal = current_bal - withdraw_amt

                    # Agar settlement hai toh tran_type 'SETTLE' otherwise 'W'
                    narr_clean = narration.strip()
                    v_type = 'A' if "SETTLEMENT" in narr_clean.upper() else 'W'

                    insert_query = """
                        INSERT INTO transactions (
                            user_id, tran_date, particular, tran_type,
                            purchase_qty, purchase_value, sell_qty, sell_value,
                            brokerage, credit_amount, debit_amount, balance_amount,
                            created_at, total_value
                        ) VALUES (
                            %s, %s, %s, %s,
                            NULL, NULL, NULL, NULL,
                            NULL, NULL, %s, %s,
                            CURRENT_TIMESTAMP, %s
                        );
                    """
                    cur.execute(insert_query, (
                        user_id,
                        tx_date,
                        narr_clean,
                        v_type,
                        withdraw_amt,
                        new_bal,
                        withdraw_amt
                    ))

                    conn.commit()

            return True, f"Successfully processed ₹{withdraw_amt:,.2f}. Remaining Balance: ₹{new_bal:,.2f}"

        except Exception as e:
            return False, f"Withdrawal error: {e}"

    # =========================================================================
    # LEDGER VIEW
    # =========================================================================
    def get_user_ledger(self, user_id: str) -> list[dict]:
        if not user_id:
            return []

        def _safe_float(val) -> float:
            try:
                return float(val) if val is not None else 0.0
            except (ValueError, TypeError):
                return 0.0

        def _format_date(d_val, fallback_val) -> str:
            target = d_val if d_val else fallback_val
            if hasattr(target, "strftime"):
                return target.strftime("%Y-%m-%d")
            elif target is not None:
                return str(target)[:10]
            return "—"

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    query = f"""
                        SELECT 
                            tran_date,
                            particular,
                            COALESCE(tran_type, 'TX') AS voucher_type,
                            COALESCE(debit_amount, 0.0) AS debit,
                            COALESCE(credit_amount, 0.0) AS credit,
                            COALESCE(balance_amount, 0.0) AS balance,
                            created_at
                        FROM transactions
                        WHERE user_id = %s
                        ORDER BY tran_date DESC, created_at DESC, id DESC;
                    """
                    cur.execute(query, (user_id,))
                    rows = cur.fetchall()

                    ledger_records = []
                    for t_date, narr, v_type, deb, crd, bal, cr_at in rows:
                        ledger_records.append({
                            "date": _format_date(t_date, cr_at),
                            "particulars": str(narr),
                            "type": str(v_type).upper(),
                            "debit": _safe_float(deb),
                            "credit": _safe_float(crd),
                            "balance": _safe_float(bal)
                        })
                    return ledger_records

        except Exception as e:
            print(f"⚠️ [UserDatabase.get_user_ledger Error]: {e}")
            return []

    # =========================================================================
    # HOLDINGS (RAW TRANSACTIONS)
    # =========================================================================
    def get_raw_transactions(self, user_id: str) -> list[dict]:
        """
        HoldingsEngine ke liye transactions return karta hai.
        🌟 tran_date aur created_at bhi return hote hain taaki FIFO chronological calculation sahi ho sake.
        """
        if not user_id:
            return []

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:

                    query = f"""
                        SELECT 
                            user_id,
                            particular,
                            COALESCE(tran_type, '') AS tran_type,
                            COALESCE(purchase_qty, 0) AS purchase_qty,
                            COALESCE(purchase_value, 0.0) AS purchase_value,
                            COALESCE(sell_qty, 0) AS sell_qty,
                            COALESCE(sell_value, 0.0) AS sell_value,
                            COALESCE(credit_amount, 0.0) AS credit_amount,
                            COALESCE(debit_amount, 0.0) AS debit_amount,
                            tran_date,
                            created_at
                        FROM transactions
                        WHERE user_id = %s
                        ORDER BY tran_date ASC, created_at ASC, id ASC;
                    """
                    cur.execute(query, [user_id])
                    rows = cur.fetchall()

                    return [
                        {
                            "user_id": r[0],
                            "particular": str(r[1]).strip().upper(),
                            "tran_type": str(r[2]).strip().upper(),
                            "purchase_qty": int(r[3] or 0),
                            "purchase_value": float(r[4] or 0.0),
                            "sell_qty": int(r[5] or 0),
                            "sell_value": float(r[6] or 0.0),
                            "credit_amount": float(r[7] or 0.0),
                            "debit_amount": float(r[8] or 0.0),
                            "tran_date": r[9],
                            "created_at": r[10]
                        }
                        for r in rows
                    ]
        except Exception as e:
            print(f"⚠️ [user_db.get_raw_transactions Error]: {e}")
            return []
