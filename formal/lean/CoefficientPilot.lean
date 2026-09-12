import SparsePilot
/- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic
   Low-order Cauchy coefficients with H4=4H, including all cross terms.
   This module does not by itself identify the Cauchy series with exp(-iTH). -/
set_option autoImplicit false
set_option maxRecDepth 10000
namespace CentralPilot
attribute [local irreducible] p0 p1 p2

theorem overlap_nil_left (xs : Terms) : overlap [] xs = 0 := rfl
theorem overlap_nil_right (xs : Terms) : overlap xs [] = 0 := by
  simp [overlap, value]

def cauchyZero : ℚ := (overlap (project p0) (project p0) : ℚ)
def cauchyTwo (v2 : Terms) : ℚ :=
  -((overlap (project p0) (project v2) : ℚ) - 2*(overlap (project p1) (project p1) : ℚ)
    + (overlap (project v2) (project p0) : ℚ)) / (4^2 * 2)
def cauchyFour (v3 v4 : Terms) : ℚ :=
  ((overlap (project p0) (project v4) : ℚ) - 4*(overlap (project p1) (project v3) : ℚ)
    + 6*(overlap (project p2) (project p2) : ℚ)
    - 4*(overlap (project v3) (project p1) : ℚ)
    + (overlap (project v4) (project p0) : ℚ)) / (4^4 * 24)

theorem zero_coefficient : cauchyZero = 0 := by
  simp only [cauchyZero, projected_initial, overlap_nil_left, Int.cast_zero]
theorem second_coefficient (v2 : Terms) : cauchyTwo v2 = 0 := by
  simp only [cauchyTwo, projected_initial, projected_first, overlap_nil_left, overlap_nil_right]
  norm_num
theorem fourth_coefficient (v3 v4 : Terms) : cauchyFour v3 v4 = 1 := by
  simp only [cauchyFour, projected_initial, projected_first, overlap_nil_left, overlap_nil_right,
    projected_second_mass]
  norm_num

def archivePrefix : List ℚ := [0,0,1]
theorem matches_archive_prefix (v3 v4 : Terms) :
    [cauchyZero, cauchyTwo p2, cauchyFour v3 v4] = archivePrefix := by
  rw [zero_coefficient, second_coefficient, fourth_coefficient]
  rfl
theorem polynomial_through_four (v3 v4 : Terms) (T : ℚ) :
    cauchyZero + cauchyTwo p2*T^2 + cauchyFour v3 v4*T^4 = T^4 := by
  rw [zero_coefficient, second_coefficient, fourth_coefficient]
  ring
end CentralPilot
