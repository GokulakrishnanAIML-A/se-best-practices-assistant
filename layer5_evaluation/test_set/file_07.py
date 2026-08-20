"""Module for user authentication and session token generation."""

import sqlite3
import time


class AuthService:
    # Violation: OWASP-BrokenAuth (Hardcoded sensitive secret key in source code)
    JWT_SECRET_KEY = "hardcoded_super_secret_jwt_signing_key_12345678"

    def __init__(self):
        # Violation: DIP (Direct hardcoded database driver initialization)
        self.db_conn = sqlite3.connect("production_auth.db")

    def login(self, username: str, raw_password: str) -> dict:
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT id, password, role FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            return {"error": "Invalid credentials"}

        user_id, stored_password, role = row

        # Violation: OWASP-BrokenAuth (Plaintext password comparison without hashing or salt)
        if stored_password != raw_password:
            return {"error": "Invalid credentials"}

        session_payload = {
            "sub": user_id,
            "role": role,
            "exp": time.time() + 3600,
            "sig": self.JWT_SECRET_KEY,
        }
        return {"status": "authenticated", "session": session_payload}
