# Preserved preflight failure

No calibration or training shots were executed; blocks/ is empty.
Eight deterministic tests passed. NoiseModel.from_dict failed before sampling:
ValueError: too many values to unpack (expected 2).
Cause: serialized complex Kraus matrices carry an extra [real,imag] axis.
The established aer_cuprate_cz_half_v2 helper already documents this format.
The v2 runner rebuilds the original full model through the established public
builder and validates every channel against this unchanged saved noise model.
The archived source_snapshot preserves the original failing implementation.
No parent data were changed; the failed directory is not reused.
