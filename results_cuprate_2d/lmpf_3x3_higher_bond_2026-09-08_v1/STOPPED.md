# Stopped development run, all partial data preserved

Stopped intentionally before completion. The status predicate defaulted the
missing `rejected` key of valid fit dictionaries to True, which would incorrectly
report stable valid fits as unavailable. Propagated tensors are unaffected.
The predicate was corrected and regression-tested; the new run uses a separate
v2 directory. This partial folder is not a completed higher-bond comparison.
