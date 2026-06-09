"""
tests/test_grover.py
====================
These tests encode the core claim of the repo: Grover's algorithm amplifies the
marked state until it dominates. With the local simulator at shots=0 the
probabilities are exact, so the assertions are fully deterministic and run in CI
with no AWS credentials.
"""

import pytest

from quantum.grover import (
    grover_circuit,
    optimal_iterations,
    state_probabilities,
    success_probability,
)


def test_optimal_iterations_known_values():
    assert optimal_iterations(2, 1) == 1   # 2 qubits, single target -> exact in 1
    assert optimal_iterations(3, 1) == 2
    assert optimal_iterations(4, 1) == 3


def test_two_qubit_search_is_exact():
    # The 2-qubit / single-target case reaches 100% in one iteration.
    circ = grover_circuit(["11"], n_qubits=2)
    assert success_probability(circ, ["11"]) == pytest.approx(1.0, abs=1e-9)


def test_single_target_dominates():
    target = "101"
    probs = state_probabilities(grover_circuit([target], n_qubits=3))
    assert max(probs, key=probs.get) == target
    assert probs[target] > 0.9


def test_multiple_marked_states():
    circ = grover_circuit(["000", "111"], n_qubits=3)
    assert success_probability(circ, ["000", "111"]) > 0.9


def test_marked_given_as_int():
    # 5 == "101" on 3 qubits
    probs = state_probabilities(grover_circuit([5], n_qubits=3))
    assert max(probs, key=probs.get) == "101"


def test_n_qubits_inferred_from_bitstring():
    circ = grover_circuit(["1010"])  # width inferred = 4
    assert circ.qubit_count == 4
    assert max(state_probabilities(circ), key=lambda s: state_probabilities(circ)[s]) == "1010"


def test_invalid_marked_state_rejected():
    with pytest.raises(ValueError):
        grover_circuit(["12"], n_qubits=2)
    with pytest.raises(ValueError):
        grover_circuit(["101"], n_qubits=2)  # wrong width
