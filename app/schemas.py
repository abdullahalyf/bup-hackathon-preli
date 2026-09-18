"""Public request validation. Keep this aligned with docs/CONTRACTS.md."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Hour(StrictModel):
    hour: int = Field(ge=0, le=23, strict=True)
    demand_kwh: float = Field(ge=0, allow_inf_nan=False)
    solar_kwh: float = Field(ge=0, allow_inf_nan=False)
    tariff_bdt_per_kwh: float = Field(ge=0, allow_inf_nan=False)


class Battery(StrictModel):
    capacity_kwh: float = Field(ge=0, allow_inf_nan=False)
    initial_energy_kwh: float = Field(ge=0, allow_inf_nan=False)
    minimum_energy_kwh: float = Field(ge=0, allow_inf_nan=False)
    max_charge_kwh_per_hour: float = Field(ge=0, allow_inf_nan=False)
    max_discharge_kwh_per_hour: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def check_energy_range(self):
        if not self.minimum_energy_kwh <= self.initial_energy_kwh <= self.capacity_kwh:
            raise ValueError("battery energy must satisfy minimum <= initial <= capacity")
        return self


class OptimizeRequest(StrictModel):
    scenario_id: str = Field(min_length=1)
    operator_notes: list[str] = Field(min_length=1, max_length=3)
    hours: list[Hour] = Field(min_length=24, max_length=24)
    battery: Battery

    @field_validator("scenario_id")
    @classmethod
    def check_scenario_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scenario_id must not be blank")
        return value

    @field_validator("operator_notes")
    @classmethod
    def check_notes(cls, values: list[str]) -> list[str]:
        if any(not note.strip() for note in values):
            raise ValueError("operator notes must not be blank")
        return values

    @model_validator(mode="after")
    def check_hours(self):
        if {entry.hour for entry in self.hours} != set(range(24)):
            raise ValueError("hours must contain each hour from 0 through 23 exactly once")
        return self
