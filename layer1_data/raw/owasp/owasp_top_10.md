# OWASP Top 10 Web Application Security Risks

Authoritative reference guidelines for application security and secure coding practices.

## A01:2021 - Broken Access Control
Access control enforces policy such that users cannot act outside of their intended permissions. Failures typically lead to unauthorized information disclosure, modification, or destruction of all data, or performing a business function outside the user's limits.
- **Violation Indicators:** Bypassing access control checks by modifying the URL (parameter tampering), internal application state, or the HTML page; elevating privileges (acting as an admin when logged in as a user); insecure direct object references (IDOR); metadata manipulation such as replaying or tampering with JWT tokens; missing CORS configuration or access control checks on API endpoints.
- **Remediation:** Enforce access control mechanisms in server-side code or trusted serverless APIs. Deny by default. Implement access control lists and role-based access control (RBAC) systematically. Validate that the requesting user owns the requested record on every mutation and query.
- **Citation:** OWASP Top 10:2021 — A01 Broken Access Control.

## A02:2021 - Cryptographic Failures
Failures related to cryptography (previously known as Sensitive Data Exposure) frequently lead to sensitive data exposure or system compromise.
- **Violation Indicators:** Transmitting sensitive data (passwords, credit cards, health records, personal info) in clear text over HTTP or FTP; using old or weak cryptographic algorithms (MD5, SHA1, RC4, DES); using default or weak cryptographic keys; lack of proper key rotation; storing plaintext passwords instead of adaptive salted hashes (bcrypt, Argon2, scrypt, PBKDF2).
- **Remediation:** Classify data processed, stored, or transmitted by an application. Apply encryption in transit with secure protocols like TLS 1.3. Encrypt all sensitive data at rest using strong modern algorithms (AES-GCM-256). Always hash passwords using Argon2id or bcrypt with strong work factors.
- **Citation:** OWASP Top 10:2021 — A02 Cryptographic Failures.

## A03:2021 - Injection
Injection flaws, such as SQL, NoSQL, OS command, LDAP, and expression language injection, occur when untrusted data is sent to an interpreter as part of a command or query.
- **Violation Indicators:** User-supplied data is directly concatenated, formatted, or interpolated into dynamic queries or system execution strings (e.g., `cursor.execute("SELECT * FROM users WHERE id = '" + user_id + "'")` or `subprocess.run(f"ping {ip_input}", shell=True)`).
- **Remediation:** The preferred defense is the use of a safe API, which avoids the use of the interpreter entirely or provides a parameterized interface (e.g., parameterized SQL queries / prepared statements or ORM queries). Use positive server-side input validation and escape special characters.
- **Citation:** OWASP Top 10:2021 — A03 Injection.

## A04:2021 - Insecure Design
Insecure design represents missing or ineffective control design. It cannot be fixed by a perfect implementation because by definition, needed security controls were never created to defend against specific attacks.
- **Violation Indicators:** Missing rate limiting on password reset or payment endpoints; lack of threat modeling during architectural design; unrestrained resource consumption allowing Denial of Service (DoS); trusting client-side pricing or validation checks without server validation.
- **Remediation:** Integrate threat modeling into user stories and design phases. Establish and use a secure development lifecycle with AppSec professionals. Limit resource consumption per user/tenant.
- **Citation:** OWASP Top 10:2021 — A04 Insecure Design.

## A05:2021 - Security Misconfiguration
Security misconfiguration occurs when security controls are inaccurately configured or left at default settings.
- **Violation Indicators:** Unnecessary features enabled (e.g., unnecessary ports, services, pages, accounts, or privileges); default accounts and passwords unchanged; debug mode enabled in production exposing detailed stack traces (`DEBUG = True` in Django/Flask); permissive Cross-Origin Resource Sharing (CORS) headers like `Access-Control-Allow-Origin: *` with credentials.
- **Remediation:** A repeatable hardening process should be automated. Disable unnecessary features, components, and frameworks. Ensure debug mode is disabled in production environments. Send security headers (CSP, HSTS, X-Content-Type-Options).
- **Citation:** OWASP Top 10:2021 — A05 Security Misconfiguration.

## A07:2021 - Identification and Authentication Failures
Confirmation of the user's identity, authentication, and session management is critical to protect against authentication-related attacks.
- **Violation Indicators:** Permitting automated brute-force credential stuffing without rate-limiting or CAPTCHA; allowing weak or default passwords; exposing session IDs in URLs; not invalidating session tokens upon logout; weak session timeout policies.
- **Remediation:** Implement multi-factor authentication (MFA). Implement weak password checks against top breached password lists. Enforce rate limiting on authentication endpoints. Use secure, built-in session managers.
- **Citation:** OWASP Top 10:2021 — A07 Identification and Authentication Failures.

## A10:2021 - Server-Side Request Forgery (SSRF)
SSRF flaws occur whenever a web application is fetching a remote resource without validating the user-supplied URL.
- **Violation Indicators:** The server accepts a full URL parameter from an end user and makes an HTTP request to that URL without validating the destination host or protocol, allowing attackers to access internal cloud metadata services (e.g., `http://169.254.169.254/`) or internal intranet services.
- **Remediation:** Enforce strict URL allowlists and sanitize input. Disable HTTP redirections on server HTTP clients. Segment remote resource fetching functionality into isolated network zones.
- **Citation:** OWASP Top 10:2021 — A10 Server-Side Request Forgery.
