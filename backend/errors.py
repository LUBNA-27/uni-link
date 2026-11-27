"""Uniform API error type. Rendered as {"code", "message", "current_revision"?} (the frontend parser's
format), plus a nested {"error": {...}} copy for older clients. Never a stack trace."""
from __future__ import annotations

from typing import Optional


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, current_revision: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.current_revision = current_revision
