import EvenTaylorRemainder

/- Operator-norm sufficient conditions for the even-series coefficient bound.
This does not identify a concrete archived array with these coefficients.
ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic -/
noncomputable section
set_option autoImplicit false
set_option maxHeartbeats 2000000
open scoped BigOperators
namespace CommutatorRemainder

variable {A : Type} [NormedRing A]

def ad (K O : A) : ℕ → A
  | 0 => O
  | n+1 => K * ad K O n - ad K O n * K

theorem commutator_norm_bound (K O : A) :
    ‖K*O-O*K‖ ≤ (2*‖K‖)*‖O‖ := by
  calc
    _ ≤ ‖K*O‖ + ‖O*K‖ := norm_sub_le _ _
    _ ≤ ‖K‖*‖O‖ + ‖O‖*‖K‖ := add_le_add (norm_mul_le _ _) (norm_mul_le _ _)
    _ = _ := by ring

theorem iterated_commutator_bound (K O : A) (M : ℝ)
    (hK : ‖K‖ ≤ 40) (hO : ‖O‖ ≤ M) (n : ℕ) :
    ‖ad K O n‖ ≤ (80 : ℝ)^n * M := by
  induction n with
  | zero => simpa [ad] using hO
  | succ n ih =>
    calc
      _ ≤ (2*‖K‖)*‖ad K O n‖ := commutator_norm_bound K (ad K O n)
      _ ≤ 80*((80 : ℝ)^n*M) :=
        mul_le_mul (by linarith) ih (norm_nonneg _) (by norm_num)
      _ = (80 : ℝ)^(n+1)*M := by rw [pow_succ]; ring

def coefficient (K O : A) (evaluate : A → ℝ) (n : ℕ) : ℝ :=
  (-1 : ℝ)^n * evaluate (ad K O (2*n)) / (Nat.factorial (2*n) : ℝ)

theorem coefficient_bound (K O : A) (evaluate : A → ℝ) (M : ℝ)
    (hK : ‖K‖ ≤ 40) (hO : ‖O‖ ≤ M)
    (heval : ∀ X, |evaluate X| ≤ ‖X‖) (n : ℕ) :
    |coefficient K O evaluate n| ≤ M*(80 : ℝ)^(2*n)/(Nat.factorial (2*n) : ℝ) := by
  unfold coefficient
  rw [abs_div, abs_mul, abs_pow]
  norm_num only [abs_neg, abs_one, one_pow, one_mul]
  have hfac : |(Nat.factorial (2*n) : ℝ)| = (Nat.factorial (2*n) : ℝ) :=
    abs_of_nonneg (by positivity)
  rw [hfac]
  apply div_le_div_of_nonneg_right _ (by positivity)
  calc
    _ ≤ ‖ad K O (2*n)‖ := heval _
    _ ≤ (80 : ℝ)^(2*n)*M := iterated_commutator_bound K O M hK hO _
    _ = M*(80 : ℝ)^(2*n) := mul_comm _ _

theorem commutator_series_remainder (K O : A) (evaluate : A → ℝ) (M T : ℝ)
    (hK : ‖K‖ ≤ 40) (hO : ‖O‖ ≤ M)
    (heval : ∀ X, |evaluate X| ≤ ‖X‖) (hT : |T| ≤ 2/5) :
    Summable (EvenTaylorRemainder.evenTerm (coefficient K O evaluate) T) ∧
    |(∑' n, EvenTaylorRemainder.evenTerm (coefficient K O evaluate) T n) -
      ∑ n ∈ Finset.range 55, EvenTaylorRemainder.evenTerm (coefficient K O evaluate) T n| ≤
      M*(32 : ℝ)^110/(Nat.factorial 110 : ℝ)/(1-(32 : ℝ)^2/(111*112)) := by
  exact EvenTaylorRemainder.uniform_even_remainder _ M T ((norm_nonneg O).trans hO)
    (coefficient_bound K O evaluate M hK hO heval) hT

theorem commutator_charge_remainder (K O : A) (evaluate : A → ℝ) (T : ℝ)
    (hK : ‖K‖ ≤ 40) (hO : ‖O‖ ≤ 2)
    (heval : ∀ X, |evaluate X| ≤ ‖X‖) (hT : |T| ≤ 2/5) :
    |(∑' n, EvenTaylorRemainder.evenTerm (coefficient K O evaluate) T n) -
      ∑ n ∈ Finset.range 55, EvenTaylorRemainder.evenTerm (coefficient K O evaluate) T n| <
      5058/10^16 := by
  exact EvenTaylorRemainder.charge_remainder _ T
    (coefficient_bound K O evaluate 2 hK hO heval) hT

theorem commutator_unit_remainder (K O : A) (evaluate : A → ℝ) (T : ℝ)
    (hK : ‖K‖ ≤ 40) (hO : ‖O‖ ≤ 1)
    (heval : ∀ X, |evaluate X| ≤ ‖X‖) (hT : |T| ≤ 2/5) :
    |(∑' n, EvenTaylorRemainder.evenTerm (coefficient K O evaluate) T n) -
      ∑ n ∈ Finset.range 55, EvenTaylorRemainder.evenTerm (coefficient K O evaluate) T n| <
      2529/10^16 := by
  apply EvenTaylorRemainder.unit_observable_remainder _ T _ hT
  simpa using coefficient_bound K O evaluate 1 hK hO heval

end CommutatorRemainder
