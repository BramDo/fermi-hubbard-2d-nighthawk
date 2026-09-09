# Prepared only: twirl1 central onsite ZZ

Status: NOT RUN. Both central single-Z operators now pass their fixed local
chi64/128 checks. This plan requests no QPU use, publishing or automatic batch.

Next operator: index22, support {8:'Z',9:'Z'} on physical qubits109,108.
This is Z_up*Z_down, NOT the product of two separately evolved/noisy operators.
Compute its own ideal factor1 and noisy factor1/2/3 operators for twirl1,
using native providerrecords25/19/2 and each record's two-bit mask product.

Choose chi128/256 before inspecting this operator's hardware outcomes.
Reason: the historical twirl0 ZZ control needed128/256 for the exact-norm/G/b
local test (see ../lmpf_3x3_exact_norm_2026-09-09_v1/DELIVERY.md).
This is a fixed, history-informed numerical resolution choice, not a target-
accuracy scan. It does not guarantee that twirl1 will pass.

Compute at most eight NEW states. No substitution of twirl0 ZZ or products of
the existing Z_up/Z_down states. Retain the same canonical-chain kernel,
cutoff1e-12, rsum2, renorm0, all physical preparation/native gates and frozen
depolarizing surrogate.

Resource bounds: one numerical thread; hard600s calculation-process timeout,
block-boundary deadline checks and per-state checkpoints; no automatic retries,
chi512 or additional twirls. Check free memory/disk before launching. If timed
out, preserve completed states and report the missing level as incomplete.

For chi256, use the previously verified explicit overlap guard of3e9 FLOPs
and2^22 intermediate elements; do NOT silently change the historical default
2e9 guard. Apply this explicit bound consistently to roundtrip norms, Grams
and independent raw-network auditing. A guard failure remains a failure.

Validate all raw Grams first. In a separate copy set only exact ideal F00=1.
Use the same1% relative-change limits for exact-norm F, G and b and0.05
coefficient L1-change. Preserve raw norms, raw convergence and any failures.

Fit only the unchanged eta1 shot-aware rule,N=(43,7,14). For ZZ compute the
range of the readout-corrected product score over ALL four measured outcomes,
using BOTH central calibration modes. Do not substitute either single-Z
penalty. Audit it with explicit assignment-matrix inversion, including tests
with unequal and asymmetric readout errors.

Chi256 NPZ files may exceed10MB. Keep the original local states and pack only
the large files losslessly with lmpf_2d/portable_archive.py and the existing
scripts/restore_archives.py verification route. All archive parts below10MB.
Never overwrite a mismatching restore or add a large raw binary directly to Git.

After successful calculation, independently audit every saved overlap and fit,
sign/mask, actual native input and hashes; retain both uncorrected and corrected
norm evidence. Archive/integrity and audit are separate bounded follow-up checks.
No 18-qubit dense channel or target/reference-assisted optimizer.

Only after ALL THREE matching operators pass their declared checks should the
complete central lading/spin/doublon comparison be prepared on archived twirl1
hardware data. Keep that comparison at the same matched target budget and
propagate shared readout-calibration uncertainty, including the calibration
dependence of shot-aware weights. It remains reused-data robustness analysis,
not a blinded holdout. No automatic6x6 escalation.
