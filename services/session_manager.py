import socket
from datetime import datetime, timedelta
from database.DBCore import DBCore

class SessionManager:
    def __init__(self, db_core, session_timeout_minutes=30*60):
        self.db = db_core or DBCore
        self.timeout_minutes = session_timeout_minutes
        self.current_session_id = None
        self.current_user_id = None

    def _get_machine_details(self):
        """Client machine name aur local IP fetch karta hai"""
        try:
            hostname = socket.gethostname()
            ip_addr = socket.gethostbyname(hostname)
            return ip_addr, hostname
        except Exception:
            return "127.0.0.1", "Unknown-PC"

    def create_session(self, user_id):
        """Login ke waqt naya session generate karta hai"""
        ip, hostname = self._get_machine_details()
        expires_at = datetime.now() + timedelta(minutes=self.timeout_minutes)

        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Purane sabhi active sessions close karein (Single Device Login)
                    cur.execute("""
                        UPDATE user_sessions 
                        SET is_active = FALSE 
                        WHERE user_id = %s AND is_active = TRUE;
                    """, (user_id,))

                    # 2. Naya active session insert karein
                    cur.execute("""
                        INSERT INTO user_sessions (user_id, ip_address, machine_name, expires_at, is_active)
                        VALUES (%s, %s, %s, %s, TRUE)
                        RETURNING session_id;
                    """, (user_id, ip, hostname, expires_at))

                    session_id = cur.fetchone()[0]

            self.current_session_id = str(session_id)
            self.current_user_id = user_id
            print(f"🔒 Session Created: {self.current_session_id} for User: {user_id}")
            return self.current_session_id

        except Exception as e:
            print(f"Session creation error: {e}")
            if self.db.conn:
                self.db.conn.rollback()
            return None

    def touch_activity(self):
        """User ke click/activity par last_activity aur expiry time aage badhata hai"""
        if not self.current_session_id:
            return False

        try:
            new_expiry = datetime.now() + timedelta(minutes=self.timeout_minutes)
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_sessions
                        SET last_activity = CURRENT_TIMESTAMP,
                            expires_at = %s
                        WHERE session_id = %s AND is_active = TRUE;
                    """, (new_expiry, self.current_session_id))
            return True
        except Exception as e:
            print(f"Session touch error: {e}")
            return False

    def validate_session(self):
        """Check karta hai ki session active aur non-expired hai ya nahi"""
        if not self.current_session_id:
            return False, "Session not found"

        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT expires_at, is_active 
                        FROM user_sessions 
                        WHERE session_id = %s;
                    """, (self.current_session_id,))
                    row = cur.fetchone()

            if not row:
                return False, "Session invalid"

            expires_at, is_active = row[0], row[1]

            if not is_active:
                return False, "Logged in from another device"

            if datetime.now() > expires_at:
                self.terminate_session()
                return False, "Session expired due to inactivity"

            return True, "Session valid"

        except Exception as e:
            return False, f"Session validation error: {e}"

    def terminate_session(self):
        """Logout par session ko permanently de-activate karta hai"""
        if not self.current_session_id:
            return

        try:
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_sessions 
                        SET is_active = FALSE 
                        WHERE session_id = %s;
                    """, (self.current_session_id,))
            print(f"🔓 Session Terminated: {self.current_session_id}")
        except Exception as e:
            print(f"Session termination error: {e}")
        finally:
            self.current_session_id = None
            self.current_user_id = None
