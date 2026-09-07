# 2D Cuprate Hubbard Comparison Targets

This file separates direct Hubbard benchmarks from real-material cuprate phenomenology.
Use the high-priority classical targets first; real cuprate measurements are qualitative unless a material-specific mapping is added.

| priority | kind | target | compare to | caveat |
|---|---|---|---|---|
| high | classical_arxiv | [Solutions of the Two Dimensional Hubbard Model: Benchmarks and Results from a Wide Range of Numerical Algorithms](https://arxiv.org/abs/1505.02290) | energy, double occupancy, density, small-cluster exact/reference runs | Not a cuprate measurement; mainly a numerical benchmark suite. |
| high | classical_arxiv | [Benchmark study of the two-dimensional Hubbard model with auxiliary-field quantum Monte Carlo method](https://arxiv.org/abs/1605.09421) | energy, double occupancy, spin/magnetization, momentum distribution | Away from half filling uses constrained-path control of the sign problem. |
| high | classical_arxiv | [Stripe order in the underdoped region of the two-dimensional Hubbard model](https://arxiv.org/abs/1701.00054) | charge stripe structure factor, spin stripe structure factor, stripe filling | Found filled stripe order in the pure model that differs from real cuprates. |
| high | classical_arxiv | [Absence of superconductivity in the pure two-dimensional Hubbard model](https://arxiv.org/abs/1910.08931) | long-distance d-wave pair correlations | Pure t'=0 model; not the same as cuprate-like t'<0 target. |
| highest | classical_arxiv | [Coexistence of superconductivity with partially filled stripes in the Hubbard model](https://arxiv.org/abs/2303.08376) | d-wave pair order/correlations, stripe filling, charge modulation, AF correlations | Tiny energy scales; needs careful size/boundary extrapolation. |
| highest | classical_dataset | [Intertwined spin, charge and pair correlations in the two-dimensional Hubbard model in the thermodynamic limit](https://arxiv.org/abs/2106.01944) | spin/charge/pair correlation functions and structure factors | Embedded-cluster method; match parameters before numeric comparison. |
| medium | classical_arxiv | [Stripes, Antiferromagnetism, and the Pseudogap in the Doped Hubbard Model at Finite Temperature](https://arxiv.org/abs/2009.10736) | spin correlations, charge order, specific heat/susceptibility proxies | Finite temperature and cylinder geometry; not a direct hardware-time trace. |
| medium | quantum_gas_measurement | [String patterns in the doped Hubbard model](https://arxiv.org/abs/1810.03584) | hole-spin patterns, geometric-string observables, spin-charge diagnostics | Analog cold-atom simulator, not electronic cuprate material and not d-wave SC. |
| medium | quantum_gas_measurement | [Pseudogap in a Fermi-Hubbard quantum simulator](https://arxiv.org/abs/2509.18075) | compressibility proxy, spectral response proxy, doping phase boundary | Recent arXiv preprint; not a local-pairing or d-wave order measurement. |
| low | cuprate_measurement_review | [Energy gaps in high-transition temperature cuprate superconductors](https://arxiv.org/abs/1503.00391) | momentum-space d-wave symmetry and pseudogap phenomenology, not local Z observables | Real cuprates include material chemistry beyond the one-band Hubbard model. |
| low | cuprate_measurement_review | [Resonant x-ray scattering studies of charge order in cuprates](https://arxiv.org/abs/1509.03313) | charge ordering wave vectors and doping trends | Phenomenological comparison only; not a direct one-band-Hubbard benchmark. |

Recommended order:

1. Validate bookkeeping against LeBlanc 2015 and Qin 2016 style 2D Hubbard benchmarks.
2. Use Zheng 2017, Xu 2024, and Mai 2022 for stripe and pairing observables.
3. Use cold-atom measurements for experimental Hubbard patterns and pseudogap observables.
4. Use ARPES/RXS cuprate measurements only as qualitative material motivation.
