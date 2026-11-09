class TgtgLoginError(Exception):
    pass


class TgtgAPIError(Exception):
    pass


class TgtgProtectionError(TgtgAPIError):
    """Bot protection rejected the request; no automatic retry was attempted."""


class TgtgPollingError(Exception):
    pass
