import re
import time
from datetime import datetime
import requests
from database.DBCore import DBCore

class ETFRegistryService:
    def __init__(self, db_core):
        self.db = db_core or DBCore
        self.session = requests.Session()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/market-data/exchange-traded-funds-etf",
        }

    def _init_session(self):
        """NSE cookies refresh karne ke liye"""
        try:
            self.session.cookies.clear()
            self.session.get("https://www.nseindia.com", headers=self.headers, timeout=12)
            time.sleep(1.5)
        except Exception as e:
            print(f"⚠️ [ETFRegistry] Session init warning: {e}")

    # =========================================================================
    # FUNCTION 3: Dynamic Table Creation for New Symbols
    # =========================================================================
    def create_stock_table(self, table_name: str) -> bool:
        """
        Naye symbol ke liye exact 9-column schema ke sath dedicated table banata hai:
        id, "date", close_price, gain, loss, avg_gain, avg_loss, rs, rsi
        """
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                "date" DATE NOT NULL UNIQUE,
                close_price NUMERIC(10, 2),
                gain NUMERIC(10, 2) DEFAULT 0,
                loss NUMERIC(10, 2) DEFAULT 0,
                avg_gain NUMERIC(10, 4) DEFAULT 0,
                avg_loss NUMERIC(10, 4) DEFAULT 0,
                rs NUMERIC(10, 4) DEFAULT 0,
                rsi NUMERIC(10, 2) DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_{table_name}_date ON {table_name} ("date");
        """
        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(create_sql)
            print(f"📦 [Function 3] Table created successfully: {table_name}")
            return True
        except Exception as e:
            if self.db.conn:
                self.db.conn.rollback()
            print(f"❌ [Function 3] Table creation failed for {table_name}: {e}")
            return False

    # =========================================================================
    # FUNCTION 1 & FUNCTION 2: Fetch, Insert, Reconcile Status & Trigger Table
    # =========================================================================
    def fetch_nse_live_etfs(self) -> dict:
        """
        NSE official endpoint se saare listed ETFs fetch karta hai.
        Returns dict: { 'NIFTYBEES': {'status': 'ACTIVE', ...}, ... }
        """
        self._init_session()
        url = "https://www.nseindia.com/api/etf"

        try:
            res = self.session.get(url, headers=self.headers, timeout=15)
            if res.status_code in [401, 403]:
                self._init_session()
                res = self.session.get(url, headers=self.headers, timeout=15)

            if res.status_code != 200:
                print(f"❌ Failed to fetch ETF list from NSE. HTTP {res.status_code}")
                return {}

            data = res.json().get("data", [])
            nse_etf_map = {}

            for item in data:
                raw_sym = item.get("symbol")
                if not raw_sym:
                    continue

                sym = raw_sym.strip().upper()
                
                # Check trading status / suspension flag
                meta = item.get("meta", {}) or {}
                # Agar trading suspended hai ya market status suspended show kare
                is_suspended = item.get("tradingStatus") == "Suspended" or meta.get("isSuspended", False)
                status = "SUSPENDED" if is_suspended else "ACTIVE"

                nse_etf_map[sym] = {
                    "symbol": sym,
                    "status": status,
                    "meta": meta
                }

            print(f"✅ NSE Live: Total {len(nse_etf_map)} ETFs fetched.")
            return nse_etf_map

        except Exception as e:
            print(f"❌ Error fetching from NSE: {e}")
            return {}

    def sync_etf_registry_and_tables(self):
        """
        Function 1, 2, aur 3 ko coordinate karne wala main master method.
        """
        # 1. NSE se fresh list layein
        nse_etfs = self.fetch_nse_live_etfs()
        if not nse_etfs:
            print("⚠️ NSE data nahi mila. Registry update aborted.")
            return

        

        # 2. Database mein maujood saare ETFs nikaalein
        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT symbol, status, table_name 
                        FROM admin_symbol_registry 
                        WHERE instrument_type = 'ETF';
                    """)
                    db_rows = cur.fetchall()
            db_etfs = {r[0].upper(): {"status": r[1], "table_name": r[2]} for r in db_rows}
        except Exception as e:
            print(f"❌ Error reading existing ETFs from DB: {e}")
            return

        new_symbols_to_insert = []
        status_updates = []

        # =====================================================================
        # Function 1 Check: Naye symbols dhoondhein aur ACTIVE status dein
        # =====================================================================
        for sym, nse_data in nse_etfs.items():
            if sym not in db_etfs:
                # Clean table name format: stock_niftybees
                clean_sym = re.sub(r'[^a-zA-Z0-9_]', '_', sym.lower())
                table_name = f"stock_{clean_sym}"
                
                # Naye records hamesha 'ACTIVE' state mein insert honge
                new_symbols_to_insert.append((sym, "ETF", table_name, "ACTIVE"))

        # =====================================================================
        # Function 2 Check: Existing symbols ka status update karein
        # (ACTIVE -> SUSPENDED / DELISTED)
        # =====================================================================
        for sym, db_info in db_etfs.items():
            current_db_status = db_info["status"] or "ACTIVE"

            if sym not in nse_etfs:
                # Agar symbol NSE ki fresh list mein exist hi nahi karta -> DELISTED
                if current_db_status != "DELISTED":
                    status_updates.append(("DELISTED", sym))
            else:
                # Agar NSE par hai, toh check karein ACTIVE hai ya SUSPENDED
                nse_current_status = nse_etfs[sym]["status"]
                if current_db_status != nse_current_status:
                    status_updates.append((nse_current_status, sym))

        # =====================================================================
        # Database Execution & Table Generation
        # =====================================================================
        try:
            # A. Naye symbols ko admin_symbol_registry mein insert karein (Function 1)
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    # Naye symbols ko admin_symbol_registry mein insert karein (Function 1)
                    if new_symbols_to_insert:
                        insert_query = """
                            INSERT INTO admin_symbol_registry (symbol, instrument_type, table_name, status)
                            VALUES (%s, %s, %s, %s);
                        """
                        cur.executemany(insert_query, new_symbols_to_insert)
                        print(f"✨ [Function 1] {len(new_symbols_to_insert)} naye ETFs registry mein insert ho gaye (Status: ACTIVE).")

            # C. Existing symbols ka status update karein (Function 2)
            if status_updates:
                update_query = """
                    UPDATE admin_symbol_registry 
                    SET status = %s 
                    WHERE symbol = %s;
                """
                cur.executemany(update_query, status_updates)
                
                print(f"🔄 [Function 2] {len(status_updates)} symbols ka status update hua: {status_updates}")
            else:
                print("👍 [Function 2] Sabhi symbols ka status already up-to-date hai.")

			# B. Registry commit hone ke baad naye symbols ke liye tables banayein (Function 3)
            if new_symbols_to_insert:
                for item in new_symbols_to_insert:
                    tbl_name = item[2]
                    self.create_stock_table(tbl_name)

        except Exception as e:
            print(f"❌ Error during registry sync: {e}")
