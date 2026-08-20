"""
Sample Python file for testing the SE Best Practices Assistant.

This file intentionally contains common violations across:
- SOLID Principles (SRP, OCP, DIP)
- OWASP Security (SQL Injection, hardcoded credentials)
- Clean Code (high complexity, long functions, poor naming)
- Static Analysis (Bandit, Radon, AST flags)
"""

import sqlite3
import subprocess
import hashlib

# -----------------------------------------------------------------------
# VIOLATION: Hardcoded credentials (OWASP A07 - Identification & Auth Failures)
# -----------------------------------------------------------------------
DB_HOST = "localhost"
DB_USER = "admin"
DB_PASSWORD = "supersecret123"   # Bandit: hardcoded password
SECRET_KEY = "myapp-secret-key"  # Bandit: hardcoded secret


# -----------------------------------------------------------------------
# VIOLATION: God Class - SRP Violation
# UserManager handles auth, DB access, email, and logging all in one class.
# -----------------------------------------------------------------------
class UserManager:
    """Manages users, authentication, emailing, and order processing."""

    def __init__(self):
        self.conn = sqlite3.connect("app.db")
        self.cursor = self.conn.cursor()
        self.log_file = open("app.log", "a")  # resource leak (never closed)

    # VIOLATION: SQL Injection (OWASP A03 - Injection)
    def get_user(self, username):
        query = f"SELECT * FROM users WHERE username = '{username}'"
        self.cursor.execute(query)  # Bandit: sql injection via string formatting
        return self.cursor.fetchone()

    # VIOLATION: SQL Injection + poor naming
    def upd(self, u, p):
        sql = "UPDATE users SET password='" + p + "' WHERE username='" + u + "'"
        self.cursor.execute(sql)  # Bandit: string concatenation in SQL
        self.conn.commit()

    # VIOLATION: Hardcoded hash algorithm (MD5 is weak)
    def hash_password(self, password):
        return hashlib.md5(password.encode()).hexdigest()  # Bandit: use of MD5

    # VIOLATION: Command injection (OWASP A03)
    def send_notification(self, email, msg):
        cmd = f"echo '{msg}' | mail -s 'Notification' {email}"
        subprocess.call(cmd, shell=True)  # Bandit: shell=True with user input

    # VIOLATION: High cyclomatic complexity (Radon CC > 10)
    # VIOLATION: Long function (> 50 lines)
    # VIOLATION: OCP - requires modification for each new discount type
    def calculate_order_total(self, user_type, items, coupon_code, is_vip, region, season):
        total = 0
        discount = 0

        for item in items:
            if item["category"] == "electronics":
                if item["qty"] > 10:
                    total += item["price"] * item["qty"] * 0.85
                elif item["qty"] > 5:
                    total += item["price"] * item["qty"] * 0.90
                else:
                    total += item["price"] * item["qty"]
            elif item["category"] == "clothing":
                if season == "winter":
                    total += item["price"] * item["qty"] * 0.70
                elif season == "summer":
                    total += item["price"] * item["qty"] * 0.80
                else:
                    total += item["price"] * item["qty"]
            elif item["category"] == "food":
                total += item["price"] * item["qty"]
            else:
                total += item["price"] * item["qty"]

        if user_type == "premium":
            discount += 0.10
        elif user_type == "vip":
            discount += 0.20
        elif user_type == "employee":
            discount += 0.30

        if is_vip:
            discount += 0.05

        if coupon_code == "SAVE10":
            discount += 0.10
        elif coupon_code == "SAVE20":
            discount += 0.20
        elif coupon_code == "HALFOFF":
            discount += 0.50

        if region == "EU":
            tax = total * 0.20
        elif region == "US":
            tax = total * 0.08
        elif region == "IN":
            tax = total * 0.18
        else:
            tax = total * 0.15

        total = total - (total * discount) + tax
        self.log_file.write(f"Order total: {total}\n")
        return total

    # VIOLATION: DIP - directly instantiates concrete EmailService instead of injecting
    def register_user(self, username, password, email):
        hashed = self.hash_password(password)
        # SQL injection via f-string
        self.cursor.execute(
            f"INSERT INTO users (username, password, email) VALUES ('{username}', '{hashed}', '{email}')"
        )
        self.conn.commit()
        # Direct concrete instantiation
        emailer = EmailService()  # DIP violation
        emailer.send_welcome(email)

    # VIOLATION: ISP - forces all callers to depend on admin-only methods
    def delete_all_users(self):
        self.cursor.execute("DELETE FROM users")
        self.conn.commit()

    def reset_database(self):
        self.cursor.execute("DROP TABLE IF EXISTS users")
        self.conn.commit()


# -----------------------------------------------------------------------
# VIOLATION: No interface abstraction (DIP, ISP)
# EmailService is a concrete dependency instantiated directly above.
# -----------------------------------------------------------------------
class EmailService:
    def send_welcome(self, email):
        cmd = f"sendmail {email}"
        subprocess.call(cmd, shell=True)  # Bandit: another shell injection

    def send_reset(self, email, token):
        # VIOLATION: token exposed in URL without expiry or HTTPS enforcement
        link = f"http://myapp.com/reset?token={token}&email={email}"
        print(f"Send this link: {link}")


# -----------------------------------------------------------------------
# VIOLATION: Poor naming, magic numbers, no docstrings (Clean Code)
# -----------------------------------------------------------------------
def p(x, y, z):
    """Compute price with tax and fee."""
    return x * y + (x * y * z / 100) + 9.99  # magic number 9.99


def f(lst):
    r = []
    for i in lst:
        if i > 0:
            r.append(i * 2)
    return r


# -----------------------------------------------------------------------
# Example usage (not executable without a real DB)
# -----------------------------------------------------------------------
if __name__ == "__main__":
    mgr = UserManager()
    user = mgr.get_user("admin' OR '1'='1")  # deliberate injection attempt string
    print(user)
    total = mgr.calculate_order_total(
        user_type="premium",
        items=[
            {"category": "electronics", "qty": 12, "price": 499.99},
            {"category": "clothing", "qty": 3, "price": 49.99},
        ],
        coupon_code="SAVE20",
        is_vip=True,
        region="IN",
        season="winter",
    )
    print(f"Order Total: {total}")
