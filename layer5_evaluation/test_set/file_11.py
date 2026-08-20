"""Module for vehicle fleet telemetry and refueling."""


class FuelVehicle:
    def __init__(self, make: str, model: str, tank_capacity: float):
        self.make = make
        self.model = model
        self.tank_capacity = tank_capacity
        self.fuel_level = 0.0

    def fill_gasoline(self, liters: float) -> float:
        # Violation: poor-naming (v, amt, tmp_cap, res_val)
        v = self.fuel_level
        amt = liters
        tmp_cap = self.tank_capacity
        if v + amt <= tmp_cap:
            self.fuel_level += amt
            res_val = self.fuel_level
        else:
            self.fuel_level = tmp_cap
            res_val = self.fuel_level
        return res_val


class ElectricCar(FuelVehicle):
    def __init__(self, make: str, model: str, battery_capacity_kwh: float):
        super().__init__(make, model, tank_capacity=0.0)
        self.battery_capacity = battery_capacity_kwh
        self.battery_charge = 0.0

    # Violation: LSP (Subclass breaks base class contract by refusing the fundamental base method)
    def fill_gasoline(self, liters: float) -> float:
        raise NotImplementedError("Electric vehicles cannot accept gasoline refueling")

    def charge_battery(self, kwh: float) -> float:
        self.battery_charge = min(self.battery_capacity, self.battery_charge + kwh)
        return self.battery_charge
