import AnalyticPilot
import MomentPilot
import CoefficientPilot
/- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic
   Exact central doublon series for the concrete 3x3 Hamiltonian. -/
set_option autoImplicit false
set_option maxRecDepth 10000
set_option maxHeartbeats 8000000
noncomputable section
namespace CentralDynamics
open ConcreteH CentralPilot CentralMoment ExponentialPilot
open scoped BigOperators Matrix.Norms.Operator
abbrev MC := Matrix State State ℂ
def lift : CentralMoment.M →+* MC := (Int.castRingHom ℂ).mapMatrix
def HC4 : MC := lift h4Matrix
def DC : MC := lift CentralMoment.D
def Gplus : MC := (Complex.I/4) • HC4
def Gminus : MC := (-Complex.I/4) • HC4
def scalarCoefficient (n : ℕ) : ℂ := (ExponentialPilot.coefficient (R := MC) Gplus Gminus DC n) initialState initialState
def evaluation : MC →+ ℂ where
  toFun X := X initialState initialState
  map_zero' := rfl
  map_add' _ _ := rfl

theorem lift_apply (A : CentralMoment.M) (s t : State) : lift A s t = (A s t : ℂ) := rfl

theorem evaluation_continuous : Continuous evaluation :=
  continuous_id.matrix_elem initialState initialState

theorem evaluation_apply (X : MC) : evaluation X = X initialState initialState := rfl
attribute [local irreducible] h4Matrix ConcreteH.H4 HC4 DC Gplus Gminus scalarCoefficient
  CentralMoment.D CentralMoment.moment initialState

theorem complex_moment (a b : ℕ) :
    (HC4^a * DC * HC4^b : MC) initialState initialState = (moment a b : ℂ) := by
  have h : lift (h4Matrix^a * CentralMoment.D * h4Matrix^b : CentralMoment.M) = (HC4^a * DC * HC4^b : MC) := by
    simp only [map_mul, map_pow, HC4, DC]
  have he := congrArg (fun X : MC => X initialState initialState) h
  rw [lift_apply] at he
  simpa only [CentralMoment.moment] using he.symm

def weight (a b : ℕ) : ℂ :=
  (Nat.factorial a : ℂ)⁻¹ * (Complex.I/4)^a * (Nat.factorial b : ℂ)⁻¹ * (-Complex.I/4)^b

theorem summand_moment (a b : ℕ) :
    (term Gplus a * DC * term Gminus b : MC) initialState initialState = weight a b * (moment a b : ℂ) := by
  simp only [term, Gplus, Gminus, smul_pow, smul_smul, smul_mul_assoc, mul_smul_comm,
    Matrix.smul_apply, smul_eq_mul]
  rw [complex_moment]
  unfold weight
  ring

theorem coefficient_as_moments (n : ℕ) :
    scalarCoefficient n = ∑ k ∈ Finset.range (n+1), weight k (n-k) * (moment k (n-k) : ℂ) := by
  simp only [scalarCoefficient, ExponentialPilot.coefficient, Matrix.sum_apply, summand_moment]

theorem coefficient_zero : scalarCoefficient 0 = 0 := by
  norm_num [coefficient_as_moments, Finset.sum_range_succ, moment_zero_left, weight]
theorem coefficient_one : scalarCoefficient 1 = 0 := by
  norm_num [coefficient_as_moments, Finset.sum_range_succ, moment_zero_left, moment_zero_right, weight]
theorem coefficient_two : scalarCoefficient 2 = 0 := by
  norm_num [coefficient_as_moments, Finset.sum_range_succ, moment_zero_left, moment_zero_right, moment_one_left, weight]
theorem coefficient_three : scalarCoefficient 3 = 0 := by
  norm_num [coefficient_as_moments, Finset.sum_range_succ, moment_zero_left, moment_zero_right, moment_one_left, moment_one_right, weight]
theorem coefficient_four : scalarCoefficient 4 = 1 := by
  norm_num [coefficient_as_moments, Finset.sum_range_succ, moment_zero_left, moment_zero_right, moment_one_left, moment_one_right, moment_two_two, weight, div_pow, neg_sq, Complex.I_sq]

