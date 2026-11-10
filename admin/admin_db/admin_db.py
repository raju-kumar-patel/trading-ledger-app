from database.DBCore import DBCore

class AdminDB:
    def __init__(self, db_core=None):
        """
        DBCore instance ke through database operations execute karta hai.
        """
        self.db = db_core or DBCore
     
    # ===========================admin_main=======================================================

    def get_header_metrics(self):
        """
        Row 1 aur Row 2 ke liye sabhi counts aur balance fetch karta hai.
        Returns: dict with active_users, total_users, stocks_count, etfs_count, liquid_balance
        """
        metrics = {
            "total_users": 0,
            "active_users": 0,
            "stocks_count": 0,
            "etfs_count": 0,
            "liquid_balance": 0.00
        }
        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
					# 1. Active Online Sessions
                    cur.execute("""
                        SELECT COUNT(DISTINCT user_id) 
                        FROM user_sessions 
                        WHERE is_active = TRUE AND expires_at > CURRENT_TIMESTAMP;
                    """)
                    res = cur.fetchone()
                    metrics["active_users"] = res[0] if res else 0
					
					# 2. Stock Tables Count
                    cur.execute("""SELECT COUNT(*) FROM admin_symbol_registry WHERE instrument_type = 'Equity Share';""")
                    metrics["stocks_count"] = cur.fetchone()[0] or 0

					# 3. ETF Tables Count
                    cur.execute("""SELECT COUNT(*) FROM admin_symbol_registry WHERE instrument_type = 'ETF';""")
                    metrics["etfs_count"] = cur.fetchone()[0] or 0

					# 4. Total Liquid Balance (Agar balance table ho toh wahan se sum lein)
                    metrics["liquid_balance"] = 0.00  # Dynamic table query attach kar sakte hain

        except Exception as e:
            print(f"AdminDB -> get_header_metrics error: {e}")

        return metrics
	
	
	# ===========================user_management_view=======================================================
	
	
    def get_users_with_sessions(self):
        """
        Users aur unke latest Session record ko LEFT JOIN karke fetch karta hai.
        """
        query = """
            SELECT 
                u.user_id,
                COALESCE(u.name, u.user_id) AS name,
                u.role,
                u.status AS account_status,
                s.session_id,
                s.ip_address,
                s.machine_name,
                s.login_time,
                s.last_activity,
                CASE 
                    WHEN s.is_active = TRUE AND s.expires_at > CURRENT_TIMESTAMP THEN 'Online'
                    ELSE 'Offline'
                END AS live_session_status
            FROM users u
            LEFT JOIN (
                SELECT DISTINCT ON (user_id) 
                    session_id, user_id, ip_address, machine_name, login_time, last_activity, expires_at, is_active
                FROM user_sessions
                ORDER BY user_id, login_time DESC
            ) s ON u.user_id = s.user_id
            ORDER BY u.user_id ASC;
        """
        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    return cur.fetchall()
        except Exception as e:
            print(f"Error fetching user session records: {e}")
            return []

    #  =======================================================================================
	
    def get_user_management_metrics(self):
        """Total users aur currently logged-in users ka live count deta hai"""
        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Total & Active registered users
                    cur.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'active') FROM users;")
                    total_users, active_accounts = cur.fetchone()

                    # 2. Currently logged-in active sessions
                    cur.execute("""
                        SELECT COUNT(DISTINCT user_id) 
                        FROM user_sessions 
                        WHERE is_active = TRUE AND expires_at > CURRENT_TIMESTAMP;
                    """)
                    online_users = cur.fetchone()[0]
                    return {
						"total_users": total_users,
						"active_accounts": active_accounts,
						"online_users": online_users
					}
        except Exception as e:
            print(f"Error fetching user metrics: {e}")
            return {"total_users": 0, "active_accounts": 0, "online_users": 0}

    #  =======================================================================================

    def toggle_user_account_status(self, user_id, current_status):
        """Account ko active se inactive ya vice-versa switch karta hai"""
        new_status = "inactive" if current_status.lower() == "active" else "active"
        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE users SET status = %s WHERE user_id = %s;", (new_status, user_id))
                    
                    # Agar user deactivate ho raha hai toh uska session bhi turant kill karein
                    if new_status == "inactive":
                        cur.execute("UPDATE user_sessions SET is_active = FALSE WHERE user_id = %s;", (user_id,))
                        
            return True, new_status
        except Exception as e:
            return False, str(e)

    #  =======================================================================================

    def kill_user_session(self, user_id):
        """Force Logout: User ka active session database se kill kar deta hai"""
        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_sessions 
                        SET is_active = FALSE 
                        WHERE user_id = %s AND is_active = TRUE;
                    """, (user_id,))
                    rows_affected = cur.rowcount
            return True, rows_affected
        except Exception as e:
            return False, str(e)
            
    #  =======================================================================================        
    #  ================================stocks_view===========================================  
         

    def get_stock_tables_list(self):
        """Sirf 'Equity Share' instrument_type wale records fetch karta hai"""
        query = """
            SELECT id, symbol, table_name 
            FROM admin_symbol_registry 
            WHERE instrument_type = 'Equity Share'
            ORDER BY id ASC;
        """
        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    return cur.fetchall()
        except Exception as e:
            print(f"Error fetching equity stocks: {e}")
            return []

    #  =======================================================================================        
    #  ===========================etfs_view==============================================


    def get_etf_tables_list(self):
        """Sirf 'ETF' instrument_type wale records fetch karta hai"""
        query = """
            SELECT id, symbol, table_name 
            FROM admin_symbol_registry 
            WHERE instrument_type = 'ETF'
            ORDER BY id ASC;
        """
        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    return cur.fetchall()
        except Exception as e:
            print(f"Error fetching ETFs: {e}")
            return []
