import MatrixPilot
/- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic -/
set_option autoImplicit false
set_option maxRecDepth 10000
set_option maxHeartbeats 8000000
namespace CentralPilot
open ConcreteH
open scoped BigOperators

theorem value_cons (p : Raw × ℤ) (xs : Terms) (r : Raw) :
    value (p::xs) r = (if p.1=r then p.2 else 0) + value xs r := rfl

theorem value_project (xs : Terms) (r : Raw) :
    value (project xs) r = if central r then value xs r else 0 := by
  induction xs with
  | nil => simp [project, value]
  | cons p xs ih =>
    simp only [project] at ih
    by_cases hp : p.1=r
    · by_cases hc : central r=true <;> by_cases hz : p.2=0 <;>
        simp [project, value_cons, hp, hc, hz, ih]
    · by_cases hc : central p.1=true <;> by_cases hz : p.2=0 <;>
        simp [project, value_cons, hp, hc, hz, ih]

theorem overlap_cons (p : Raw × ℤ) (xs ys : Terms) :
    overlap (p::xs) ys = p.2*value ys p.1 + overlap xs ys := rfl

theorem overlap_matrix (xs ys : Terms) (hx : supportValid xs=true) :
    overlap xs ys = ∑ s : State, value xs s.val * value ys s.val := by
  induction xs with
  | nil => simp [overlap, value]
  | cons p xs ih =>
    have hh : (p.2=0 ∨ validRaw p.1=true) ∧ supportValid xs=true := by
      simpa [supportValid, Bool.or_eq_true] using hx
    rw [overlap_cons, ih hh.2]
    simp only [value_cons, add_mul, Finset.sum_add_distrib]
    congr 1
    rcases hh.1 with hz | hv
    · simp [hz]
    · obtain ⟨r,hr⟩ := state_of_valid p.1 hv
      have he : ∀ s : State, p.1=s.val ↔ s=r := by
        intro s
        rw [← hr]
        exact ⟨fun h => state_val_injective h.symm, fun h => h ▸ rfl⟩
      simp only [he, ite_mul, zero_mul, Finset.sum_ite_eq', Finset.mem_univ, if_true, hr]

theorem projected_support_two : supportValid (project p2)=true := by decide +kernel

theorem first_projected_matrix_zero (t : State) :
    (if central t.val then H4 initialState t else 0) = 0 := by
  rw [← first_values, ← value_project, projected_first]
  rfl

theorem second_projected_matrix_mass :
    (∑ t : State, (if central t.val then (h4Matrix*h4Matrix : Matrix State State ℤ) initialState t else 0)^2) = 1024 := by
  have h := (overlap_matrix (project p2) (project p2) projected_support_two).symm.trans projected_second_mass
  simpa only [value_project, second_values, pow_two] using h

theorem matrix_fourth_candidate :
    (((∑ t : State, (if central t.val then (h4Matrix*h4Matrix : Matrix State State ℤ) initialState t else 0)^2) : ℤ) : ℚ) /
      (4^4*4) = 1 := by
  rw [second_projected_matrix_mass]
  norm_num
end CentralPilot
