"""Module for shipping logistics and parcel rate calculations."""


class Package:
    def __init__(self, weight_kg: float, width: float, height: float, depth: float):
        self.weight_kg = weight_kg
        self.width = width
        self.height = height
        self.depth = depth


class FragilePackage(Package):
    def __init__(self, weight_kg: float, width: float, height: float, depth: float, insurance_val: float):
        super().__init__(weight_kg, width, height, depth)
        self.insurance_val = insurance_val


class PerishablePackage(Package):
    def __init__(self, weight_kg: float, width: float, height: float, depth: float, temp_celsius: float):
        super().__init__(weight_kg, width, height, depth)
        self.temp_celsius = temp_celsius


class ShippingRateCalculator:
    # Violation: OCP (isinstance type checking) & high-complexity (nested conditionals)
    def calculate_total_rate(self, packages: list[Package], destination_zone: str) -> float:
        total_rate = 0.0

        for pkg in packages:
            volumetric_weight = (pkg.width * pkg.height * pkg.depth) / 5000.0
            billable_weight = max(pkg.weight_kg, volumetric_weight)

            if destination_zone == "ZONE_A":
                base_rate = billable_weight * 5.0
            elif destination_zone == "ZONE_B":
                base_rate = billable_weight * 8.5
            elif destination_zone == "INTERNATIONAL":
                base_rate = billable_weight * 15.0
            else:
                base_rate = billable_weight * 12.0

            # Violation: OCP (Type-checking subclasses directly with isinstance)
            if isinstance(pkg, FragilePackage):
                if pkg.insurance_val > 1000:
                    base_rate += pkg.insurance_val * 0.05 + 20.0
                else:
                    base_rate += pkg.insurance_val * 0.02 + 5.0
            elif isinstance(pkg, PerishablePackage):
                if pkg.temp_celsius < 0:
                    base_rate += 30.0  # Deep freeze
                else:
                    base_rate += 15.0  # Refrigerated

            total_rate += base_rate

        return total_rate
