import os
import sys
from datetime import datetime

# Path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database.DBCore import DBCore
from user.user_db import UserDatabase

try:
    from user.body.logic.holdings_engine import HoldingsEngine
except ModuleNotFoundError:
    try:
        from user.logic.holdings_engine import HoldingsEngine
    except ModuleNotFoundError:
        from holdings_engine import HoldingsEngine

try:
    from services.nse_fetcher_nseindia import NSEDataFetcher
except ModuleNotFoundError:
    try:
        from user.services.nse_fetcher_nseindia import NSEDataFetcher
    except ModuleNotFoundError:
        from nse_fetcher_nseindia import NSEDataFetcher


class UserPortfolioDatabase:
    """
    User dashboard portfolio metrics provider with in-memory singleton cache.
    - Prevents duplicate NSE network calls across Dashboard and Holdings.
    - Filters out zero-quantity (fully sold) stocks before querying NSE.
    """
    # 🌟 Application-wide Shared Cache
    _SHARED_CACHE = {
        "user_id": None,
        "timestamp": None,
        "summary": None,
        "holdings": None
    }

    def __init__(self, db_core=None):
        self.db_core = db_core or DBCore
        self.user_db = UserDatabase(self.db_core)
        self.fetcher = NSEDataFetcher()

    @classmethod
    def get_cached_result(cls, user_id: str):
        """Agar cache valid aur same user ka hai toh return karein"""
        if cls._SHARED_CACHE["user_id"] == user_id and cls._SHARED_CACHE["summary"] is not None:
            return {
                "summary": cls._SHARED_CACHE["summary"],
                "holdings": cls._SHARED_CACHE["holdings"] or []
            }
        return None

    @classmethod
    def invalidate_cache(cls):
        """New buy/sell hone par shared cache reset karein"""
        cls._SHARED_CACHE["user_id"] = None
        cls._SHARED_CACHE["timestamp"] = None
        cls._SHARED_CACHE["summary"] = None
        cls._SHARED_CACHE["holdings"] = None

    def get_portfolio_summary(self, user_id: str, fetch_live_cmp: bool = True, force_refresh: bool = False) -> dict:
        default_res = {
            "invested": 0.0,
            "market_value": 0.0,
            "gain_loss": 0.0,
            "pct_change": 0.0,
            "total_stocks": 0
        }

        if not user_id:
            return default_res

        # Cache check (agar live rate pehle se fetch ho chuka hai)
        if not force_refresh and fetch_live_cmp:
            cached = self.get_cached_result(user_id)
            if cached:
                s = cached["summary"]
                return {
                    "invested": float(s.get("total_invested", 0.0) or 0.0),
                    "market_value": float(s.get("total_market_val", 0.0) or 0.0),
                    "gain_loss": float(s.get("total_gain_loss", 0.0) or 0.0),
                    "pct_change": float(s.get("total_gain_loss_pct", 0.0) or 0.0),
                    "total_stocks": int(s.get("total_stocks", 0) or 0)
                }

        try:
            # 1. DB se raw transactions fetch karein
            raw_txs = self.user_db.get_raw_transactions(user_id)
            if not raw_txs:
                return default_res

            # 2. 🌟 STEP 1: Quick Offline Pass (Zero Sold-Out Stocks Filter)
            # Bina internet ke calculate karke sirf unhi stocks ko nikalein jinki Qty > 0 hai
            offline_result = HoldingsEngine.process_holdings(raw_txs, live_prices={})
            active_holdings = offline_result.get("holdings", [])
            active_symbols = sorted(list(set([row["name"] for row in active_holdings if row.get("quantity", 0) > 0])))

            live_prices = {}
            if fetch_live_cmp and active_symbols:
                try:
                    # 🌟 Sirf 1 baar call hoga active stocks ke liye
                    live_prices = self.fetcher.fetch_bulk_live_cmp(active_symbols)
                except Exception as e:
                    print(f"⚠️ [PortfolioDB] Live CMP fetch error: {e}")
                    live_prices = {}

            # 3. Final Engine calculation with live CMP
            engine_output = HoldingsEngine.process_holdings(raw_txs, live_prices)
            summary = engine_output.get("summary", {})

            # 4. Result ko Shared Cache mein save karein
            if fetch_live_cmp:
                UserPortfolioDatabase._SHARED_CACHE["user_id"] = user_id
                UserPortfolioDatabase._SHARED_CACHE["timestamp"] = datetime.now()
                UserPortfolioDatabase._SHARED_CACHE["summary"] = summary
                UserPortfolioDatabase._SHARED_CACHE["holdings"] = engine_output.get("holdings", [])

            return {
                "invested": float(summary.get("total_invested", 0.0) or 0.0),
                "market_value": float(summary.get("total_market_val", 0.0) or 0.0),
                "gain_loss": float(summary.get("total_gain_loss", 0.0) or 0.0),
                "pct_change": float(summary.get("total_gain_loss_pct", 0.0) or 0.0),
                "total_stocks": int(summary.get("total_stocks", 0) or 0)
            }

        except Exception as e:
            print(f"❌ [UserPortfolioDatabase.get_portfolio_summary Error]: {e}")
            return default_res
