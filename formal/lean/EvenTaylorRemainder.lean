import Mathlib.Analysis.SpecificLimits.Normed
import Mathlib.Topology.Algebra.InfiniteSum.NatInt
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring

/- Analytic infinite-tail theorem, not an assertion about imported coefficients.
ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic -/
noncomputable section
set_option autoImplicit false
set_option maxRecDepth 10000
set_option maxHeartbeats 2000000
open scoped BigOperators
namespace EvenTaylorRemainder

def majorant (x : ℝ) (r k : ℕ) : ℝ := x^(r+2*k) / (Nat.factorial (r+2*k) : ℝ)
def ratio (x : ℝ) (r : ℕ) : ℝ := x^2 / (((r : ℝ)+1)*((r : ℝ)+2))

theorem majorant_nonneg (x : ℝ) (hx : 0 ≤ x) (r k : ℕ) : 0 ≤ majorant x r k := by
  unfold majorant
  positivity

theorem ratio_nonneg (x : ℝ) (r : ℕ) : 0 ≤ ratio x r := by
  unfold ratio
  positivity

theorem majorant_step_identity (x : ℝ) (r k : ℕ) :
    majorant x r (k+1) * (((r+2*k : ℕ) : ℝ)+1) * (((r+2*k : ℕ) : ℝ)+2) =
      majorant x r k * x^2 := by
  have hindex : r+2*(k+1) = (r+2*k)+2 := by omega
  have hf : (Nat.factorial (r+2*k) : ℝ) ≠ 0 := by positivity
  have h1 : (((r+2*k : ℕ) : ℝ)+1) ≠ 0 := by positivity
  have h2 : (((r+2*k : ℕ) : ℝ)+2) ≠ 0 := by positivity
  unfold majorant
  rw [hindex, pow_add]
  simp only [Nat.factorial_succ, Nat.cast_mul, Nat.cast_add, Nat.cast_one, Nat.cast_ofNat]
  field_simp
  ring

theorem majorant_step_le (x : ℝ) (hx : 0 ≤ x) (r k : ℕ) :
    majorant x r (k+1) ≤ ratio x r * majorant x r k := by
  have hk : (r : ℝ) ≤ ((r+2*k : ℕ) : ℝ) := by exact_mod_cast (Nat.le_add_right r (2*k))
  have hd : ((r : ℝ)+1)*((r : ℝ)+2) ≤
      (((r+2*k : ℕ) : ℝ)+1)*(((r+2*k : ℕ) : ℝ)+2) :=
    mul_le_mul (by linarith) (by linarith) (by positivity) (by positivity)
  have hdpos : 0 < ((r : ℝ)+1)*((r : ℝ)+2) := by positivity
  calc
    majorant x r (k+1) ≤ (majorant x r k * x^2) / (((r : ℝ)+1)*((r : ℝ)+2)) := by
      apply (le_div_iff₀ hdpos).2
      calc
        _ ≤ majorant x r (k+1) *
            ((((r+2*k : ℕ) : ℝ)+1)*(((r+2*k : ℕ) : ℝ)+2)) :=
          mul_le_mul_of_nonneg_left hd (majorant_nonneg x hx r (k+1))
        _ = majorant x r k * x^2 := by rw [← mul_assoc, majorant_step_identity]
    _ = ratio x r * majorant x r k := by unfold ratio; ring

theorem majorant_geometric (x : ℝ) (hx : 0 ≤ x) (r k : ℕ) :
    majorant x r k ≤ majorant x r 0 * (ratio x r)^k := by
  induction k with
  | zero => simp
  | succ k ih =>
    calc
      _ ≤ ratio x r * majorant x r k := majorant_step_le x hx r k
      _ ≤ ratio x r * (majorant x r 0 * (ratio x r)^k) :=
        mul_le_mul_of_nonneg_left ih (ratio_nonneg x r)
      _ = majorant x r 0 * (ratio x r)^(k+1) := by rw [pow_succ]; ring

