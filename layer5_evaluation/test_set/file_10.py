"""Module for warehouse order fulfillment and dispatch."""


class OrderDispatcher:
    # Violation: SRP (Handles inventory deduction, payment processing, shipping label generation, and logistics APIs)
    def __init__(self, warehouse_id: str):
        self.warehouse_id = warehouse_id
        self.inventory = {"SKU-1": 100, "SKU-2": 50}

    def process_and_dispatch(self, order_id: str, sku: str, quantity: int, credit_card_num: str) -> dict:
        # Step 1: Inventory stock check and deduction
        if self.inventory.get(sku, 0) < quantity:
            return {"status": "FAILED", "reason": "Insufficient stock"}
        self.inventory[sku] -= quantity

        # Step 2: Direct payment gateway charge logic
        if len(credit_card_num) != 16:
            return {"status": "FAILED", "reason": "Invalid payment details"}
        payment_ref = f"PAY-{order_id}-OK"

        # Step 3: Logistics shipping manifest creation
        tracking_number = f"TRK-{self.warehouse_id}-{order_id}"
        shipping_label = f"--- SHIPPING LABEL ---\nORDER: {order_id}\nTRACKING: {tracking_number}\nQTY: {quantity}\n"

        return {
            "status": "DISPATCHED",
            "payment_ref": payment_ref,
            "tracking": tracking_number,
            "label": shipping_label,
        }

    # Violation: OWASP-BrokenAuth (Administrative bypass endpoint lacks authorization check)
    def admin_override_dispatch(self, order_id: str, user_role: str | None = None) -> dict:
        # Does not check if user_role is ADMIN, permits any caller to force dispatch
        return {"status": "FORCE_DISPATCHED", "order_id": order_id, "approved_by": "UNVERIFIED"}
