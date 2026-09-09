# Prepared only: bounded first matched twirl1 operator check

Status: NOT RUN. No hardware or cloud authority requested or implied.

Reason: the saved high-bond twirl0 states are not proven transferable to
twirl1. Choose ID1 because it is the next archived ID, not because its measured
results look favorable. Do not load target bitstrings or exact target values
to choose the operator, chi, weights, seed, or penalty.

Start narrowly with observable 8: central Z_up on logical mode8 (physical109).
Use native twirl1 provider records:
- factor1: index25, circuit_025.qpy (5727 gates, 1008 CZ)
- factor2: index19, circuit_019.qpy (6735 gates, 2016 CZ)
- factor3: index2, circuit_002.qpy (7743 gates, 3024 CZ)

Use the verified layout and mask from the corresponding archive records.
Use the same frozen gate-error depolarizing model and canonical-chain kernel.
Do not alter old modules whose hashes are frozen in earlier result bundles.

Compute four matched Heisenberg operator states (ideal factor1, noisy factors
1/2/3) independently at chi64 and chi128: at most eight new states. Retain
readout unmask signs and all native preparation gates. Reuse no twirl0 state
as if it were the twirl1 result. Do not form an eight-twirl channel mixture.

Local safeguards: one numerical thread; 600-second process budget with state
checkpoints and a hard process timeout; no chi256, automatic retries or next
twirl batch. First confirm available RAM and disk. Preserve partial output if
the time cap is reached. Do not treat incomplete contraction as a zero value.

Independently audit the saved chain contractions. Check raw Gram PSD and all
raw entries; retain the raw F00 convergence issue separately. In a separate
copy use the exact ideal Pauli norm F00=1. This is exact for a single twirl's
unitary operator, not justified by its expectation on one state.

Compare chi64/128 exact-norm F, noisy block G and ideal/noisy overlap b with
the already declared 1% relative limits; coefficients with L1-change <=0.05.
Fit only the unchanged eta1 shot-aware rule, N=(43,7,14), using calibration and
all possible outcome ranges, not actual target sample frequencies or reference
values. The fitted operator is Z_up alone: do not present charge, spin or
doublons before matched Z_down/ZZ operator calculations also exist.

If the local gates pass, the next candidate is Z_down, followed by onsite ZZ,
each with its own bounded plan. Only then perform one predetermined matched
hardware robustness comparison using this twirl's data. It is reused data,
not an untouched holdout; no automatic 6x6 escalation.

