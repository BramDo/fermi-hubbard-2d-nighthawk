# Preserved first PA pilot attempt

The 8 physics tests passed. Full 6x6 preparation and the first native
network-order circuit were generated. No provider calls or QPU usage.

Execution stopped in audit_pa_ancilla_6x6.py after the first twirl:
AttributeError: 'tuple' object has no attribute 'num_qubits'.
Cause: compact_bound returns (circuit, proof), not a circuit alone.

Fixed in the new v2 runner with a regression test. This v1 source snapshot
and every existing v1 artifact are preserved. The v1 directory is a partial
failed audit, not a completed or hardware-ready result.
