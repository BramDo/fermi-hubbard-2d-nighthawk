# One authorized 6x6 original versus compact hardware test

User on 2026-09-07: "Laten we maar een hardware test 6 x6 doen", in response
to the proposed single original/compact pilot capped at 15 QPU seconds.
One new job on ibm_phoenix with existing saved account qiskit-runtime-q9.
No backend/account switching, automatic resubmission, or higher cap.
The selected instance is pay-as-you-go; the bound is QPU time, not wall time.
The API does not expose a remaining allocation for this instance. Do not
claim unlimited quota. Do not change billing or instance settings.

Same full 6x6, 72 fermion modes, N=32 (16+16), stripe-Neel initial state,
open boundaries, t=1, t'=-.25, U=8, total model time T=.4, two symmetric
steps. Spin means n_up-n_down=2Sz. The reference is the finite-step circuit,
not certified continuous Hamiltonian evolution. No terms or steps removed.

Original parameterized family versus verified compact parameterized family.
Same physical layout and four CZ/readout twirls, seeds 202609061600..603.
Schedule both with current ALAP/PadDelay before binding; no DD. Parameter
binding must not change gate structure, delays, CZ count or readout mapping.
Per arm: six U0 training times .04,.08,.12,.24,.32,.48; two independent U0
holdouts .2,.4; one U8 target at .4. Four twirls x 512 shots each setting.
72 dynamics PUBs and four all0/all1 readout calibration PUBs: 38,912 shots.
Pair original/compact for each setting/twirl and shuffle pair/order using
seed 202609071501. Calibration bookends are requested, not guaranteed by IBM.

Primary: original-minus-compact RMS error on exact finite-circuit U0 holdouts,
separately raw, readout and readout+TFLO. No selection of the best twirl.
Same fixed affine TFLO per Pauli and per arm: ridge .001 toward (1,0),
six U0 training points only. No time feature or U8 reference in the fit.
Holdout screen: upper 95% RMS <=.05 charge, .05 spin, .03 doublon on both
heldout times; a screen is not a certificate of transfer to U8.
Secondary: U8 charge, spin and doublons compared with existing uncertified
chi64, including the no-target-hardware-input ablation. Report negative
probabilities without clipping. No ZNE, PEC, postselection, or DD in this
comparison. Passing holdouts alone does not establish quantum advantage.
Uncertainty: 400 whole-shot bootstrap draws at fixed four twirls, independent
Jeffreys readout Beta draws, refitting training each draw; seed 202609071515.
Conditional intervals exclude drift, correlated SPAM, TFLO transfer bias,
Trotter and classical truncation. They are not simultaneous certificates.

Before POST: frozen source/input hashes and all 76 scalar PUBs validated,
current native target/fault checks, rep-delay/reset/memory/time estimates,
max_execution_time=15, init_qubits=True, built-in twirling/DD disabled,
no sessions or batches, retries disabled, exclusive new attempt marker.
Planning budget includes four internal subjob overheads and .75s headroom;
actual internal splitting is unknown and completion is not guaranteed.
Persist job ID before waiting; verify provider cap, cancel if mismatched.
Uncertain POST consumes authorization: recover by unique tag only.
Preserve old archives, new raw bitstrings, provider inputs, result metadata,
calibration snapshot, versions, circuit hashes, metrics and analysis.

Official references checked 2026-09-07:
- https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time
- https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time
