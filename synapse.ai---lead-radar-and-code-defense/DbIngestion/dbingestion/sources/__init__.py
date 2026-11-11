"""Source adapters: turn an external input into typed, validated records (or structured rejections)."""

from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class SourceItem(Generic[T]):
    """One input record: either a validated `value` or an `error` explaining why it was rejected."""

    index: int
    value: Optional[T] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw: Any = None
