# Fermi-Hubbard 2D cuprate series, part 1: from 1D to 2D

Originally published at:
https://edukaizen.nl/fermi-hubbard-2d-cuprate-series-part-1-from-1d-to-2d/

Part 1 of 6 in the Fermi-Hubbard 2D cuprate series.
Series page: https://edukaizen.nl/fermi-hubbard-2d-cuprate-series/

The first Fermi-Hubbard series on Edukaizen was about a one-dimensional chain.
It used 60 qubits for 30 Hubbard sites, 8 Trotter steps, IBM hardware, and
ITensorMPS TDVP as the classical reference. The best hardware route was close
to the TDVP chi64 reference on the diagonal observables: charge RMSE
`0.01471` and spin RMSE `0.03850`. The local chi64 TDVP run took about
`821.277 s`.

That first series was not a quantum-advantage claim. It was a reproducible
engineering and validation snapshot. The useful part was not just the final
number. The useful part was the workflow:

- define the physical model;
- choose observables that can be compared route by route;
- use a fermion-aware circuit construction;
- respect hardware layout and calibration;
- run hardware;
- compare against a local classical baseline;
- keep the interpretation boundary explicit.

This second series keeps that discipline, but moves from a 1D chain to a
two-dimensional route.

## Why 2D is a real change

One-dimensional Hubbard dynamics can already be hard, but the geometry gives
you structure. A line can be mapped to a line of fermionic modes. A
pair-interleaved Jordan-Wigner ordering and fSWAP routing can keep the circuit
compact. The 1D route is still subtle, but the geometry is friendly.

Two dimensions are different. A square lattice has horizontal and vertical
bonds. Fermion routing becomes harder. Exact diagonalization fails earlier.
Hardware connectivity matters more. A circuit that is acceptable for a small
3x3 lattice may already become too noisy at 4x4 if routing and mitigation are
not under control.

That is why the second series does not start by submitting the largest circuit
we can write down. It starts with a ladder:

- `3x3`, because exact fixed-sector ED is still possible;
- `4x4`, because exact ED is no longer a comfortable general route and tensor
  baselines become necessary;
- later larger dry-runs only after the 3x3 and 4x4 steps make sense.

## What the new route tries to measure

The current 2D route uses diagonal Z-basis observables:

- `charge_i = n_i,up + n_i,down`
- `spin_z_i = n_i,up - n_i,down`
- `double_occupancy_i = n_i,up n_i,down`
- nearest-neighbor charge and spin-z bond correlations

These observables do not prove superconductivity. They do not measure
off-diagonal d-wave pairing. They are the first layer of diagnostic physics:
does charge move sensibly, does spin-z melt in a controlled way, does doublon
formation look plausible, and does the hardware stay in the right particle
sector?

That is the right first question. If hardware output fails at this level, a
larger claim would be premature.

## What counts as evidence in this series

In this series, a hardware result is not interpreted by itself. It has to be
placed next to local baselines:

- exact fixed-sector ED where possible;
- TDHF as a mean-field baseline;
- Gaussian/free-fermion evolution as a noninteracting baseline;
- MPS circuit simulation for 4x4 and beyond;
- observable-comparison tables using the same site and bond definitions.

This is the core interpretation boundary:

hardware output is diagnostic until it has been compared with the local
baselines and validation files.

That boundary matters especially for the 2D route. A raw IBM or Fire Opal
result can look structured while still being dominated by sector leakage,
readout error, or circuit noise. The comparison is not optional. It is the
thing that makes the result readable.

## The current status

The present 2D route has five layers:

1. A 3x3 validation run with one hole, exact ED, TDHF, Gaussian/free
   evolution, IBM hardware, and Fire Opal diagnostics.
2. A 3x3 time sweep through step 4, showing how the exact dynamics and
   approximate baselines separate over time.
3. A 4x4 run with two holes, IBM hardware on `ibm_marrakesh`, and a quimb
   MPS circuit baseline for the shallow circuit family.
4. A 4x4 Fire Opal qelib retry on the same shallow route, compared against the
   same MPS observables.
5. A 6x6, 72-qubit diagnostic step with an MPS chi32 baseline and completed
   IBM hardware output. The matching Fire Opal qelib fallback is still pending.

The main lesson so far is straightforward. 3x3 is a good validation lab.
Fire Opal is much cleaner than direct IBM at 3x3 and 4x4. A direct 6x6 IBM run
is executable, but the RMSE against the local MPS baseline is large and the
particle-sector survival is very low. The next improvement is therefore not
just "run bigger". It is "make the circuit shallower, improve the layout and
mitigation, and strengthen the tensor baseline".

Part 2 introduces the physical model: the 2D Hubbard Hamiltonian, why it is
connected to cuprates, and how recent Google/Willow 2D Hubbard work sets the
external scale.
