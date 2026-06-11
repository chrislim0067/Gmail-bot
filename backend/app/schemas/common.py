"""Shared Pydantic schemas."""

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"
    errors: list[str] = Field(default_factory=list)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
    pages: int


class PreflightCheckItem(BaseModel):
    name: str
    passed: bool
    message: str


class PreflightCheckResponse(BaseModel):
    passed: bool
    checks: list[PreflightCheckItem]


class MessageResponse(BaseModel):
    status: str
    message: str | None = None


class IDMixin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
