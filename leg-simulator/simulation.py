from dataclasses import dataclass

from model import CommunityState, EnergyModel, GridExchange, HouseState


@dataclass
class SimulationSnapshot:
    houses: list[HouseState]
    community: CommunityState
    grid: GridExchange


class Simulation:
    def __init__(self, house_count: int) -> None:
        self.model = EnergyModel(house_count)

    def tick(self) -> SimulationSnapshot:
        houses, community, grid = self.model.update()
        return SimulationSnapshot(houses=houses, community=community, grid=grid)
