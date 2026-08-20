"""Module for tier-based customer discount calculations."""


class DiscountCalculator:
    # Violation: OCP & high-complexity (Radon CC > 13 with deep nested conditionals)
    def compute_discount(
        self,
        base_price: float,
        customer_tier: str,
        is_first_order: bool,
        coupon_code: str | None,
        country: str,
    ) -> float:
        discount = 0.0

        if customer_tier == "PLATINUM":
            if is_first_order:
                discount = base_price * 0.30
            else:
                if country == "US":
                    discount = base_price * 0.25
                elif country == "EU":
                    discount = base_price * 0.22
                else:
                    discount = base_price * 0.20
        elif customer_tier == "GOLD":
            if is_first_order:
                discount = base_price * 0.20
            else:
                if coupon_code == "SUMMER20":
                    discount = base_price * 0.18
                else:
                    discount = base_price * 0.15
        elif customer_tier == "SILVER":
            if coupon_code == "WELCOME10":
                discount = base_price * 0.10
            else:
                discount = base_price * 0.05
        elif customer_tier == "BRONZE":
            discount = base_price * 0.02
        else:
            discount = 0.0

        return max(0.0, base_price - discount)
