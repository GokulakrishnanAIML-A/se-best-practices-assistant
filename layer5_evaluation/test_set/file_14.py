"""Module for digital document signing and billing."""

import hashlib
import time


class DocumentSigner:
    # Violation: SRP (Handles cryptographic signing, cloud upload, and billing charges)
    def __init__(self, private_key_pem: str):
        self.private_key = private_key_pem

    def sign_document_content(self, document_bytes: bytes) -> str:
        signature = hashlib.sha256(document_bytes + self.private_key.encode()).hexdigest()
        return signature

    def upload_to_cloud_storage(self, doc_id: str, signature: str) -> str:
        cloud_url = f"https://storage.provider.com/signed_docs/{doc_id}?sig={signature}"
        return cloud_url

    def charge_customer_for_signing(self, customer_id: str, doc_count: int) -> float:
        fee_per_doc = 1.50
        total_charge = doc_count * fee_per_doc
        return total_charge

    # Violation: OWASP-BrokenAuth (Exposing secret session token in URL query parameter and audit logs)
    def create_signing_link(self, doc_id: str, auth_token: str) -> str:
        # Exposes secret session token in GET URL
        link = f"https://app.example.com/sign?doc_id={doc_id}&auth_token={auth_token}"
        print(f"[AUDIT LOG] Created signing URL with token: {link}")
        return link
