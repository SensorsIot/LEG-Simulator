import math
import random
import time
from dataclasses import dataclass


@dataclass
class HouseState:
    house_id: str
    pv_power_w: float
    base_load_w: float
    flex_load_w: float
    net_power_w: float


@dataclass
class CommunityState:
    total_production_w: float
    total_consumption_w: float
    net_community_power_w: float


@dataclass
class GridExchange:
    grid_import_w: float
    grid_export_w: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class EnergyModel:
    def __init__(self, house_count: int, flex_load_probability: float) -> None:
        self.house_count = house_count
        self.flex_load_probability = flex_load_probability
        self._rng = random.Random(42)
        self._houses = []
        now = time.time()
        for idx in range(house_count):
            base_load = self._rng.uniform(300, 700)
            pv_peak = self._rng.uniform(1500, 4500)
            phase = self._rng.uniform(0, math.tau)
            self._houses.append(
                {
                    "house_id": f"house_{idx + 1}",
                    "base_load_w": base_load,
                    "pv_peak_w": pv_peak,
                    "pv_phase": phase,
                    "flex_load_w": 0.0,
                    "last_flex_toggle": now,
                    "flex_active": False,
                }
            )

    def update(self, pv_variation_enabled: bool) -> tuple[list[HouseState], CommunityState, GridExchange]:
        now = time.time()
        house_states: list[HouseState] = []
        total_prod = 0.0
        total_cons = 0.0

        for house in self._houses:
            pv_power = house["pv_peak_w"]
            if pv_variation_enabled:
                pv_wave = (math.sin(now / 15.0 + house["pv_phase"]) + 1.0) / 2.0
                pv_noise = self._rng.uniform(-0.08, 0.08)
                pv_power *= _clamp(pv_wave + pv_noise, 0.0, 1.0)

            base_load = house["base_load_w"]
            flex_load = self._update_flex_load(house, now)

            total_load = base_load + flex_load
            net_power = pv_power - total_load

            total_prod += pv_power
            total_cons += total_load

            house_states.append(
                HouseState(
                    house_id=house["house_id"],
                    pv_power_w=round(pv_power, 1),
                    base_load_w=round(base_load, 1),
                    flex_load_w=round(flex_load, 1),
                    net_power_w=round(net_power, 1),
                )
            )

        net_community = total_prod - total_cons
        community_state = CommunityState(
            total_production_w=round(total_prod, 1),
            total_consumption_w=round(total_cons, 1),
            net_community_power_w=round(net_community, 1),
        )

        grid_exchange = GridExchange(
            grid_import_w=round(abs(net_community), 1) if net_community < 0 else 0.0,
            grid_export_w=round(net_community, 1) if net_community > 0 else 0.0,
        )

        return house_states, community_state, grid_exchange

    def _update_flex_load(self, house: dict, now: float) -> float:
        if now - house["last_flex_toggle"] > 3.0:
            house["last_flex_toggle"] = now
            if house["flex_active"]:
                if self._rng.random() < 0.3:
                    house["flex_active"] = False
            else:
                if self._rng.random() < self.flex_load_probability:
                    house["flex_active"] = True
                    house["flex_load_w"] = self._rng.uniform(1500, 7000)

        if not house["flex_active"]:
            return 0.0

        return house["flex_load_w"]
