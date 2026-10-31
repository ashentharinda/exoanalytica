from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=64)


class Stellar(BaseModel):
    radius_rsun: Optional[float] = Field(None, gt=0.08, le=100)
    mass_msun: Optional[float] = Field(None, gt=0.08, le=100)
    teff_k: Optional[float] = Field(None, ge=2300, le=50000)


class FetchRequest(BaseModel):
    target: str = Field(pattern=r"^(TIC|KIC|EPIC) ?\d{1,10}$")
    mission: Literal["TESS", "Kepler"]
    stellar: Stellar = Stellar()
    injection: bool = False
