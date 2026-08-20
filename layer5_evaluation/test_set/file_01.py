"""Module for user management and registration."""

import sqlite3
import smtplib
from email.mime.text import MIMEText


class UserManager:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path

    def register_user(self, username: str, email: str, raw_password: str) -> bool:
        # Violation: OWASP-Injection (raw string concatenation into SQL query)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = "SELECT * FROM users WHERE username = '" + username + "' AND email = '" + email + "'"
        cursor.execute(query)
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return False

        # Violation: SRP (UserManager directly handles password hashing, DB insertion, and email dispatch)
        insert_sql = "INSERT INTO users (username, email, password) VALUES ('" + username + "', '" + email + "', '" + raw_password + "')"
        cursor.execute(insert_sql)
        conn.commit()
        conn.close()

        # Send welcome email formatting and SMTP dispatch
        self.send_welcome_email(email, username)
        return True

    def send_welcome_email(self, email: str, username: str) -> None:
        html_body = f"<html><body><h1>Welcome, {username}!</h1><p>Your account is ready.</p></body></html>"
        msg = MIMEText(html_body, "html")
        msg["Subject"] = "Welcome to Our Platform"
        msg["From"] = "no-reply@platform.com"
        msg["To"] = email

        server = smtplib.SMTP("smtp.example.com", 587)
        server.send_message(msg)
        server.quit()

    def update_user_status(self, user_id: int, status: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET status = '{status}' WHERE id = {user_id}")
        conn.commit()
        conn.close()
