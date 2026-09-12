import CommutatorRemainder
import Mathlib.Analysis.Matrix.Normed

/- Explicit row-sum operator norm, NOT the entrywise sup norm.
The scalar functional selects the initial basis state's diagonal matrix entry.
ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic -/
noncomputable section
set_option autoImplicit false
set_option maxHeartbeats 2000000
open scoped BigOperators
namespace MatrixRemainder

attribute [local instance] Matrix.linftyOpSeminormedAddCommGroup
  Matrix.linftyOpNormedAddCommGroup Matrix.linftyOpNormedRing

variable {ι : Type} [Fintype ι] [DecidableEq ι]

theorem row_sum_norm_bound (K : Matrix ι ι ℝ) (B : ℝ) (hB : 0 ≤ B)
    (hrow : ∀ i, ∑ j, |K i j| ≤ B) : ‖K‖ ≤ B := by
  rw [Matrix.linfty_opNorm_def]
  let b : NNReal := ⟨B,hB⟩
  have hrows : ∀ i, (∑ j, ‖K i j‖₊) ≤ b := by
    intro i
    apply NNReal.coe_le_coe.mp
    change ((∑ j, ‖K i j‖₊ : NNReal) : ℝ) ≤ B
    simpa only [NNReal.coe_sum, coe_nnnorm, Real.norm_eq_abs] using hrow i
  have hmax : (Finset.univ.sup (fun i => ∑ j, ‖K i j‖₊)) ≤ b :=
    Finset.sup_le (fun i _ => hrows i)
  exact_mod_cast hmax

theorem diagonal_entry_contractive (s : ι) (X : Matrix ι ι ℝ) : |X s s| ≤ ‖X‖ := by
  have hrow : ‖X s s‖₊ ≤ ∑ j, ‖X s j‖₊ :=
    Finset.single_le_sum (f := fun j => ‖X s j‖₊) (fun j _ => by positivity) (Finset.mem_univ s)
  have hmax : (∑ j, ‖X s j‖₊) ≤ Finset.univ.sup (fun i => ∑ j, ‖X i j‖₊) :=
    Finset.le_sup (f := fun i => ∑ j, ‖X i j‖₊) (Finset.mem_univ s)
  rw [Matrix.linfty_opNorm_def]
  have h := hrow.trans hmax
  simpa [Real.norm_eq_abs] using (NNReal.coe_le_coe.mpr h)

theorem diagonal_observable_norm (v : ι → ℝ) (M : ℝ) (hM : 0 ≤ M)
    (hv : ∀ i, |v i| ≤ M) : ‖Matrix.diagonal v‖ ≤ M := by
  rw [Matrix.linfty_opNorm_diagonal]
  apply (pi_norm_le_iff_of_nonneg hM).2
  simpa [Real.norm_eq_abs] using hv

theorem transpose_ad_sign (K O : Matrix ι ι ℝ)
    (hK : K.transpose = K) (hO : O.transpose = O) (n : ℕ) :
    (CommutatorRemainder.ad K O n).transpose =
      (-1 : ℝ)^n • CommutatorRemainder.ad K O n := by
  induction n with
  | zero => simp [CommutatorRemainder.ad, hO]
  | succ n ih =>
    simp only [CommutatorRemainder.ad, Matrix.transpose_sub, Matrix.transpose_mul]
    rw [ih, hK, Matrix.smul_mul, Matrix.mul_smul, ← smul_sub]
    rw [pow_succ, mul_neg_one, neg_smul, ← smul_neg]
    congr 1
    exact (neg_sub _ _).symm

theorem odd_diagonal_commutator_zero (K : Matrix ι ι ℝ) (v : ι → ℝ) (s : ι)
    (hK : K.transpose = K) (n : ℕ) :
    CommutatorRemainder.ad K (Matrix.diagonal v) (2*n+1) s s = 0 := by
  have h := transpose_ad_sign K (Matrix.diagonal v) hK (by simp) (2*n+1)
  have hp : (-1 : ℝ)^(2*n+1) = -1 := by rw [pow_add, pow_mul]; norm_num
  have he := congrFun (congrFun h s) s
  simp only [Matrix.transpose_apply, Matrix.smul_apply, smul_eq_mul, hp] at he
  linarith

theorem matrix_charge_remainder (K : Matrix ι ι ℝ) (v : ι → ℝ) (s : ι) (T : ℝ)
    (hrow : ∀ i, ∑ j, |K i j| ≤ 40) (hv : ∀ i, |v i| ≤ 2)
    (hT : |T| ≤ 2/5) :
    |(∑' n, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient K (Matrix.diagonal v) (fun X => X s s)) T n) -
      ∑ n ∈ Finset.range 55, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient K (Matrix.diagonal v) (fun X => X s s)) T n| <
        5058/10^16 := by
  apply CommutatorRemainder.commutator_charge_remainder K (Matrix.diagonal v)
    (fun X => X s s) T
  · exact row_sum_norm_bound K 40 (by norm_num) hrow
  · exact diagonal_observable_norm v 2 (by norm_num) hv
  · exact diagonal_entry_contractive s
  · exact hT

theorem matrix_unit_remainder (K : Matrix ι ι ℝ) (v : ι → ℝ) (s : ι) (T : ℝ)
    (hrow : ∀ i, ∑ j, |K i j| ≤ 40) (hv : ∀ i, |v i| ≤ 1)
    (hT : |T| ≤ 2/5) :
    |(∑' n, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient K (Matrix.diagonal v) (fun X => X s s)) T n) -
      ∑ n ∈ Finset.range 55, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient K (Matrix.diagonal v) (fun X => X s s)) T n| <
        2529/10^16 := by
  apply CommutatorRemainder.commutator_unit_remainder K (Matrix.diagonal v)
    (fun X => X s s) T
  · exact row_sum_norm_bound K 40 (by norm_num) hrow
  · exact diagonal_observable_norm v 1 (by norm_num) hv
  · exact diagonal_entry_contractive s
  · exact hT

end MatrixRemainder
