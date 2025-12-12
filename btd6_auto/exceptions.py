"""Custom exceptions for BTD6 automation errors."""


class UpgradeActionError(Exception):
    """Base exception for upgrade action failures."""
    pass


class UpgradeVerificationError(UpgradeActionError):
    """Raised when upgrade verification fails after all retries."""
    pass


class UpgradeStateError(UpgradeActionError):
    """Raised for inconsistent upgrade state conditions."""
    pass