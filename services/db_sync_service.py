import threading
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
from psycopg2.extras import execute_batch
from services.nse_fetcher import NSEDataFetcher
from database.DBCore import DBCore


class SyncService:
    def __init__(self, db_core=None, on_progress_callback=None, on_complete_callback=None):
        self.db = db_core or DBCore
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback
        self.on_success = None
        self.on_error = None
        self.is_running = False

        self.fetcher = NSEDataFetcher()

    def _get_conn_context(self):
        """DBCore / DatabaseManager se connection context safely return karta hai"""
        if hasattr(self.db, "get_connection"):
            return self.db.get_connection()
        return DBCore.get_connection()

    def start_sync_thread(self, on_success_callback=None, on_error_callback=None, on_progress_callback=None, **kwargs):
        if self.is_running:
            if on_error_callback:
                on_error_callback("Sync pehle se chal raha hai.")
            return False, "Sync pehle se running hai."

        if on_success_callback:
            self.on_success = on_success_callback
        if on_error_callback:
            self.on_error = on_error_callback
        if on_progress_callback:
            self.on_progress = on_progress_callback

        self.is_running = True
        worker = threading.Thread(target=self._run_sync_task, daemon=True)
        worker.start()
        return True, "Sync task start ho gaya."

    def _run_sync_task(self):
        try:
            print("🚀 [SyncService] Starting Delta Sync & Wilder RSI Calculation...")
            symbols = self._get_active_symbols()
            total_symbols = len(symbols)

            if total_symbols == 0:
                print("⚠️ [SyncService] admin_symbol_registry mein koi symbols nahi mile.")
                if self.on_success:
                    self.on_success(datetime.now().strftime("%d %b, %H:%M"))
                return

            completed_count = 0

            # 5 Parallel workers ek sath symbols process karenge
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_symbol = {
                    executor.submit(self._sync_single_stock_worker, item): item[1]
                    for item in symbols
                }

                for future in as_completed(future_to_symbol):
                    sym = future_to_symbol[future]
                    completed_count += 1
                    if self.on_progress:
                        self.on_progress(completed_count, total_symbols, sym)

            now_str = datetime.now().strftime("%d %b, %H:%M")
            self._update_last_sync_timestamp(now_str)

            print("✅ [SyncService] Full Sync Completed Successfully!")
            if self.on_success:
                self.on_success(now_str)
            if self.on_complete:
                self.on_complete(True, "Sync successfully complete!", now_str)

        except Exception as e:
            print(f"❌ [SyncService Task Error]: {e}")
            if self.on_error:
                self.on_error(str(e))
            if self.on_complete:
                self.on_complete(False, str(e), None)

        finally:
            self.is_running = False

    def _sync_single_stock_worker(self, item):
        """Ek single stock ke liye price sync aur delta RSI update chalata hai"""
        sym_id, symbol, inst_type, table_name = item
        try:
            # 1. Last date check karke data fetch aur insert karein
            records_added, last_date_before_sync = self._sync_single_stock(symbol, table_name)

            # 2. Agar data sync hua hai, toh RSI calculate karein
            if records_added > 0:
                self._calculate_and_update_wilder_rsi(
                    table_name=table_name,
                    last_date_before_sync=last_date_before_sync,
                    period=14
                )
            return True, symbol
        except Exception as e:
            print(f"❌ [Worker Error] {symbol}: {e}")
            return False, symbol

    def _get_active_symbols(self):
        """Registry se active symbols aur unki table nikaalta hai"""
        query = """
            SELECT id, symbol, instrument_type, table_name 
            FROM admin_symbol_registry 
            WHERE COALESCE(status, 'ACTIVE') = 'ACTIVE'
            ORDER BY id ASC;
        """
        with self._get_conn_context() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()

    def _get_table_last_date(self, table_name: str):
        """Table se aakhri entry ki 'date' nikaalta hai"""
        try:
            with self._get_conn_context() as conn:
                with conn.cursor() as cur:
                    cur.execute(f'SELECT MAX("date") FROM {table_name};')
                    res = cur.fetchone()
                    return res[0] if res and res[0] is not None else None
        except Exception as e:
            print(f"Error fetching max date from {table_name}: {e}")
            return None

    def _sync_single_stock(self, symbol: str, table_name: str):
        """
        Last date check karke data insert karta hai.
        Returns: (records_count, last_date_before_sync)
        """
        today = date.today()
        last_date = self._get_table_last_date(table_name)

        if last_date is None:
            # Table empty hai -> Aaj se 1 saal back ka data
            from_date = today - timedelta(days=365)
            print(f"[{symbol}] Table khali hai. 1 saal ka data fetch ho raha hai ({from_date} to {today})")
        else:
            # Table mein data hai -> Last date se aaj tak ka data
            from_date = last_date
            print(f"[{symbol}] Last Date: {last_date}. Fetching missing records ({from_date} to {today})")

        records = self.fetcher.fetch_historical_prices(symbol, from_date, today)
        if not records:
            return 0, last_date

        insert_query = f"""
            INSERT INTO {table_name} ("date", close_price)
            VALUES (%s, %s)
            ON CONFLICT ("date") DO UPDATE 
            SET close_price = EXCLUDED.close_price;
        """
        try:
            with self._get_conn_context() as conn:
                with conn.cursor() as cur:
                    execute_batch(cur, insert_query, records, page_size=100)
                conn.commit()
            print(f"✅ [{symbol}] {len(records)} date/close rows sync ho gayi.")
            return len(records), last_date
        except Exception as e:
            print(f"❌ [{symbol}] Insert query error: {e}")
            return 0, last_date

    def _calculate_and_update_wilder_rsi(self, table_name: str, last_date_before_sync=None, period: int = 14):
        """
        - Agar last_date_before_sync maujood hai: Poora table read NAHI hoga. Sirf last_date se
          aaj tak ki rows read aur update hongi.
        - Agar last_date_before_sync None hai (table khali thi): 1 saal ke data par full RSI calculate hoga.
        """
        try:
            with self._get_conn_context() as conn:
                with conn.cursor() as cur:
                    # =========================================================
                    # CASE 1: DELTA RSI UPDATE (Jab Table Mein Pehle Se Data Tha)
                    # =========================================================
                    if last_date_before_sync is not None:
                        # Last entry date se theek 1 din pehle ki row layein (base values ke liye)
                        cur.execute(f"""
                            SELECT "date", close_price, avg_gain, avg_loss
                            FROM {table_name}
                            WHERE "date" < %s
                            ORDER BY "date" DESC
                            LIMIT 1;
                        """, (last_date_before_sync,))
                        prev_row = cur.fetchone()

                        # Agar pichli row mein avg_gain / avg_loss pehle se maujood hai
                        if prev_row and prev_row[2] is not None and prev_row[3] is not None and (float(prev_row[2]) > 0 or float(prev_row[3]) > 0):
                            prev_close = float(prev_row[1])
                            prev_avg_gain = float(prev_row[2])
                            prev_avg_loss = float(prev_row[3])

                            # Sirf last_date_before_sync se aaj tak ki rows read karein
                            cur.execute(f"""
                                SELECT "date", close_price
                                FROM {table_name}
                                WHERE "date" >= %s
                                ORDER BY "date" ASC;
                            """, (last_date_before_sync,))
                            delta_rows = cur.fetchall()

                            if not delta_rows:
                                return

                            update_data = []
                            for r_date, r_close in delta_rows:
                                curr_close = float(r_close)
                                diff = curr_close - prev_close

                                gain = diff if diff > 0 else 0.0
                                loss = -diff if diff < 0 else 0.0

                                curr_avg_gain = ((prev_avg_gain * (period - 1)) + gain) / period
                                curr_avg_loss = ((prev_avg_loss * (period - 1)) + loss) / period

                                if curr_avg_loss == 0:
                                    rs = 0.0
                                    rsi = 100.0
                                else:
                                    rs = curr_avg_gain / curr_avg_loss
                                    rsi = 100.0 - (100.0 / (1.0 + rs))

                                update_data.append((
                                    round(gain, 2),
                                    round(loss, 2),
                                    round(curr_avg_gain, 4),
                                    round(curr_avg_loss, 4),
                                    round(rs, 4),
                                    round(rsi, 2),
                                    r_date
                                ))

                                prev_close = curr_close
                                prev_avg_gain = curr_avg_gain
                                prev_avg_loss = curr_avg_loss

                            update_query = f"""
                                UPDATE {table_name} 
                                SET gain = %s,
                                    loss = %s,
                                    avg_gain = %s,
                                    avg_loss = %s,
                                    rs = %s,
                                    rsi = %s
                                WHERE "date" = %s;
                            """
                            execute_batch(cur, update_query, update_data, page_size=100)
                            conn.commit()
                            print(f"⚡ [{table_name}] Delta RSI updated from {last_date_before_sync} ({len(update_data)} rows).")
                            return

                    # =========================================================
                    # CASE 2: FULL TABLE RSI (Sirf Tab Jab Table Empty Thi)
                    # =========================================================
                    cur.execute(f"""
                        SELECT "date", close_price 
                        FROM {table_name} 
                        ORDER BY "date" ASC;
                    """)
                    rows = cur.fetchall()

                    if len(rows) <= period:
                        return

                    df = pd.DataFrame(rows, columns=["date", "close_price"])
                    df["close_price"] = pd.to_numeric(df["close_price"], errors="coerce")

                    delta = df["close_price"].diff()
                    df["gain"] = np.where(delta > 0, delta, 0.0)
                    df["loss"] = np.where(delta < 0, -delta, 0.0)

                    n = len(df)
                    avg_gain = np.zeros(n)
                    avg_loss = np.zeros(n)
                    rs = np.zeros(n)
                    rsi = np.zeros(n)

                    # Pehle 14 din ka Initial Simple Average (Wilder Seed)
                    first_avg_gain = df["gain"].iloc[1 : period + 1].mean()
                    first_avg_loss = df["loss"].iloc[1 : period + 1].mean()

                    avg_gain[period] = first_avg_gain
                    avg_loss[period] = first_avg_loss

                    if first_avg_loss == 0:
                        rsi[period] = 100.0
                        rs[period] = 0.0
                    else:
                        rs[period] = first_avg_gain / first_avg_loss
                        rsi[period] = 100.0 - (100.0 / (1.0 + rs[period]))

                    gain_vals = df["gain"].values
                    loss_vals = df["loss"].values

                    for i in range(period + 1, n):
                        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain_vals[i]) / period
                        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss_vals[i]) / period

                        if avg_loss[i] == 0:
                            rs[i] = 0.0
                            rsi[i] = 100.0
                        else:
                            rs[i] = avg_gain[i] / avg_loss[i]
                            rsi[i] = 100.0 - (100.0 / (1.0 + rs[i]))

                    df["avg_gain"] = avg_gain
                    df["avg_loss"] = avg_loss
                    df["rs"] = rs
                    df["rsi"] = rsi

                    valid_df = df.iloc[1:]

                    update_data = [
                        (
                            round(float(r["gain"]), 2),
                            round(float(r["loss"]), 2),
                            round(float(r["avg_gain"]), 4),
                            round(float(r["avg_loss"]), 4),
                            round(float(r["rs"]), 4),
                            round(float(r["rsi"]), 2),
                            r["date"],
                        )
                        for _, r in valid_df.iterrows()
                    ]

                    update_query = f"""
                        UPDATE {table_name} 
                        SET gain = %s,
                            loss = %s,
                            avg_gain = %s,
                            avg_loss = %s,
                            rs = %s,
                            rsi = %s
                        WHERE "date" = %s;
                    """
                    execute_batch(cur, update_query, update_data, page_size=100)
                    conn.commit()
                    print(f"🎯 [{table_name}] New table 1-year base RSI updated ({len(update_data)} rows).")

        except Exception as e:
            print(f"❌ Error calculating indicators for {table_name}: {e}")

    def _update_last_sync_timestamp(self, timestamp_str: str):
        try:
            with self._get_conn_context() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS system_metadata (
                            key VARCHAR(50) PRIMARY KEY,
                            value TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cur.execute("""
                        INSERT INTO system_metadata (key, value, updated_at)
                        VALUES ('last_sync', %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (key) DO UPDATE 
                        SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
                    """, (timestamp_str,))
                conn.commit()
        except Exception as e:
            print(f"Error updating timestamp: {e}")
