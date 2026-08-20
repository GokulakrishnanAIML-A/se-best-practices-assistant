"""Module for order payment processing."""


class ConcreteStripeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def charge(self, amount: float, token: str) -> dict:
        return {"status": "success", "charge_id": "ch_12345"}


class PaymentProcessor:
    def __init__(self):
        # Violation: DIP (Direct instantiation of low-level concrete SDK client instead of abstraction)
        self.stripe_client = ConcreteStripeClient(api_key="sk_live_1234567890abcdef")

    def calculate_final_amount(self, base_amount: float, payment_method: str) -> float:
        # Violation: OCP (Hardcoded type checks instead of strategy/polymorphism)
        if payment_method == "CREDIT_CARD":
            fee = base_amount * 0.029 + 0.30
            return base_amount + fee
        elif payment_method == "PAYPAL":
            fee = base_amount * 0.034 + 0.49
            return base_amount + fee
        elif payment_method == "CRYPTO":
            fee = base_amount * 0.010
            return base_amount + fee
        elif payment_method == "BANK_TRANSFER":
            return base_amount
        elif payment_method == "KLARNA":
            fee = base_amount * 0.045
            return base_amount + fee
        else:
            raise ValueError(f"Unsupported payment method: {payment_method}")

    def execute_charge(self, base_amount: float, payment_method: str, token: str) -> dict:
        total = self.calculate_final_amount(base_amount, payment_method)
        return self.stripe_client.charge(total, token)
