from services.connection_checker import ConnectionChecker
from services.validators import validate_pan, validate_pin
from services.session_manager import SessionManager
from database.DBCore import DBCore


class AuthManager:
    def __init__(self, db_service=None):
        self.db = db_service or DBCore
        self.checker = ConnectionChecker(self.db)
		
    def test_connection(self):
        """ConnectionChecker utility ko call karta hai"""
        return self.checker.check_all()
    
    def authenticate(self, user_id, user_pin):
        """
        Login hamesha UID (PAN) aur PIN se hoga
        """
        try:
            is_ok, msg = self.test_connection()
            if not is_ok:
                return False, None

			# User ID ko uppercase mein convert karein taki case mismatch na ho
            formatted_uid = str(user_id).strip().upper()
            formatted_pin = str(user_pin).strip()

            print(f"DEBUG DB QUERY -> Checking user_id='{formatted_uid}' and user_pin='{formatted_pin}'")
            
            # Pool-based context manager
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT user_id, name, role, status 
                        FROM users 
                        WHERE UPPER(TRIM(user_id)) = %s AND TRIM(user_pin) = %s;
                    """
                    cur.execute(query, (formatted_uid, formatted_pin))
                    row = cur.fetchone()
                    print(f"DEBUG DB FETCH -> Row Result: {row}")

            if row:
                # Check karein ki user ka status active hai ya nahi
                user_id_val, name_val, role_val, status_val = row[0], row[1], row[2], row[3]
                
                if status_val and status_val.strip().lower() != 'active':
                    print("Login blocked: Account inactive hai.")
                    return False, None

                user_info = {
                    "id": user_id_val,
                    "name": name_val or user_id_val,
                    "role": (role_val or "user").strip().lower()
                }
                return True, user_info
            
            return False, None
        except Exception as e:
            print(f"Authentication query error: {e}")
            return False, None

    def register_user(self, name, email, pan, pin, password):
        """
        Naya user register karta hai jisme PAN user_id banta hai 
        aur role/status auto define hote hain.
        """
        try:
            is_ok, msg = self.test_connection()
            if not is_ok:
                return False, msg

            pan = pan.strip().upper()
            pin = pin.strip()

            # 1. PAN Format Validation
            if not validate_pan(pan):
                return False, "Invalid PAN Format! (e.g. ABCDE1234F)"

            # 2. PIN Validation (4 digits)
            if not validate_pin(pin):
                return False, "PIN strictly 4-digit numeric hona chahiye!"

            if not name or not email or not password:
                return False, "Sabhi fields bharna zaroori hai!"
            
            with DBCore.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if PAN or Email already exists
                    check_query = "SELECT user_id FROM users WHERE UPPER(TRIM(user_id)) = %s OR email = %s;"
                    cur.execute(check_query, (pan, email.strip()))
                    if cur.fetchone():
                        return False, "Yeh PAN Number ya Email pehle se registered hai!"

                    # Insert new user (role='user', status='active')
                    insert_query = """
                        INSERT INTO users (user_id, name, email, user_pin, pswd, role, status) 
                        VALUES (%s, %s, %s, %s, %s, 'user', 'active');
                    """
                    cur.execute(
                        insert_query,
                        (pan, name.strip(), email.strip(), pin, password.strip())
                    )
                    # Yahan conn.commit() likhne ki zaroorat nahi hai, 
                    # context manager block khatam hote hi auto-commit kar deta hai.       
            
            return True, "Registration Successful! Ab aap login kar sakte hain."
        except Exception as e:
            print(f"Registration error: {e}")
            return False, f"Error: {e}"
