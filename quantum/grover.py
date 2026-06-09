"""
quantum/grover.py
=================
Grover's algorithm -- unstructured search with a quadratic speedup -- built on
the Amazon Braket SDK and runnable on the free local simulator.

Given an N = 2^n item search space with M marked items, Grover finds a marked
item in ~ (pi/4) * sqrt(N/M) oracle queries, versus ~N/2 for a classical brute
force scan. The circuit here is the textbook construction: a uniform
superposition, then Grover iterations of (phase oracle) followed by (diffuser,
i.e. inversion about the mean).

Nothing in this module talks to AWS. `grover_circuit` returns a Braket
`Circuit`; *how* and *where* you run it -- the free local simulator vs a paid
QPU behind the cost guard -- lives in `quantum/device.py`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from braket.circuits import Circuit


def optimal_iterations(n_qubits: int, n_marked: int = 1) -> int:
    """Grover iteration count that maximises the marked-state probability.

    The exact optimum is round((pi/2 - theta) / (2*theta)) where
    sin^2(theta) = M/N; for small M/N this is the familiar ~(pi/4)*sqrt(N/M).
    """
    if n_marked <= 0:
        raise ValueError("n_marked must be >= 1")
    n = 2**n_qubits
    if n_marked >= n:
        return 0
    theta = math.asin(math.sqrt(n_marked / n))
    iters = round((math.pi / 2 - theta) / (2 * theta))
    return max(iters, 1)


def _normalise_marked(marked: Iterable, n_qubits: int) -> list[str]:
    """Coerce marked items (ints or bitstrings) to validated n-bit strings."""
    out: list[str] = []
    for m in marked:
        bits = format(m, f"0{n_qubits}b") if isinstance(m, int) else str(m)
        if len(bits) != n_qubits or any(ch not in "01" for ch in bits):
            raise ValueError(f"marked item {m!r} is not a valid {n_qubits}-bit state")
        out.append(bits)
    if not out:
        raise ValueError("at least one marked state is required")
    return out


def _phase_flip_all_ones(circ: Circuit, qubits: list[int]) -> None:
    """Multi-controlled Z: flip the phase of |11...1> over `qubits`."""
    if len(qubits) == 1:
        circ.z(qubits[0])
    else:
        *controls, target = qubits
        circ.z(target, control=list(controls))


def _oracle(circ: Circuit, qubits: list[int], marked: list[str]) -> None:
    """Phase oracle: flip the sign of every marked computational basis state."""
    for bits in marked:
        zeros = [q for q, b in zip(qubits, bits) if b == "0"]
        for q in zeros:
            circ.x(q)
        _phase_flip_all_ones(circ, qubits)
        for q in zeros:
            circ.x(q)


def _diffuser(circ: Circuit, qubits: list[int]) -> None:
    """Inversion about the mean (Grover diffusion operator)."""
    for q in qubits:
        circ.h(q)
    for q in qubits:
        circ.x(q)
    _phase_flip_all_ones(circ, qubits)
    for q in qubits:
        circ.x(q)
    for q in qubits:
        circ.h(q)


def grover_circuit(
    marked: Iterable,
    n_qubits: int | None = None,
    n_iterations: int | None = None,
) -> Circuit:
    """Build a Grover search circuit.

    Args:
        marked: the states to search for, as bitstrings ("101") or ints (5).
        n_qubits: width of the search register; inferred from a bitstring if omitted.
        n_iterations: Grover iterations; defaults to the optimal count.
    """
    if n_qubits is None:
        first = next(iter(marked))
        if isinstance(first, int):
            raise ValueError("n_qubits is required when marked items are given as ints")
        n_qubits = len(str(first))

    bits = _normalise_marked(marked, n_qubits)
    if n_iterations is None:
        n_iterations = optimal_iterations(n_qubits, len(bits))

    qubits = list(range(n_qubits))
    circ = Circuit()
    for q in qubits:
        circ.h(q)
    for _ in range(n_iterations):
        _oracle(circ, qubits, bits)
        _diffuser(circ, qubits)
    return circ


def state_probabilities(circ: Circuit) -> dict[str, float]:
    """Exact per-basis-state probabilities via the free local simulator (shots=0).

    Deterministic and credential-free -- this is an analysis tool, not a QPU run.
    """
    from braket.devices import LocalSimulator

    n = circ.qubit_count
    measured = circ.copy()
    measured.probability()
    values = LocalSimulator().run(measured, shots=0).result().values[0]
    return {format(i, f"0{n}b"): float(p) for i, p in enumerate(values)}


def success_probability(circ: Circuit, marked: Iterable) -> float:
    """Total probability mass on the marked states for a built Grover circuit."""
    probs = state_probabilities(circ)
    bits = _normalise_marked(marked, circ.qubit_count)
    return sum(probs[b] for b in bits)
