from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Any] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details

class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(message, "NOT_FOUND", status.HTTP_404_NOT_FOUND, details)

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized", details: Optional[Any] = None):
        super().__init__(message, "UNAUTHORIZED", status.HTTP_401_UNAUTHORIZED, details)

class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden", details: Optional[Any] = None):
        super().__init__(message, "FORBIDDEN", status.HTTP_403_FORBIDDEN, details)

class BusinessRuleException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, "BUSINESS_RULE_VIOLATION", status.HTTP_400_BAD_REQUEST, details)
