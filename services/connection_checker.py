import socket
import time
import urllib.request
import threading


class ConnectionChecker:
    def __init__(self, db_service=None):
        self.db = db_service
        self._thread = None
        self._stop_event = threading.Event()
        self._is_running = False

        # Status tracking taaki baar-baar CMD spam na ho
        self.last_status = None
        self.last_msg = ""
        self.callback = None
        self.interval = 15  # Default 15 seconds (2 sec ki jagah)

    # =========================================================================
    # Synchronous Single Checks (Lightweight & Fast)
    # =========================================================================
    def check_internet(self, timeout=1.0):
        """
        Direct DNS IP (8.8.8.8 / 1.1.1.1) check.
        Timeout 1 sec rakha gaya hai taaki thread zyada der block na ho.
        """
        for host in ["8.8.8.8", "1.1.1.1"]:
            try:
                sock = socket.create_connection((host, 53), timeout=timeout)
                sock.close()
                return True, "Internet connected successfully"
            except (socket.timeout, OSError):
                continue
            except Exception:
                continue

        return False, "Internet connection fail ho gaya hai!"

    def check_database(self):
        """Database connection check karta hai"""
        if not self.db:
            return False, "Database service missing hai"
        try:
            if hasattr(self.db, "get_connection"):
                with self.db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                        cur.fetchone()
                return True, "Database connected successfully"
            elif hasattr(self.db, "conn") and self.db.conn:
                with self.db.conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
                return True, "Database connected successfully"
            return False, "Database connection object missing hai"
        except Exception as e:
            return False, f"Database error: {e}"

    def check_all(self):
        """Pehle Internet check karega, phir Database"""
        net_ok, net_msg = self.check_internet()
        if not net_ok:
            return False, net_msg

        db_ok, db_msg = self.check_database()
        if not db_ok:
            return False, db_msg

        return True, "Internet aur Database dono connected hain!"

    # =========================================================================
    # 🌟 Asynchronous Non-Blocking Background Thread Engine
    # =========================================================================
    def start_monitoring(self, callback=None, interval=15):
        """
        Background daemon thread start karta hai.
        - callback(is_online: bool, message: str): UI update ke liye function
        - interval: kitne seconds baad check karega (default: 15s)
        """
        if self._is_running:
            return

        self.callback = callback
        self.interval = interval
        self._stop_event.clear()
        self._is_running = True

        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        """Thread ko safely band karta hai"""
        if not self._is_running:
            return
        self._stop_event.set()
        self._is_running = False

    def _worker_loop(self):
        """Worker thread loop - zero UI interference"""
        while not self._stop_event.is_set():
            is_ok, msg = self.check_all()

            # Status badalne par hi console print karein (No CMD Flood)
            if is_ok != self.last_status:
                state_str = "Online" if is_ok else "Offline"
                print(f"[Heartbeat] Status: {state_str} | Msg: {msg}")
                self.last_status = is_ok
                self.last_msg = msg

                # Agar callback provided hai toh trigger karein
                if self.callback:
                    try:
                        self.callback(is_ok, msg)
                    except Exception as cb_err:
                        print(f"⚠️ [Heartbeat Callback Error]: {cb_err}")

            # Safe sleep mechanism (app exit par turant release ho sake)
            self._stop_event.wait(self.interval)
