import time
from datetime import date, datetime, timedelta
import yfinance as yf


class NSEDataFetcher:
    def __init__(self):
        pass

    def fetch_historical_prices(self, symbol: str, from_date: date, to_date: date):
        """
        Sirf Date aur Close Price fetch karta hai.
        Returns: [(date_obj, close_price_float), ...]
        """
        ticker_symbol = f"{symbol.strip().upper()}.NS"
        records = []

        try:
            # End date ko 1 din aage badhate hain taaki to_date inclusive ho sake
            fetch_end = to_date + timedelta(days=1)
            
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(
                start=from_date.strftime("%Y-%m-%d"),
                end=fetch_end.strftime("%Y-%m-%d"),
                auto_adjust=False
            )

            if df.empty:
                print(f"⚠️ [DataFetcher] {ticker_symbol} ke liye koi data nahi mila.")
                return []

            for index, row in df.iterrows():
                t_date = index.date()
                close_p = round(float(row["Close"]), 2)
                records.append((t_date, close_p))

            records.sort(key=lambda x: x[0])
            return records

        except Exception as e:
            print(f"❌ [DataFetcher] Error fetching {symbol}: {e}")
            return []
