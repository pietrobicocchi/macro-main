from typing import Literal

from pydantic import BaseModel


class Consumption(BaseModel):
    name: Literal[
        "AutoregressiveGovernmentConsumptionSetter",
        "AutoregressiveGrowthGovernmentConsumptionSetter",
        "ConstantGrowthGovernmentConsumptionSetter",
        "ExogenousGovernmentConsumptionSetter",
    ] = "AutoregressiveGrowthGovernmentConsumptionSetter"  # MD16: AR(1) on growth rates of CPI-deflated spending
    path_name: str = "consumption"
    parameters: dict = {"consistency": 1.0, "deflator": "cpi"}


class GovernmentFunctions(BaseModel):
    consumption: Consumption = Consumption()


class GovernmentEntitiesConfiguration(BaseModel):
    functions: GovernmentFunctions = GovernmentFunctions()
