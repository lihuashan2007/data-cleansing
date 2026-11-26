"""SIC screens used by the original research script."""


def valid_obs(sic: int | float) -> int:
    """Return 0 for observations excluded by the industry screen."""
    return int(bool(valid_industry(sic)) and not sic > 9000)


def identify_manufacturing(sic: int | float) -> int:
    """Return 1 for SIC codes strictly between 2000 and 4000."""
    return int(2000 < sic < 4000)


def valid_industry(sic: int | float) -> int:
    """Return 0 for the financial and utility SIC ranges."""
    return int(not (6000 < sic < 6800 or 4900 < sic < 4950))
