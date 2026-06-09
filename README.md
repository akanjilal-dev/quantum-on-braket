# quantum-on-braket

**Quantum algorithms you can actually run — and actually afford.** Runnable,
cost-aware implementations on **Amazon Braket**, free on the local simulator and
one environment flag away from real hardware. Every paid QPU call goes through a
**cost guard** first, because metered quantum hardware deserves the same FinOps
discipline as any other cloud spend.

First algorithm: **Grover's search**. Next: QAOA, VQE, and quantum phase
estimation (see the roadmap).

> **Runs free, offline, with zero AWS credentials.** The Braket SDK ships a
> local statevector simulator; the demo and the entire test suite run on it. The
> *exact same circuit* runs on IonQ, Rigetti, IQM, or QuEra by setting one
> environment variable — and the cost guard makes sure you meant to spend the money.

---

## Quickstart

```bash
git clone https://github.com/akanjilal-dev/quantum-on-braket
cd quantum-on-braket
pip install -r requirements.txt
python -m quantum.main        # Grover on the free local simulator
pytest -q                     # the quantum + cost-guard claims, as tests
```

Search a different space:

```bash
python -m quantum.main --target 1011 --shots 2000
```

Run on real hardware — one flag, still gated by the cost guard:

```bash
export BRAKET_DEVICE=arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1
export BRAKET_ALLOW_QPU_SPEND=5.00     # dollar ceiling; omit it and the run is refused
python -m quantum.main
```

## What you'll see

```
GROVER'S SEARCH — finding a needle in an unstructured haystack
----------------------------------------------------------------------
  Search space      : 8 items (3 qubits)
  Marked item       : |101>  (the 'needle' an oracle recognises)
  Classical queries : ~4 on average, 8 worst case
  Grover iterations : 2  (~sqrt of the space)
  Start probability :  12.50%  (uniform — every item equally likely)
  After amplification: 94.53%  on |101>

  Exact amplitude distribution (top states):
    |101>  94.53% ██████████████████████████  <- marked
    ...
  Sampled run on LocalSimulator (1000 shots): most frequent = |101>  (cost $0.0000)

  Cost-awareness — the same 1000-shot job on real hardware would cost:
    IonQ       ~$ 30.30
    Rigetti    ~$  1.20
    IQM        ~$  1.75
```

One uniform superposition starts every item at 12.5%. Two Grover iterations
amplify the marked state to **94.5%** — a quadratic speedup over the ~N/2
queries a classical scan needs. The probabilities printed are *exact* (computed
at `shots=0` on the simulator), so the result is deterministic.

## How Grover works (as built here)

| Step | What it does | In the code |
|---|---|---|
| **Superposition** | `H` on every qubit — all N states equally likely | `grover_circuit` |
| **Oracle** | Flip the *phase* of the marked state(s) — mark without measuring | `_oracle` |
| **Diffuser** | Invert all amplitudes about their mean — turns the phase flip into a probability bump | `_diffuser` |
| **Repeat** | ~`(π/4)·√(N/M)` times — the optimal iteration count | `optimal_iterations` |

The oracle and diffuser both need a multi-controlled `Z`; we build it with Braket
gate **control modifiers** (`z(target, control=[...])`), which keeps the circuit
readable and vendor-neutral.

## The cost guard (the part most quantum demos skip)

Quantum hardware is billed **per task + per shot**. A "quick experiment" at a few
thousand shots on a premium QPU is real money, and it's easy to fire one off by
accident. So paid runs fail closed:

| Situation | Behaviour |
|---|---|
| Local simulator | Always runs, always free (`$0.00`) |
| QPU, no `BRAKET_ALLOW_QPU_SPEND` set | **Refused** — prints the estimate and how to authorize |
| QPU, estimate over your ceiling | **Refused** — aborts before a single shot is submitted |
| QPU, estimate within your ceiling | Runs, and reports the estimated cost |

The estimate is shown *before* submission, the authorization is an explicit
dollar ceiling, and the default is "don't spend." That's least-privilege applied
to a budget — see [`quantum/cost.py`](quantum/cost.py).

## Roadmap

- [x] **Grover's search** — amplitude amplification, multi-target oracle, cost guard
- [ ] **QAOA** (Max-Cut / portfolio) — combinatorial optimization; the enterprise-relevant one
- [ ] **VQE** — variational eigensolver; pairs with Braket Hybrid Jobs
- [ ] **QFT → Quantum Phase Estimation** — the backbone of Shor-class algorithms
- [ ] **Bernstein–Vazirani / Deutsch–Jozsa** — one-query "quantum advantage", a clean teaching demo

## Caveats

- **Teaching-grade, not research-grade.** These are clear, correct, runnable
  reference implementations — not optimized or error-corrected.
- **Gate support varies by device.** The multi-controlled `Z` uses OpenQASM
  control modifiers; Braket's compiler decomposes them for hardware that lacks
  native support, but check your target device's gate set before a real run.
- **Pricing is approximate and drifts.** The cost-guard rates are ballpark Braket
  on-demand figures for making spend *visible and bounded* — re-verify against the
  [Braket pricing page](https://aws.amazon.com/braket/pricing/) before you rely on a number.

---

*Part of [akanjilal.dev](https://akanjilal.dev) — frontier compute, made secure, cost-governed, and production-real.*
