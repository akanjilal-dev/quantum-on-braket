"""
quantum/cost.py
===============
The cost guard. Quantum hardware is metered per-task and per-shot, so this is
the FinOps discipline applied to QPU access: estimate the spend, fail closed,
and never submit a paid job the operator did not explicitly authorize.

The pricing below is *approximate* Amazon Braket on-demand pricing and WILL
drift -- re-verify against the Braket pricing page before you rely on it (the
suite's maintenance cadence re-checks ARNs and pricing quarterly). The guard's
job is not to be exact to the cent; it is to make spend explicit and bounded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

# Authorize a paid run by setting this to a dollar ceiling, e.g.
#   export BRAKET_ALLOW_QPU_SPEND=5.00
ALLOW_ENV = "BRAKET_ALLOW_QPU_SPEND"


@dataclass(frozen=True)
class Pricing:
    per_task_usd: float
    per_shot_usd: float
    label: str


# Free, always-available, no credentials. The default everywhere in this repo.
LOCAL_FREE = Pricing(0.0, 0.0, "LocalSimulator (free)")

# Approximate Braket on-demand QPU rates (USD). Per-task fee + per-shot fee.
# Matched against a device ARN by vendor substring. VERIFY before real runs.
_QPU_PRICING: dict[str, Pricing] = {
    "ionq": Pricing(0.30, 0.03000, "IonQ"),
    "rigetti": Pricing(0.30, 0.00090, "Rigetti"),
    "iqm": Pricing(0.30, 0.00145, "IQM"),
    "quera": Pricing(0.30, 0.01000, "QuEra"),
}
# Used when a QPU ARN doesn't match a known vendor -- deliberately not cheap, so
# an unknown device errs toward caution rather than under-estimating spend.
_GENERIC_QPU = Pricing(0.30, 0.01000, "QPU (generic estimate)")

_LOCAL_ALIASES = {"local", "simulator", "sim"}


class QpuSpendError(RuntimeError):
    """Raised when a paid QPU run is unauthorized or exceeds the budget ceiling."""


def pricing_for(device_arn: str) -> Pricing:
    """Resolve a pricing model from a device identifier or ARN."""
    a = device_arn.lower()
    if a in _LOCAL_ALIASES:
        return LOCAL_FREE
    for vendor, pricing in _QPU_PRICING.items():
        if vendor in a:
            return pricing
    return _GENERIC_QPU


def estimate_cost(pricing: Pricing, shots: int) -> float:
    """Estimated USD for `shots` shots: per-task fee + per-shot fee * shots."""
    if shots <= 0:
        return 0.0
    return round(pricing.per_task_usd + shots * pricing.per_shot_usd, 6)


def authorize_qpu_run(
    device_arn: str,
    pricing: Pricing,
    shots: int,
    *,
    env: Mapping[str, str] = os.environ,
) -> float:
    """Gate a paid run. Returns the estimate if allowed; raises otherwise.

    Free runs (estimate <= 0) are always allowed. A paid run requires
    BRAKET_ALLOW_QPU_SPEND to be set to a dollar ceiling that covers the
    estimate; anything else fails closed before a single shot is submitted.
    """
    estimate = estimate_cost(pricing, shots)
    if estimate <= 0:
        return estimate

    raw = env.get(ALLOW_ENV)
    if raw is None:
        raise QpuSpendError(
            f"Refusing to submit to {pricing.label} ({device_arn}): estimated "
            f"${estimate:.4f} for {shots} shots "
            f"(per-task ${pricing.per_task_usd:.2f} + {shots}×${pricing.per_shot_usd:.5f}). "
            f"This is a paid QPU. Authorize by setting {ALLOW_ENV} to a dollar "
            f"ceiling, e.g. {ALLOW_ENV}={estimate:.2f}"
        )
    try:
        ceiling = float(raw)
    except ValueError as exc:
        raise QpuSpendError(f"{ALLOW_ENV}={raw!r} is not a dollar amount.") from exc

    if estimate > ceiling:
        raise QpuSpendError(
            f"Estimated ${estimate:.4f} exceeds your ceiling {ALLOW_ENV}=${ceiling:.2f}. "
            f"Aborting before any spend -- raise the ceiling or lower the shot count."
        )
    return estimate