theorem infinite_tail_bound (f : ℕ → ℝ) (N r : ℕ) (x M : ℝ)
    (hx : 0 ≤ x) (hM : 0 ≤ M) (hq : ratio x r < 1)
    (hf : ∀ k, |f (k+N)| ≤ M * majorant x r k) :
    Summable f ∧ |(∑' n, f n) - ∑ n ∈ Finset.range N, f n| ≤
      M * majorant x r 0 / (1-ratio x r) := by
  have hdom : ∀ k, ‖f (k+N)‖ ≤ (M * majorant x r 0) * (ratio x r)^k := by
    intro k
    rw [Real.norm_eq_abs]
    calc
      _ ≤ M * majorant x r k := hf k
      _ ≤ M * (majorant x r 0 * (ratio x r)^k) :=
        mul_le_mul_of_nonneg_left (majorant_geometric x hx r k) hM
      _ = _ := by ring
  have hg := (hasSum_geometric_of_lt_one (ratio_nonneg x r) hq).mul_left (M * majorant x r 0)
  have htail : Summable (fun k => f (k+N)) := hg.summable.of_norm_bounded hdom
  have hsum : Summable f := (summable_nat_add_iff N).mp htail
  refine ⟨hsum, ?_⟩
  have hsplit : (∑' n, f n) - ∑ n ∈ Finset.range N, f n = ∑' k, f (k+N) := by
    have h := hsum.sum_add_tsum_nat_add N
    linarith
  rw [hsplit]
  simpa only [Real.norm_eq_abs, div_eq_mul_inv] using tsum_of_norm_bounded hg hdom

def evenTerm (a : ℕ → ℝ) (T : ℝ) (n : ℕ) : ℝ := a n * T^(2*n)

theorem even_term_zero_time (a : ℕ → ℝ) (n : ℕ) :
    evenTerm a 0 n = if n=0 then a 0 else 0 := by
  by_cases h : n=0
  · simp [evenTerm, h]
  · have hn : 2*n ≠ 0 := Nat.mul_ne_zero (by decide) h
    simp [evenTerm, h, hn]

theorem zero_time_remainder (a : ℕ → ℝ) :
    |(∑' n, evenTerm a 0 n) - ∑ n ∈ Finset.range 55, evenTerm a 0 n| = 0 := by
  simp [even_term_zero_time]

theorem even_term_majorant (a : ℕ → ℝ) (M T : ℝ) (hM : 0 ≤ M)
    (ha : ∀ n, |a n| ≤ M * (80 : ℝ)^(2*n) / (Nat.factorial (2*n) : ℝ))
    (hT : |T| ≤ 2/5) (k : ℕ) :
    |evenTerm a T (k+55)| ≤ M * majorant 32 110 k := by
  have hp : |T|^(2*(k+55)) ≤ (2/5 : ℝ)^(2*(k+55)) :=
    pow_le_pow_left₀ (abs_nonneg T) hT _
  have hn : 2*(k+55) = 110+2*k := by omega
  unfold evenTerm
  rw [abs_mul, abs_pow]
  calc
    _ ≤ (M * (80 : ℝ)^(2*(k+55)) / (Nat.factorial (2*(k+55)) : ℝ)) *
        (2/5 : ℝ)^(2*(k+55)) := mul_le_mul (ha (k+55)) hp (by positivity) (by positivity)
    _ = M * majorant 32 110 k := by
      rw [div_mul_eq_mul_div, mul_assoc, ← mul_pow]
      norm_num only [show (80 : ℝ)*(2/5)=32 by norm_num]
      rw [hn]
      unfold majorant
      ring

theorem uniform_even_remainder (a : ℕ → ℝ) (M T : ℝ) (hM : 0 ≤ M)
    (ha : ∀ n, |a n| ≤ M * (80 : ℝ)^(2*n) / (Nat.factorial (2*n) : ℝ))
    (hT : |T| ≤ 2/5) :
    Summable (evenTerm a T) ∧
      |(∑' n, evenTerm a T n) - ∑ n ∈ Finset.range 55, evenTerm a T n| ≤
        M * (32 : ℝ)^110 / (Nat.factorial 110 : ℝ) / (1-(32 : ℝ)^2/(111*112)) := by
  have h := infinite_tail_bound (evenTerm a T) 55 110 32 M (by norm_num) hM
    (by norm_num [ratio]) (even_term_majorant a M T hM ha hT)
  simpa [majorant, ratio, mul_div_assoc,
    show (110 : ℝ)+1=111 by norm_num,
    show (110 : ℝ)+2=112 by norm_num] using h

theorem charge_remainder (a : ℕ → ℝ) (T : ℝ)
    (ha : ∀ n, |a n| ≤ 2 * (80 : ℝ)^(2*n) / (Nat.factorial (2*n) : ℝ))
    (hT : |T| ≤ 2/5) :
    |(∑' n, evenTerm a T n) - ∑ n ∈ Finset.range 55, evenTerm a T n| < 5058/10^16 := by
  have h := (uniform_even_remainder a 2 T (by norm_num) ha hT).2
  apply lt_of_le_of_lt h
  norm_num [Nat.factorial]

theorem unit_observable_remainder (a : ℕ → ℝ) (T : ℝ)
    (ha : ∀ n, |a n| ≤ (80 : ℝ)^(2*n) / (Nat.factorial (2*n) : ℝ))
    (hT : |T| ≤ 2/5) :
    |(∑' n, evenTerm a T n) - ∑ n ∈ Finset.range 55, evenTerm a T n| < 2529/10^16 := by
  have ha' : ∀ n, |a n| ≤ 1 * (80 : ℝ)^(2*n) / (Nat.factorial (2*n) : ℝ) := by simpa using ha
  have h := (uniform_even_remainder a 1 T (by norm_num) ha' hT).2
  apply lt_of_le_of_lt h
  norm_num [Nat.factorial]

end EvenTaylorRemainder
