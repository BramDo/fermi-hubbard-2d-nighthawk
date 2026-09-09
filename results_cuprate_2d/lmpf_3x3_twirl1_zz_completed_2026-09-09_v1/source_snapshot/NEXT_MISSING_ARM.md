# Prepared only: finish the missing twirl1 ZZ arm

Status: NOT STARTED. Request user approval for at most300s additional local
calculation time. No QPU, hardware retrieval, publishing or parameter change.

Exactly one missing operator:
- Observable22, support{8:'Z',9:'Z'},18 active modes.
- Twirl1, native factor3, provider index2/circuit_002.qpy.
- Noise scale1 in the same frozen depolarizing surrogate.
- chi256, same canonical kernel, cutoff1e-12/rsum2/renorm0.
- Joint readout-mask sign, physical modes109/108.
- Explicit3e9 FLOP and2^22-element overlap limits.

Do NOT rerun the eight-state script unchanged. Make a new resumable output
bundle, verify the parent partial_manifest.json and every existing source,
calibration, plan and state hash, and reuse the seven completed states exactly.
Keep the parent budget failure and partial report immutable. Restore large
parent files only through the safe archive helper if absent.

Start the missing state from its own beginning; no saved intermediate state
exists for the interrupted arm. One numerical thread, hard300s process cap,
per-block deadline, no retry or higher chi. If it fails again, preserve both
parent and new partial evidence rather than replacing the prior states.

After the new state is complete, reconstruct both full four-arm Grams using
the saved three high-chi states and all four low-chi states. Validate raw PSD
before making separate exact-F00=1 copies. Use the unchanged eta1 shot-aware
penalty from both readout modes,N=(43,7,14), not target sample frequencies.

Reapply exactly the previously declared1% exact-norm F/G/b change limits and
0.05 coefficient L1 limit; retain raw-F changes independently. Do not relax
a failing criterion or select another state based on target accuracy.

Independently audit all20 overlaps and both direct-KKT fits; verify existing
data were reused byte-for-byte. Archive all large files losslessly in parts
below10MB using the existing helpers. Audit/archive operations remain separate
short bounded integrity checks. Preserve raw local state files.

Only if the complete operator gates and independent audit pass may the next
archived-hardware robustness comparison be prepared/executed under
lmpf_2d/PLAN_TWIRL1_HARDWARE.md. This resumption itself does not score target
data or authorize a6x6/QPU run.
