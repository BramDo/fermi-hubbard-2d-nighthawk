import SparsePilot
/- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic -/
set_option autoImplicit false
set_option maxRecDepth 10000
set_option maxHeartbeats 8000000
namespace CentralPilot
open ConcreteH
open scoped BigOperators
attribute [local irreducible] p0 p1 p2 h4Matrix ConcreteH.H4

theorem value_append (xs ys : Terms) (r : Raw) : value (xs++ys) r = value xs r + value ys r := by
  simp [value, List.map_append, List.sum_append]
#check value_append

theorem value_scale (a : ℤ) (xs : Terms) (r : Raw) : value (scale a xs) r = a * value xs r := by
  induction xs with
  | nil => simp [value, scale]
  | cons p xs ih =>
    change (if p.1=r then a*p.2 else 0) + value (scale a xs) r = a*((if p.1=r then p.2 else 0)+value xs r)
    rw [ih, mul_add]
    split_ifs <;> simp
#check value_scale

def supportValid (xs : Terms) : Bool := xs.all (fun p => p.2 == 0 || validRaw p.1)

theorem advance_matrix (xs : Terms) (hx : supportValid xs = true) (t : State) :
    value (advance xs) t.val = ∑ s : State, value xs s.val * H4 s t := by
  induction xs with
  | nil => simp [value, advance]
  | cons p xs ih =>
    have hh : (p.2=0 ∨ validRaw p.1=true) ∧ supportValid xs=true := by
      simpa [supportValid, Bool.or_eq_true] using hx
    simp only [advance, List.flatMap_cons, value_append, value_scale]
    change p.2 * value (entries p.1) t.val + value (advance xs) t.val = _
    rw [ih hh.2]
    simp only [value, List.map_cons, List.sum_cons, add_mul, Finset.sum_add_distrib]
    congr 1
    rcases hh.1 with hz | hv
    · simp [hz]
    · obtain ⟨r,hr⟩ := state_of_valid p.1 hv
      have he : ∀ s : State, p.1=s.val ↔ s=r := by
        intro s
        rw [← hr]
        exact ⟨fun h => state_val_injective h.symm, fun h => h ▸ rfl⟩
      simp only [he, ite_mul, zero_mul, Finset.sum_ite_eq', Finset.mem_univ, if_true]
      simpa only [value, hr] using congrArg (fun z : ℤ => p.2*z) (entry_matrix r t)
#check advance_matrix

theorem support_zero : supportValid p0 = true := by decide +kernel
theorem support_one : supportValid p1 = true := by decide +kernel

theorem initial_values (t : State) : value p0 t.val = if initialState=t then 1 else 0 := by
  have he : (325,170)=t.val ↔ initialState=t := by
    change initialState.val=t.val ↔ initialState=t
    exact ⟨fun h => state_val_injective h, congrArg State.val⟩
  simp only [value, p0, List.map_cons, List.map_nil, List.sum_cons, List.sum_nil, add_zero, he]
#check initial_values

theorem first_values (t : State) : value p1 t.val = H4 initialState t := by
  rw [p1, advance_matrix p0 support_zero]
  simp only [initial_values, ite_mul, one_mul, zero_mul]
  simp
#check first_values

theorem second_values (t : State) : value p2 t.val = (h4Matrix * h4Matrix : Matrix State State ℤ) initialState t := by
  rw [p2, advance_matrix p1 support_one]
  simp only [first_values]
  simpa only [h4Matrix] using (Matrix.mul_apply (M := h4Matrix) (N := h4Matrix) (i := initialState) (k := t)).symm
#check second_values
end CentralPilot
