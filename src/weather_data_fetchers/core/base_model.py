from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    """Base model with strict configuration."""

    model_config = ConfigDict(
        extra="forbid",
    )
