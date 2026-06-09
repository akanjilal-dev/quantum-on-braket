"""
tests/test_cost.py
==================
The cost guard is a security/FinOps control, so it gets tested like one: a paid
QPU run must fail closed unless it is explicitly authorized and within budget.
The local simulator must always be free and unconditional.
"""

import pytest

from quantum.cost import (
    LOCAL_FREE,
    QpuSpendError,
    authorize_qpu_run,
    estimate_cost,
    pricing_for,
)

IONQ_ARN = "arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1"


def test_local_is_free_and_unconditional():
    assert estimate_cost(LOCAL_FREE, 1000) == 0.0
    # No env, no ceiling -- still allowed, because it costs nothing.
    assert authorize_qpu_run("local", LOCAL_FREE, 1000, env={}) == 0.0


def test_pricing_resolves_vendor_from_arn():
    assert pricing_for(IONQ_ARN).label == "IonQ"
    assert pricing_for("local").label.startswith("LocalSimulator")
    assert pricing_for("arn:.../qpu/unknownvendor/X").label.startswith("QPU")


def test_qpu_estimate_matches_formula():
    pricing = pricing_for(IONQ_ARN)
    assert estimate_cost(pricing, 1000) == pytest.approx(0.30 + 1000 * 0.03)


def test_paid_run_blocked_without_authorization():
    pricing = pricing_for(IONQ_ARN)
    with pytest.raises(QpuSpendError):
        authorize_qpu_run(IONQ_ARN, pricing, 1000, env={})


def test_paid_run_blocked_over_ceiling():
    pricing = pricing_for(IONQ_ARN)
    with pytest.raises(QpuSpendError):
        # Estimate is ~$30.30; a $1 ceiling must abort.
        authorize_qpu_run(IONQ_ARN, pricing, 1000, env={"BRAKET_ALLOW_QPU_SPEND": "1.00"})


def test_paid_run_allowed_within_ceiling():
    pricing = pricing_for(IONQ_ARN)
    est = authorize_qpu_run(IONQ_ARN, pricing, 1000, env={"BRAKET_ALLOW_QPU_SPEND": "100"})
    assert est == pytest.approx(30.30)


def test_non_numeric_ceiling_rejected():
    pricing = pricing_for(IONQ_ARN)
    with pytest.raises(QpuSpendError):
        authorize_qpu_run(IONQ_ARN, pricing, 10, env={"BRAKET_ALLOW_QPU_SPEND": "lots"})
