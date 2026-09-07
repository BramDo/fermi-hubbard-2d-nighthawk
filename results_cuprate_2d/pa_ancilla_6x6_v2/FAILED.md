# Preserved second PA pilot attempt

Stopped at the new cleanup-interface regression test before large transpilation.
The test supplied an H gate to a verifier that accepts only the native CZ basis.
Error: ValueError: Unexpected operation: h.
The other 8 physics tests passed. Corrected the test input to native SX.
No hardware submission, no QPU usage. Original v2 source snapshot is preserved.
