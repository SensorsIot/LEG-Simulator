from dataclasses import dataclass

from model import CommunityState, EnergyModel, GridExchange, HouseState


@dataclass
class SimulationSnapshot:
    houses: list[HouseState]
    community: CommunityState
    grid: GridExchange


class Simulation:
    def __init__(self, house_count: int, flex_load_probability: float, pv_variation: bool) -> None:
        self.pv_variation = pv_variation
        self.model = EnergyModel(house_count, flex_load_probability)

    def tick(self) -> SimulationSnapshot:
        houses, community, grid = self.model.update(self.pv_variation)
        return SimulationSnapshot(houses=houses, community=community, grid=grid)
