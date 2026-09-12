import Mathlib.Analysis.Normed.Algebra.Exponential
import Mathlib.Analysis.Normed.Ring.InfiniteSum
import Mathlib.Analysis.Normed.Algebra.MatrixExponential

/- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic
   Cauchy product for exp(A) O exp(B), no commutativity assumption. -/
set_option autoImplicit false
set_option maxHeartbeats 4000000
noncomputable section
open scoped BigOperators
namespace ExponentialPilot
variable {R : Type*} [NormedRing R] [NormedAlgebra ℂ R] [CompleteSpace R]
def term (A : R) (n : ℕ) : R := ((Nat.factorial n : ℂ)⁻¹) • A^n

theorem term_hasSum (A : R) : HasSum (term A) (NormedSpace.exp A) :=
  NormedSpace.exp_series_hasSum_exp' A

omit [CompleteSpace R] in
theorem term_norm_summable (A : R) : Summable (fun n => ‖term A n‖) :=
  NormedSpace.norm_expSeries_summable' A

theorem conjugation_hasSum (A B O : R) :
    HasSum (fun n => ∑ k ∈ Finset.range (n+1), (term A k * O) * term B (n-k))
      (NormedSpace.exp A * O * NormedSpace.exp B) := by
  have hl : Summable (fun n => ‖term A n * O‖) :=
    ((term_norm_summable A).mul_right ‖O‖).of_nonneg_of_le
      (fun n => norm_nonneg _) (fun n => norm_mul_le _ _)
  have h := hasSum_sum_range_mul_of_summable_norm hl (term_norm_summable B)
  rw [((term_hasSum A).mul_right O).tsum_eq, (term_hasSum B).tsum_eq] at h
  exact h

def coefficient (A B O : R) (n : ℕ) : R :=
  ∑ k ∈ Finset.range (n+1), (term A k * O) * term B (n-k)

omit [CompleteSpace R] in
theorem term_smul (z : ℂ) (A : R) (n : ℕ) : term (z • A) n = z^n • term A n := by
  simp only [term, smul_pow, smul_smul]
  congr 1
  exact mul_comm _ _

omit [CompleteSpace R] in
theorem coefficient_smul (z : ℂ) (A B O : R) (n : ℕ) :
    coefficient (z • A) (z • B) O n = z^n • coefficient A B O n := by
  simp only [coefficient, term_smul, smul_mul_assoc, mul_smul_comm, smul_smul, Finset.smul_sum]
  apply Finset.sum_congr rfl
  intro k hk
  have hk' : k ≤ n := Nat.le_of_lt_succ (Finset.mem_range.mp hk)
  rw [← pow_add, Nat.sub_add_cancel hk']

theorem time_series_hasSum (z : ℂ) (A B O : R) :
    HasSum (fun n => z^n • coefficient A B O n)
      (NormedSpace.exp (z • A) * O * NormedSpace.exp (z • B)) := by
  have h := conjugation_hasSum (z • A) (z • B) O
  change HasSum (fun n => coefficient (z • A) (z • B) O n) _ at h
  simpa only [coefficient_smul] using h
end ExponentialPilot
