import ConcreteShift

noncomputable section
set_option autoImplicit false
namespace ConcreteH

def initialState : State :=
  ⟨(⟨⟨325,by decide⟩,by decide +kernel⟩,⟨⟨170,by decide⟩,by decide +kernel⟩)⟩

def siteUp (i : Fin 9) (s : State) : ℝ := if s.val.1.testBit i.val then 1 else 0
def siteDown (i : Fin 9) (s : State) : ℝ := if s.val.2.testBit i.val then 1 else 0
def siteCharge (i : Fin 9) (s : State) : ℝ := siteUp i s + siteDown i s
def siteSpin (i : Fin 9) (s : State) : ℝ := siteUp i s - siteDown i s
def siteDoublon (i : Fin 9) (s : State) : ℝ := siteUp i s * siteDown i s

theorem site_charge_bound (i : Fin 9) (s : State) : |siteCharge i s| ≤ 2 := by
  unfold siteCharge siteUp siteDown
  split_ifs <;> norm_num
theorem site_spin_bound (i : Fin 9) (s : State) : |siteSpin i s| ≤ 1 := by
  unfold siteSpin siteUp siteDown
  split_ifs <;> norm_num
theorem site_doublon_bound (i : Fin 9) (s : State) : |siteDoublon i s| ≤ 1 := by
  unfold siteDoublon siteUp siteDown
  split_ifs <;> norm_num

theorem initial_state_masks : initialState.val=(325,170) := rfl
theorem initial_state_particles : bitCount initialState.val.1 9 + bitCount initialState.val.2 9=8 :=
  concrete_particle_number initialState
theorem initial_diagonal_link : (⟨0,4,0⟩ : Link) ∈ links := by decide +kernel
theorem initial_diagonal_fermion_sign : canonicalSign initialState.val ⟨0,4,0⟩ = -1 := by decide +kernel
theorem initial_diagonal_hopping_amplitude : amplitude initialState.val ⟨0,4,0⟩ = -1 := by decide +kernel

end ConcreteH
