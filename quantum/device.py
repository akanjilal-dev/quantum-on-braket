"""
quantum/device.py
=================
Device selection and the run path. The default is the free local simulator;
set BRAKET_DEVICE to a QPU ARN to run on real hardware. Every paid run passes
through the cost guard (quantum/cost.py) BEFORE a task is ever submitted.

    # free, no credentials:
    python -m quantum.main

    # real hardware (one flag) -- still gated by the cost guard:
    export BRAKET_DEVICE=arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1
    export BRAKET_ALLOW_QPU_SPEND=5.00
    python -m quantum.main
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from braket.circuits import Circuit

from quantum.cost import authorize_qpu_run, estimate_cost, pricing_for

LOCAL = "local"
_LOCAL_ALIASES = {"local", "simulator", "sim", ""}


@dataclass
class RunResult:
    counts: dict[str, int]
    shots: int
    device: str
    estimated_cost_usd: float


def selected_device_arn() -> str:
    """The device to use: BRAKET_DEVICE if set, else the local simulator."""
    return os.environ.get("BRAKET_DEVICE", LOCAL).strip() or LOCAL


def is_local(device_arn: str) -> bool:
    return device_arn.lower() in _LOCAL_ALIASES


def run(circuit: Circuit, shots: int = 1000, *, device_arn: str | None = None) -> RunResult:
    """Execute a circuit, returning measurement counts.

    Local runs are free and unconditional. QPU runs are authorized by the cost
    guard first; an unauthorized or over-budget run raises before submission.
    """
    arn = device_arn if device_arn is not None else selected_device_arn()

    if is_local(arn):
        from braket.devices import LocalSimulator

        result = LocalSimulator().run(circuit, shots=shots).result()
        return RunResult(dict(result.measurement_counts), shots, "LocalSimulator", 0.0)

    # --- paid QPU path: guard BEFORE we touch AWS ---
    pricing = pricing_for(arn)
    authorize_qpu_run(arn, pricing, shots)  # raises QpuSpendError if not allowed

    from braket.aws import AwsDevice  # lazy: only needed (and credential-bound) here

    result = AwsDevice(arn).run(circuit, shots=shots).result()
    return RunResult(
        dict(result.measurement_counts), shots, arn, estimate_cost(pricing, shots)
    )
