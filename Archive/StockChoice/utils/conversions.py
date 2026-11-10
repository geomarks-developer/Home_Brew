
# ============================================================
# HELPERS
# ============================================================

def decimal_to_pct(value):

    if value is None:
        return None

    return value * 100


def normalize_debt_to_equity(value):

    if value is None:
        return None

    if value > 10:
        return value / 100

    return value