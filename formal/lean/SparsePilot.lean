import ConcreteObservables
import Mathlib.Tactic.NormNum

/- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic
   Exact H4=4H paths, initial masks (325,170), central site 4. -/
set_option autoImplicit false
set_option maxRecDepth 10000
set_option maxHeartbeats 8000000
namespace CentralPilot
open ConcreteH
open scoped BigOperators

abbrev Terms := List (Raw × ℤ)
def entries (s : Raw) : Terms :=
  (s,32*(doublons s : ℤ)) :: links.map (fun e => (target s e, amplitude s e))
def value (xs : Terms) (s : Raw) : ℤ :=
  (xs.map (fun p => if p.1=s then p.2 else 0)).sum
def scale (a : ℤ) (xs : Terms) : Terms := xs.map (fun p => (p.1,a*p.2))
def advance (xs : Terms) : Terms := xs.flatMap (fun p => scale p.2 (entries p.1))
def central (s : Raw) : Bool := s.1.testBit 4 && s.2.testBit 4
def project (xs : Terms) : Terms := xs.filter (fun p => central p.1 && (p.2 != 0))
def overlap (xs ys : Terms) : ℤ := (xs.map (fun p => p.2 * value ys p.1)).sum
def p0 : Terms := [((325,170),1)]
def p1 : Terms := advance p0
def p2 : Terms := advance p1
def h4Matrix : Matrix State State ℤ := H4

theorem entry_matrix (s t : State) : value (entries s.val) t.val = H4 s t := by
  simp only [value, entries, List.map_cons, List.sum_cons, List.map_map, H4]
  have he : s.val=t.val ↔ s=t := ⟨fun h => state_val_injective h, congrArg State.val⟩
  simp only [he]
  congr 1
  apply congrArg List.sum
  apply List.map_congr_left
  intro e _
  simp only [Function.comp_apply, bond]
  by_cases h : target s.val e = t.val <;> simp [h, eq_comm]

theorem projected_initial : project p0 = [] := by decide +kernel
theorem projected_first : project p1 = [] := by decide +kernel
theorem projected_second_paths : (project p2).length = 32 := by decide +kernel
theorem projected_second_mass : overlap (project p2) (project p2) = 1024 := by decide +kernel
theorem fourth_candidate : (overlap (project p2) (project p2) : ℚ) / (4^4 * 4) = 1 := by
  rw [projected_second_mass]
  norm_num
end CentralPilot
