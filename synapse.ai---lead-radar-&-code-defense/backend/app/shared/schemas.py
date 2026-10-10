"""
Wire-format conventions shared by every module (the single API contract).

* JSON field names are camelCase on the wire (`rawPost`, `candidateName`).
* Requests also accept snake_case (`populate_by_name`), so older clients keep working.
* Models can be built from ORM objects (`from_attributes`).
* Identifiers are UUID strings.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class FieldError(ApiModel):
    field: str
    message: str


class ErrorResponse(ApiModel):
    """Every non-2xx response has this shape."""

    detail: str            # human-readable summary (safe to show in the UI)
    code: str              # stable machine-readable code, e.g. "validation_error"
    errors: Optional[List[FieldError]] = None   # per-field problems for 422
