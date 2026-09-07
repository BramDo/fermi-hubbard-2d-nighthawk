# Hardware-control implementation log

2026-09-06: User authorized one preparation/FLO control job, cap5 QPU seconds.
Fresh read-only probe: ibm_phoenix operational,120 qubits,no faulty qubits;
pending1; default rep_delay1 microsecond; consumed usage38 seconds and
remaining quota not reported. Credentials stayed in the saved account.

First local test run:7 tests passed; the T=0 reference fixture failed because
the existing configuration validator correctly refuses dt=0. The fixture
now uses preparation-only at T=0. No physics generator was modified and no
provider submission was attempted. Subsequent test output is retained in
the run directory once all tests pass.

Prediction: preparation controls should recover22/32 particles and their
full initial spin/charge/doublon profiles. The5x5 U0 finite-circuit target
is exactly calculable with FLO; good preparation need not imply good deep
dynamics. Native skeleton is held fixed against an offline-only U8 companion.

The next8 tests passed;29 existing TFLO/hardware regression tests also passed.
The first large symbolic compilation terminated after the test stage, without
an exception reaching the Python handler. No circuit, plan or submission marker
was produced. A separate45-second-bounded probe built the logical50-qubit
circuit (14822 instructions) in0.154 seconds. The original process stack limit
was8 MiB. A native-stack issue is suspected, not established. The local retry
uses a64 MiB process-local stack and one compiler worker; this changes no gates,
physics, packages, QPU budget or global WSL settings. Partial logs are retained.
