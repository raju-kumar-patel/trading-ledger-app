import time
import urllib.parse
from datetime import date, datetime, timedelta
import requests


class NSEDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.has_cookies = False
        self.cookie_attempted = False

        # Clean browser headers (Akamai HTTP/1.1 bot-trap headers completely removed)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        self.session.headers.update(self.headers)
        self._init_session()

    def _init_session(self) -> bool:
        """NSE cookies set karne ke liye landing page request"""
        if self.cookie_attempted and not self.has_cookies:
            return False

        self.cookie_attempted = True
        try:
            print("   🌐 [NSEFetcher]: Connecting to NSE for session cookies...")
            self.session.cookies.clear()
            
            # Root homepage ke bajaye quote page se cookie fetch karein (Akamai bypass)
            test_url = "https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE"
            res = self.session.get(test_url, timeout=8)
            print(f"   🌐 [NSEFetcher]: Cookie response status = {res.status_code}")

            if res.status_code == 200:
                self.has_cookies = True
                time.sleep(1.0)
                return True
            else:
                self.has_cookies = False
                return False
        except Exception as e:
            print(f"   ⚠️ [NSEFetcher] Cookie initialization failed: {e}")
            self.has_cookies = False
            return False

    # =========================================================================
    # LIVE MARKET DATA METHODS
    # =========================================================================
    def fetch_live_quote(self, symbol: str) -> dict | None:
        """
        NSE India live API se real-time CMP fetch karta hai.
        Agar NSE 403 de toh real-time NSE fallback feed se live price nikaalta hai.
        """
        sym_clean = symbol.strip().upper()

        # Step 1: Agar session cookie valid hai, toh direct NSE India API try karein
        if self.has_cookies:
            encoded_sym = urllib.parse.quote(sym_clean)
            url = f"https://www.nseindia.com/api/quote-equity?symbol={encoded_sym}"

            headers = self.headers.copy()
            headers["Accept"] = "*/*"
            headers["Referer"] = f"https://www.nseindia.com/get-quotes/equity?symbol={encoded_sym}"

            try:
                response = self.session.get(url, headers=headers, timeout=6)
                if response.status_code == 200:
                    data = response.json()
                    price_info = data.get("priceInfo", {})
                    cmp_val = float(price_info.get("lastPrice", 0.0) or 0.0)
                    if cmp_val > 0:
                        print(f"   🎯 [NSE Live]: '{sym_clean}' CMP = ₹{cmp_val:,.2f}")
                        return {"symbol": sym_clean, "cmp": cmp_val}
            except Exception:
                pass

        # Step 2: Live NSE Feed Fallback (Agar NSE website ne 403 block kiya ho)
        fallback_cmp = self._fetch_live_ticker_fallback(sym_clean)
        if fallback_cmp and fallback_cmp > 0:
            print(f"   🎯 [NSE Feed Fallback]: '{sym_clean}' Live Price = ₹{fallback_cmp:,.2f}")
            return {"symbol": sym_clean, "cmp": fallback_cmp}

        return None

    def _fetch_live_ticker_fallback(self, symbol: str) -> float | None:
        """NSE live market stream fallback jo 403 block nahi karta"""
        try:
            # NSE ticker query (.NS for Indian National Stock Exchange)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}.NS?interval=1d"
            h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            r = requests.get(url, headers=h, timeout=5)
            if r.status_code == 200:
                j = r.json()
                meta = j.get("chart", {}).get("result", [{}])[0].get("meta", {})
                last_price = meta.get("regularMarketPrice")
                if last_price:
                    return float(last_price)
        except Exception:
            pass
        return None

    def fetch_bulk_live_cmp(self, symbols: list[str]) -> dict[str, float]:
        """
        Holdings ke sabhi symbols ke live CMP ka dictionary map banata hai.
        Output: {'BEL': 312.40, 'PSUBNKBEES': 82.50}
        """
        price_map = {}
        unique_syms = sorted(list({s.strip().upper() for s in symbols if s}))

        for sym in unique_syms:
            quote = self.fetch_live_quote(sym)
            if quote and quote.get("cmp", 0.0) > 0:
                price_map[sym] = round(quote["cmp"], 2)
            time.sleep(0.2)

        return price_map

    # =========================================================================
    # HISTORICAL METHODS (Preserved for Analysis tab)
    # =========================================================================
    def fetch_historical_ohlcv(self, symbol: str, from_date: date, to_date: date):
        all_records = []
        chunk_start = from_date

        while chunk_start <= to_date:
            chunk_end = min(chunk_start + timedelta(days=80), to_date)
            records = self._fetch_chunk(symbol, chunk_start, chunk_end)
            if records:
                all_records.extend(records)
            chunk_start = chunk_end + timedelta(days=1)
            time.sleep(1.0)

        unique_records = {r[0]: r for r in all_records}
        sorted_records = sorted(unique_records.values(), key=lambda x: x[0])
        return sorted_records

    def _fetch_chunk(self, symbol: str, from_date: date, to_date: date):
        from_str = from_date.strftime("%d-%m-%Y")
        to_str = to_date.strftime("%d-%m-%Y")

        url = (
            f"https://www.nseindia.com/api/historical/cm/equity?"
            f"symbol={symbol}&series=[%22EQ%22]&from={from_str}&to={to_str}"
        )

        headers = self.headers.copy()
        headers["Referer"] = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"

        for attempt in range(2):
            try:
                response = self.session.get(url, headers=headers, timeout=15)
                if response.status_code in [401, 403, 503]:
                    self.has_cookies = False
                    self.cookie_attempted = False
                    self._init_session()
                    time.sleep(1.5)
                    response = self.session.get(url, headers=headers, timeout=15)

                if response.status_code != 200:
                    return []

                data = response.json()
                raw_items = data.get("data", [])
                chunk_records = []

                for item in raw_items:
                    raw_date_str = item.get("CH_TIMESTAMP") or item.get("mTIMESTAMP")
                    if not raw_date_str:
                        continue

                    try:
                        t_date = datetime.strptime(raw_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        t_date = datetime.strptime(raw_date_str, "%d-%b-%Y").date()

                    open_p = float(item.get("CH_OPENING_PRICE", 0) or 0)
                    high_p = float(item.get("CH_TRADE_HIGH_PRICE", 0) or 0)
                    low_p = float(item.get("CH_TRADE_LOW_PRICE", 0) or 0)
                    close_p = float(item.get("CH_CLOSING_PRICE", 0) or 0)
                    volume = int(item.get("CH_TOT_TRADED_QTY", 0) or 0)

                    chunk_records.append((t_date, open_p, high_p, low_p, close_p, volume))

                return chunk_records

            except Exception as e:
                time.sleep(1.0)

        return []
