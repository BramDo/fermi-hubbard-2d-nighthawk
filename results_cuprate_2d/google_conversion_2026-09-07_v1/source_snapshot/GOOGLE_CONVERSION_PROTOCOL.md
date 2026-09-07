# Google/Phasecraft data conversion, 2026-09-07

User: "probeer de google waarden om te rekenen naar onze resultaten";
clarification: "het is vooral 5 x5 bij google".
Compare published expectation values using our observable definitions. Keep
5x5 and 6x6 separate; per-site normalization is not a finite-size prediction.
No quantum submission, new classical dynamics, environment modification,
publication or editing of old frozen results is authorized by this task.

Primary sources: arXiv:2510.26845v2 and Zenodo record17881822. Prefer numeric
Z/ZZ data to plot digitization. Fetch only metadata and explicitly selected
exp_vals.h5 files, not the8.8GB shot archive. Preserve URLs, ZIP entry CRCs,
content sizes, hashes, configurations, methods and time points.

Our definitions at site i:
  n_up=(1-Z_up)/2, n_down=(1-Z_down)/2;
  charge=1-(Z_up+Z_down)/2;
  spin=n_up-n_down=(Z_down-Z_up)/2 =2 physical Sz;
  doublon=(1-Z_up-Z_down+ZZ_up_down)/4.
N=sum(charge); mean D=sum(D)/L; spin-profile RMS=sqrt(mean(spin_i^2)).
Staggered magnetisation is not spin-profile RMS. Averages cannot determine
local RMS errors. With only marginal uncertainties and no covariance,
do not claim exact propagated uncertainty for derived sums/products.

Target for a nearest-context descriptive comparison: U=8,T=.4,zero flux,
Néel-background holes, both5x5 and6x6 if provided. Inspect archive inventory
and initial-state metadata before selecting cases; record missing matches.
Our actual experiment uses6x6,N32,four holes,stripe_neel,t'=-.25,two steps.
The Google Hamiltonian has nearest-neighbour hopping and optional flux.
Changing t',hole positions/number,lattice size or Trotter structure cannot
be corrected by a units conversion. All mismatches stay visible.

Report own raw/TFLO and Google raw/mitigated numeric values separately.
Also compare each published hardware result with its own available classical
reference(s), not with our mismatched chi64 as an exact ground truth.
If no matched full local profile exists, report the comparison as unavailable.
State conservation constraints/postselection and possible training leakage;
N close to the prescribed sector is not an independent validation metric.

Verification: tests on vacuum/up/down/doublon and mixed probabilities;
independent direct occupancy formulas; input uniqueness/completeness;
consistent spatial and spin labels; exact selected time/no silent interpolation;
no clipping of negative reconstructed probabilities; preserve old file hashes.
