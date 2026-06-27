"""API request schemas."""

from pydantic import BaseModel


class EnvToPathwayRequest(BaseModel):
    env_factor: str


class CausalChainRequest(BaseModel):
    source: str
    target: str
    max_depth: int = 10
