from dataclasses import dataclass


@dataclass
class HouseState:
    house_id: str
    pv_power_w: float
    base_load_w: float
    ev_load_w: float
    washer_load_w: float
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


class EnergyModel:
    # Fixed power draws
    EV_POWER_W = 11000  # 11 kW EV charger
    WASHER_POWER_W = 2000  # 2 kW washer

    def __init__(self, house_count: int) -> None:
        self.house_count = house_count
        self._houses = []
        for idx in range(house_count):
            self._houses.append(
                {
                    "house_id": f"house_{idx + 1}",
                    "base_load_w": 0,
                    "pv_power_w": 0,
                    "ev_on": False,
                    "washer_on": False,
                }
            )

    def update(self) -> tuple[list[HouseState], CommunityState, GridExchange]:
        house_states: list[HouseState] = []
        total_prod = 0.0
        total_cons = 0.0

        for house in self._houses:
            pv_power = house["pv_power_w"]
            base_load = house["base_load_w"]
            ev_load = self.EV_POWER_W if house["ev_on"] else 0.0
            washer_load = self.WASHER_POWER_W if house["washer_on"] else 0.0

            total_load = base_load + ev_load + washer_load
            net_power = pv_power - total_load

            total_prod += pv_power
            total_cons += total_load

            house_states.append(
                HouseState(
                    house_id=house["house_id"],
                    pv_power_w=round(pv_power, 1),
                    base_load_w=round(base_load, 1),
                    ev_load_w=round(ev_load, 1),
                    washer_load_w=round(washer_load, 1),
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
