"""Decide which model call failures deserve another try."""

from openai import APIConnectionError, APIStatusError

REQUEST_TIMEOUT_STATUS = 408
CONFLICT_STATUS = 409
RATE_LIMIT_STATUS = 429
SERVER_ERROR_STATUS = 500

RETRYABLE_STATUSES = frozenset({REQUEST_TIMEOUT_STATUS, CONFLICT_STATUS, RATE_LIMIT_STATUS})


def should_retry(exc: BaseException) -> bool:
    """True when the failure may pass if the call is tried again."""
    if isinstance(exc, APIConnectionError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in RETRYABLE_STATUSES or exc.status_code >= SERVER_ERROR_STATUS
    return False
