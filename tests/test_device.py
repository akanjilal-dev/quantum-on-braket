"""
tests/test_device.py
====================
The run path: defaults to the free local simulator, and a local run actually
recovers the marked state. The QPU branch is not exercised here (it needs AWS
credentials); its guard is covered in test_cost.py.
"""

from quantum.device import is_local, run, selected_device_arn
from quantum.grover import grover_circuit


def test_default_device_is_local(monkeypatch):
    monkeypatch.delenv("BRAKET_DEVICE", raising=False)
    assert is_local(selected_device_arn())


def test_local_run_recovers_target_and_is_free():
    # 2-qubit Grover is exact, so "11" wins every shot.
    result = run(grover_circuit(["11"], n_qubits=2), shots=500, device_arn="local")
    assert max(result.counts, key=result.counts.get) == "11"
    assert result.estimated_cost_usd == 0.0
    assert result.device == "LocalSimulator"
