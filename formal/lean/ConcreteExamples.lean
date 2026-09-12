import ConcreteObservables

noncomputable section
set_option autoImplicit false
namespace ConcreteH

def nearestHopState : State :=
  ⟨(⟨⟨326,by decide⟩,by decide +kernel⟩,⟨⟨170,by decide⟩,by decide +kernel⟩)⟩
def diagonalHopState : State :=
  ⟨(⟨⟨340,by decide⟩,by decide +kernel⟩,⟨⟨170,by decide⟩,by decide +kernel⟩)⟩
def fourDoublonState : State :=
  ⟨(⟨⟨170,by decide⟩,by decide +kernel⟩,⟨⟨170,by decide⟩,by decide +kernel⟩)⟩

theorem initial_H4_diagonal : H4 initialState initialState=0 := by decide +kernel
theorem nearest_H4_element : H4 initialState nearestHopState = -4 := by decide +kernel
theorem diagonal_H4_element : H4 initialState diagonalHopState = -1 := by decide +kernel
theorem nearest_state_doublons : doublons nearestHopState.val=1 := by decide +kernel
theorem one_doublon_H4_diagonal : H4 nearestHopState nearestHopState=32 := by decide +kernel
theorem four_doublon_H4_diagonal : H4 fourDoublonState fourDoublonState=128 := by decide +kernel
theorem row_budget_witness : cost fourDoublonState.val=160 := by decide +kernel

theorem nearest_H_element : H initialState nearestHopState = -1 := by
  norm_num [H, nearest_H4_element]
theorem diagonal_H_element : H initialState diagonalHopState = -(1/4 : ℝ) := by
  norm_num [H, diagonal_H4_element]
theorem one_doublon_H_diagonal : H nearestHopState nearestHopState = 8 := by
  norm_num [H, one_doublon_H4_diagonal]
theorem four_doublon_H_diagonal : H fourDoublonState fourDoublonState = 32 := by
  norm_num [H, four_doublon_H4_diagonal]

end ConcreteH
