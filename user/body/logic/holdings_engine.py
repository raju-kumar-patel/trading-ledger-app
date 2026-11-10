class HoldingsEngine:
    """
    Transactions data aur live CMP par Weighted Average Cost (WAC) 
    apply karke exact holdings aur P&L calculate karta hai.
    Supports: Bonus Shares (zero cost dilution), DP Charges & Settlement bypass.
    """

    @staticmethod
    def process_holdings(raw_records: list[dict], live_prices: dict = None) -> dict:
        live_prices = live_prices or {}
        stocks = {}

        # 1. Sabhi transactions ko date/time order mein sort karein (Chronological FIFO)
        sorted_records = sorted(
            raw_records, 
            key=lambda x: (str(x.get("tran_date") or ""), str(x.get("created_at") or ""))
        )

        for row in sorted_records:
            name = str(row.get("particular") or "").strip().upper()
            t_type = str(row.get("tran_type") or "").strip().upper()
            p_qty = int(row.get("purchase_qty") or 0)
            p_val = float(row.get("purchase_value") or 0.0)
            s_qty = int(row.get("sell_qty") or 0)
            s_val = float(row.get("sell_value") or 0.0)
            deb_amt = float(row.get("debit_amount") or 0.0)

            # 🌟 POINT 2 & 3: Skip Bank Settlement, DP / CDSL Charges, UPI, Payouts
            if t_type in ("D", "DEPOSIT", "W", "WITHDRAW", "WITHDRAWAL", "SETTLEMENT", "CHG", "FEE"):
                continue
            if any(term in name for term in ("SETTLEMENT", "DP CHARGE", "CDSL", "AMC", "UPI", "PAYOUT")):
                continue

            # 🌟 POINT 1: Clean Symbol Extraction (e.g. "BEL + BONUS" -> "BEL")
            clean_name = name.replace("+ BONUS", "").replace("+BONUS", "").replace("BONUS", "").strip()
            if "(" in clean_name or " " in clean_name:
                words = clean_name.replace("(", " ").replace(")", " ").replace("X", " ").replace("@", " ").split()
                for w in words:
                    if len(w) >= 3 and w.isalnum() and not w.isdigit() and w not in ("BUY", "SELL", "DEPOSIT", "WITHDRAWAL", "UPI", "BONUS"):
                        clean_name = w
                        break

            if not clean_name:
                continue

            if clean_name not in stocks:
                stocks[clean_name] = {
                    "quantity": 0,
                    "total_invested": 0.0,
                    "avg_buy_price": 0.0
                }

            current_qty = stocks[clean_name]["quantity"]
            current_inv = stocks[clean_name]["total_invested"]

            # --- CASE A: PURCHASE / BUY / BONUS (P or B) ---
            if t_type in ("P", "PURCHASE", "B", "BONUS") or p_qty > 0 or p_val > 0:
                # Agar "+ BONUS" hai toh buy_val hamesha 0.00 rahega
                is_bonus_tran = ("+ BONUS" in name or "+BONUS" in name or t_type in ("B", "BONUS"))
                if is_bonus_tran:
                    buy_val = 0.0
                else:
                    buy_val = p_val if p_val > 0.0 else deb_amt
                    if p_qty > 1 and deb_amt > (p_val * 1.5):
                        buy_val = deb_amt

                new_qty = current_qty + p_qty
                new_inv = current_inv + buy_val
                new_avg = (new_inv / new_qty) if new_qty > 0 else 0.0

                stocks[clean_name]["quantity"] = new_qty
                stocks[clean_name]["total_invested"] = round(new_inv, 2)
                stocks[clean_name]["avg_buy_price"] = round(new_avg, 4)

            # --- CASE B: SELL (S) ---
            elif t_type in ("S", "SELL") or s_qty > 0 or s_val > 0:
                if current_qty > 0:
                    sold_qty = min(current_qty, s_qty)
                    rem_qty = current_qty - sold_qty
                    avg_p = stocks[clean_name]["avg_buy_price"]

                    if rem_qty == 0:
                        stocks[clean_name]["quantity"] = 0
                        stocks[clean_name]["total_invested"] = 0.0
                        stocks[clean_name]["avg_buy_price"] = 0.0
                    else:
                        rem_inv = rem_qty * avg_p
                        stocks[clean_name]["quantity"] = rem_qty
                        stocks[clean_name]["total_invested"] = round(rem_inv, 2)

        # 2. Output Table Rows Generation
        table_rows = []
        overall_invested = 0.0
        overall_market_val = 0.0
        sno = 1

        for sym, data in sorted(stocks.items()):
            net_qty = data["quantity"]
            if net_qty <= 0:
                continue

            tot_inv = round(data["total_invested"], 2)
            inv_per_share = round(tot_inv / net_qty, 2) if net_qty > 0 else 0.0

            # Live CMP rate (fallback to avg price)
            cmp = live_prices.get(sym)
            if cmp is None or cmp <= 0:
                cmp = inv_per_share

            current_mkt_val = round(cmp * net_qty, 2)
            gain_loss_val = round(current_mkt_val - tot_inv, 2)
            gain_loss_pct = round((gain_loss_val / tot_inv) * 100.0, 2) if tot_inv > 0 else 0.0

            overall_invested += tot_inv
            overall_market_val += current_mkt_val

            table_rows.append({
                "sno": sno,
                "name": sym,
                "quantity": net_qty,
                "inv_per_share": inv_per_share,
                "total_invested": tot_inv,
                "cmp": cmp,
                "market_value": current_mkt_val,
                "gain_loss": gain_loss_val,
                "gain_loss_pct": gain_loss_pct
            })
            sno += 1

        overall_gain_loss = round(overall_market_val - overall_invested, 2)
        overall_gain_loss_pct = round((overall_gain_loss / overall_invested) * 100.0, 2) if overall_invested > 0 else 0.0

        return {
            "summary": {
                "total_invested": round(overall_invested, 2),
                "total_market_val": round(overall_market_val, 2),
                "total_gain_loss": overall_gain_loss,
                "total_gain_loss_pct": overall_gain_loss_pct,
                "total_stocks": len(table_rows)
            },
            "holdings": table_rows
        }
