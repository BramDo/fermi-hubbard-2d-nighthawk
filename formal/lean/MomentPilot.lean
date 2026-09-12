import ProjectionPilot
import ConcreteProofs
/- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic
   Integer matrix moments for H4=4H and the central doublon projector. -/
set_option autoImplicit false
set_option maxRecDepth 10000
set_option maxHeartbeats 8000000
namespace CentralMoment
open ConcreteH CentralPilot
open scoped BigOperators
abbrev M := Matrix State State ℤ
def D : M := Matrix.diagonal (fun s => if central s.val then 1 else 0)
def moment (a b : ℕ) : ℤ := ((h4Matrix^a * D * h4Matrix^b : M) initialState initialState)
attribute [local irreducible] h4Matrix ConcreteH.H4 D initialState

theorem h4_symmetric (s t : State) : h4Matrix s t = h4Matrix t s := by
  simpa only [h4Matrix] using H4_symmetric all_sector_checked s t

theorem centre_empty : central initialState.val = false := by decide +kernel

theorem left_zero (B : M) : (D * B : M) initialState initialState = 0 := by
  simp [D, Matrix.diagonal_mul, centre_empty]

theorem right_zero (B : M) : (B * D : M) initialState initialState = 0 := by
  simp [D, Matrix.mul_diagonal, centre_empty]

theorem first_row_zero (t : State) : (h4Matrix*D : M) initialState t = 0 := by
  simp only [D, Matrix.mul_diagonal]
  have h := first_projected_matrix_zero t
  by_cases hc : central t.val=true
  · simpa only [hc, if_true, mul_one, h4Matrix] using h
  · simp [hc]

theorem first_column_zero (t : State) : (D*h4Matrix : M) t initialState = 0 := by
  simp only [D, Matrix.diagonal_mul]
  rw [h4_symmetric t initialState]
  have h := first_projected_matrix_zero t
  by_cases hc : central t.val=true
  · simpa only [hc, if_true, one_mul, h4Matrix] using h
  · simp [hc]

theorem moment_zero_left (b : ℕ) : moment 0 b = 0 := by
  simpa only [moment, pow_zero, one_mul] using left_zero (h4Matrix^b)

theorem moment_zero_right (a : ℕ) : moment a 0 = 0 := by
  simpa only [moment, pow_zero, mul_one] using right_zero (h4Matrix^a)

theorem moment_one_left (b : ℕ) : moment 1 b = 0 := by
  unfold moment
  rw [pow_one, Matrix.mul_apply]
  simp only [first_row_zero, zero_mul, Finset.sum_const_zero]

theorem moment_one_right (a : ℕ) : moment a 1 = 0 := by
  unfold moment
  rw [pow_one, Matrix.mul_assoc]
  rw [Matrix.mul_apply]
  simp only [first_column_zero, mul_zero, Finset.sum_const_zero]

theorem square_symmetric (s t : State) : (h4Matrix*h4Matrix : M) s t = (h4Matrix*h4Matrix : M) t s := by
  simp only [Matrix.mul_apply]
  apply Finset.sum_congr rfl
  intro k _
  rw [h4_symmetric s k, h4_symmetric k t]
  exact mul_comm _ _

theorem moment_two_two : moment 2 2 = 1024 := by
  unfold moment
  simp only [pow_two]
  rw [Matrix.mul_apply]
  simp only [D, Matrix.mul_diagonal]
  have h := second_projected_matrix_mass
  convert h using 1
  apply Finset.sum_congr rfl
  intro t _
  rw [square_symmetric t initialState]
  by_cases hc : central t.val=true <;> simp [hc, pow_two]
end CentralMoment
