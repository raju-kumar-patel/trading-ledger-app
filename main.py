import customtkinter as ctk
from database.DBCore import DBCore
from tkinter import messagebox
from auth.register_window import RegisterWindow
from auth.auth_manager import AuthManager
from auth.login_window import LoginWindow
from user.user_ui_main import UserApp
from admin.admin_ui_main import AdminApp
from services.session_manager import SessionManager


class MainApplication(ctk.CTk):
	def __init__(self):
		super().__init__()
		# 1. DB Service Initialize karein - Database aur Auth setup
		try:
			DBCore.initialize_pool()
			self.db = DBCore
			print(" Database Pool Initialized Successfully!")
		except Exception as e:
			print(f" Database Connection Failed: {e}")
			self.db = None
		self.auth = AuthManager(self.db)
		
		# 2. SessionManager ko pehle initialize karein
		self.session_manager = SessionManager(db_core=self.db)
		self.current_view = None
		
		# 3. Window Close Event Bind karein (WM_DELETE_WINDOW)
		self.protocol("WM_DELETE_WINDOW", self.on_app_closing)
		
		# 4. Safe Global Bindings (User activity listener)
		self.bind_all("<Any-KeyPress>", lambda e: self.session_manager.touch_activity())
		self.bind_all("<Button-1>", lambda e: self.session_manager.touch_activity())
		# 4.1. Har 1 minute mein session validity check:
		self.after(60000, self._check_session_alive)
		
		# 4. Appearence Mode Set	
		ctk.set_appearance_mode("Dark")
		ctk.set_default_color_theme("blue")
		self.title("Trending Ledger - Professional Users")
		
		# 5. Sabse pahle login window shaow 
		self.show_login_screen()
    
	def _handle_user_activity(self, event=None):
		"""Tabhi touch activity karega jab user login ho chuka ho aur session active ho"""
		if (hasattr(self, "session_manager")
            and self.session_manager
            and self.session_manager.current_session_id
        ):
			self.session_manager.touch_activity()
    
	def _check_session_alive(self):
		if (
            hasattr(self, "session_manager") 
            and self.session_manager 
            and self.session_manager.current_session_id
        ):
			is_valid, msg = self.session_manager.validate_session()
			if not is_valid:
				from tkinter import messagebox
				messagebox.showwarning("Session Expired", f"{msg}. Please login again.")
				self.show_login_screen()
				return
            
		self.after(60000, self._check_session_alive)
    
	def show_login_screen(self):
		"""Logout handle karta hai"""
        # 1. Database mein session close karein
		if hasattr(self, "session_manager") and self.session_manager:
			self.session_manager.terminate_session()
            
		# 2. puri view se pahle login view show karta hai
		if self.current_view:
			self.current_view.destroy()
			self.current_view = None
		
		self.geometry("460x520")
		self.minsize(460, 500)
		self.resizable(False, False)
		self.title("Trading Ledger - Secure Login")
		# Trading App ko login per jate hain
		self.current_view = LoginWindow(
            self,
            auth_manager=self.auth,
            on_login_success=self.route_user_to_dashboard,
            on_open_register=self.show_register_screen
			)
		self.current_view.pack(fill="both", expand=True)
    
	def show_register_screen(self):
		if self.current_view:
			self.current_view.destroy()
	
		self.title("Trading Ledger - Register New User")
		self.geometry("460x520")
		self.minsize(460, 520)
		self.resizable(False, False)
		
		from auth.register_window import RegisterWindow
		self.current_view = RegisterWindow(
            self,
            auth_manager=self.auth,
            on_back_to_login=self.show_login_screen
        )
		self.current_view.pack(fill="both", expand=True)
		
	def on_app_closing(self):
		"""App close hone par pehle session terminate aur connection pool close karega"""
		try:
            # 1. Active user session close karein
			if hasattr(self, "session_manager") and self.session_manager:
				self.session_manager.terminate_session()
                
            # 2. Database connections cleanly close karein
			DBCore.close_all()
			print(" Database Pool closed safely.")
		except Exception as e:
			print(f" Closing cleanup error: {e}")
		finally:
            # 3. Window destroy karein
			self.destroy()
    
	def route_user_to_dashboard(self, user_info):
		"""
        Login successful hone par user ke role ke mutabiq 
        resprected dashboard par switch karta hai.
        """
		if self.current_view:
			self.current_view.destroy()
		
		# 🌟 1. YAHAN SESSION BANANA HAI (Database entry ke liye)
		user_id = user_info.get("id")
		if hasattr(self, "session_manager") and self.session_manager:
			session_id = self.session_manager.create_session(user_id)
			user_info["session_id"] = session_id
			print(f" Session ID create ho gaya: {session_id} for user {user_id}")

		role = str(user_info.get("role", "user")).strip().lower()
		name = user_info.get("name", "User")

		if role in ["admin", "administrator"]:
			print(f"👑 Routing to ADMIN Dashboard: {name}")
			
			# 🌟 Window size expand karein aur resizable enable karein
			self.title("Trading Ledger - Admin Dashboard")
			self.geometry("1180x720")
			self.minsize(1050, 650)
			self.resizable(True, True)
			
			# Center window on screen
			self.update_idletasks()
			
			self.current_view = AdminApp(
                self, 
                db_service=self.db,
                user_info=user_info, 
                on_logout=self.show_login_screen
            )
		else:
			print(f"👤 Routing to USER Dashboard: {name}")
			
			self.title("Trading Ledger - User Dashboard")
			self.geometry("1180x720")
			self.minsize(1050, 650)
			self.resizable(True, True)
			
			self.current_view = UserApp(
                self, 
                db_service=self.db, 
                user_info=user_info, 
                on_logout=self.show_login_screen
            )
		self.current_view.pack(fill="both", expand=True)
		
		
    

if __name__ == "__main__":
	try:
		app = MainApplication()
		app.mainloop()
	except Exception as e:
		print(f"Application Crash Error: {e}")
