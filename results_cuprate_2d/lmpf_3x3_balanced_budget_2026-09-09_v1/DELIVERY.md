# Preserved budget attempt: calibration derivative audit failed

The main calculation and7 tests completed in2.937958s.
Independent verification failed on the calibration Jacobian: maximum reported
difference .03473427. Symmetric e0/e1 gives tied extrema in the ZZ score range,
so the variance-penalty rule has a kink. Agreement of two central step sizes
does not establish a unique derivative there.

Do not treat the first-order calibration covariance here as verified.
The original output, source snapshots and hashes are preserved. The separate
v2 calculation replaces this approximation with finite calibration outcomes
and the law of total covariance. No new QPU or TN propagation occurred.
