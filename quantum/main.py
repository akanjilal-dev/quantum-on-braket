"""
quantum/main.py
===============
A runnable Grover demo: hide a marked item in an unstructured space, then find
it with ~sqrt(N) quantum queries instead of ~N/2 classical ones -- and show what
the same job would cost on real hardware before you ever spend a cent.

    python -m quantum.main                 # free, offline, no credentials
    python -m quantum.main --target 1011   # search a 4-bit space
    python -m quantum.main --shots 2000

Point it at real hardware with one flag (still gated by the cost guard):

    export BRAKET_DEVICE=arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1
    export BRAKET_ALLOW_QPU_SPEND=5.00
    python -m quantum.main
"""

from __future__ import annotations

import argparse
import logging

# The local simulator logs an informational note that control-modifier gates use
# OpenQASM features not every QPU supports natively (Braket's compiler decomposes
# them where it can). True and worth knowing — see the README caveat — but noise
# in the demo, so quiet it here only.
logging.getLogger("braket").setLevel(logging.ERROR)

from quantum.cost import estimate_cost, pricing_for
from quantum.device import is_local, run, selected_device_arn
from quantum.grover import grover_circuit, optimal_iterations, state_probabilities

# Vendors quoted in the cost-awareness footer (illustrative ARNs).
_QUOTE_DEVICES = [
    ("IonQ", "arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1"),
    ("Rigetti", "arn:aws:braket:us-west-1::device/qpu/rigetti/Ankaa-3"),
    ("IQM", "arn:aws:braket:eu-north-1::device/qpu/iqm/Garnet"),
]


def _bar(p: float, width: int = 28) -> str:
    return "█" * round(p * width)


def demo(target: str = "101", shots: int = 1000) -> None:
    n = len(target)
    space = 2**n
    iters = optimal_iterations(n, 1)

    circ = grover_circuit([target], n_qubits=n)
    probs = state_probabilities(circ)  # exact, free
    p_target = probs[target]

    print("=" * 70)
    print("GROVER'S SEARCH — finding a needle in an unstructured haystack")
    print("-" * 70)
    print(f"  Search space      : {space} items ({n} qubits)")
    print(f"  Marked item       : |{target}>  (the 'needle' an oracle recognises)")
    print(f"  Classical queries : ~{space // 2} on average, {space} worst case")
    print(f"  Grover iterations : {iters}  (~sqrt of the space)")
    print(f"  Start probability : {1 / space:7.2%}  (uniform — every item equally likely)")
    print(f"  After amplification: {p_target:6.2%}  on |{target}>")
    print()

    print("  Exact amplitude distribution (top states):")
    for state, p in sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:5]:
        marker = "  <- marked" if state == target else ""
        print(f"    |{state}>  {p:6.2%} {_bar(p)}{marker}")
    print()

    arn = selected_device_arn()
    result = run(circ, shots=shots, device_arn=arn)
    found = max(result.counts, key=result.counts.get)
    print(f"  Sampled run on {result.device} ({shots} shots): "
          f"most frequent = |{found}>  (cost ${result.estimated_cost_usd:.4f})")
    print()

    if is_local(arn):
        print(f"  Cost-awareness — the same {shots}-shot job on real hardware would cost:")
        for label, quote_arn in _QUOTE_DEVICES:
            est = estimate_cost(pricing_for(quote_arn), shots)
            print(f"    {label:10s} ~${est:6.2f}")
        print("  (Run free here; flip BRAKET_DEVICE to a QPU ARN when it's worth the spend.)")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Grover search on Amazon Braket.")
    parser.add_argument("--target", default="101", help="bitstring to search for (e.g. 1011)")
    parser.add_argument("--shots", type=int, default=1000, help="measurement shots for the sampled run")
    args = parser.parse_args()

    if any(c not in "01" for c in args.target) or not args.target:
        parser.error("--target must be a non-empty bitstring of 0s and 1s")
    demo(target=args.target, shots=args.shots)


if __name__ == "__main__":
    main()