theorem generator_plus : Gplus = Complex.I • ConcreteH.complexH := by
  ext s t
  simp only [Gplus, HC4, Matrix.smul_apply, smul_eq_mul]
  rw [lift_apply]
  simp [h4Matrix, ConcreteH.complexH, ConcreteH.H]
  ring

theorem generator_minus : Gminus = (-Complex.I) • ConcreteH.complexH := by
  ext s t
  simp only [Gminus, HC4, Matrix.smul_apply, smul_eq_mul]
  rw [lift_apply]
  simp [h4Matrix, ConcreteH.complexH, ConcreteH.H]
  ring

theorem projector_diagonal : DC = Matrix.diagonal (fun s : State => if central s.val then (1 : ℂ) else 0) := by
  ext s t
  simp only [DC, lift_apply, CentralMoment.D, Matrix.diagonal_apply]
  by_cases h : s=t <;> simp [h]

theorem projector_matches_site : DC = Matrix.diagonal (fun s : State => (siteDoublon (4 : Fin 9) s : ℂ)) := by
  rw [projector_diagonal]
  congr 1
  funext s
  by_cases hu : s.val.1.testBit 4=true <;> by_cases hd : s.val.2.testBit 4=true <;>
    simp [central, siteDoublon, siteUp, siteDown, hu, hd]

def expectation (T : ℝ) : ℂ :=
  (NormedSpace.exp (((T : ℂ)*Complex.I) • ConcreteH.complexH) * DC *
    NormedSpace.exp ((-((T : ℂ)*Complex.I)) • ConcreteH.complexH) : MC) initialState initialState

-- As in Mathlib's MatrixExponential wrappers: expose definitionally equal
-- canonical and norm-induced matrix instances during elaboration only.
-- The ordinary Lean kernel still checks the resulting proof term.
set_option backward.isDefEq.respectTransparency false in
theorem exact_expectation_hasSum (T : ℝ) :
    HasSum (fun n => (T : ℂ)^n * scalarCoefficient n) (expectation T) := by
  have h := time_series_hasSum (R := MC) (T : ℂ) Gplus Gminus DC
  have he : HasSum (fun n => (T : ℂ)^n * scalarCoefficient n)
      (evaluation (NormedSpace.exp ((T : ℂ) • Gplus) * DC * NormedSpace.exp ((T : ℂ) • Gminus) : MC)) := by
    simpa only [Function.comp_def, evaluation_apply, Matrix.smul_apply, smul_eq_mul,
      scalarCoefficient] using h.map evaluation evaluation_continuous
  have hv : evaluation (NormedSpace.exp ((T : ℂ) • Gplus) * DC *
      NormedSpace.exp ((T : ℂ) • Gminus) : MC) = expectation T := by
    rw [evaluation_apply, generator_plus, generator_minus]
    simp only [smul_smul, mul_neg, expectation]
  exact hv ▸ he

theorem polynomial_through_four (T : ℝ) :
    (∑ n ∈ Finset.range 5, (T : ℂ)^n * scalarCoefficient n) = (T : ℂ)^4 := by
  simp [Finset.sum_range_succ, coefficient_zero, coefficient_one, coefficient_two,
    coefficient_three, coefficient_four]

theorem matches_archived_even_prefix :
    [scalarCoefficient 0, scalarCoefficient 2, scalarCoefficient 4] =
      CentralPilot.archivePrefix.map (fun q : ℚ => (q : ℂ)) := by
  simp [CentralPilot.archivePrefix, coefficient_zero, coefficient_two, coefficient_four]

theorem exact_series_split (T : ℝ) :
    expectation T = (T : ℂ)^4 + ∑' n : ℕ, (T : ℂ)^(n+5)*scalarCoefficient (n+5) := by
  have h := exact_expectation_hasSum T
  have hs := h.summable.sum_add_tsum_nat_add 5
  rw [h.tsum_eq, polynomial_through_four] at hs
  exact hs.symm
end CentralDynamics
