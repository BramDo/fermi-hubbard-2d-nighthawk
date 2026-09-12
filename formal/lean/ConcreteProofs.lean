import ConcreteCertificate
import ConcreteLogic
import ConcreteBits
import ConcreteShift
import ConcreteObservables
import ConcreteExamples
import Mathlib.LinearAlgebra.Matrix.ConjTranspose
import Mathlib.Data.Complex.Basic

noncomputable section
set_option autoImplicit false
set_option maxHeartbeats 5000000
open scoped BigOperators
namespace ConcreteH

theorem all_sector_checked : Checked := by
  intro s
  have hu : s.pair.1.val.val ∈ masks := (masks_complete s.pair.1.val).2 s.pair.1.property
  have hd : s.pair.2.val.val ∈ masks := (masks_complete s.pair.2.val).2 s.pair.2.property
  have h := List.all_eq_true.mp all_rows_checked s.pair.1.val.val hu
  exact List.all_eq_true.mp h s.pair.2.val.val hd

theorem concrete_canonical_H4 : canonicalH4 = H4 := by
  funext s t
  exact canonical_H4_eq all_sector_checked s t

theorem concrete_H_symmetric : H.transpose = H := real_H_symmetric all_sector_checked

def complexH : Matrix State State ℂ := fun s t => (H s t : ℂ)
theorem concrete_H_hermitian : complexH.conjTranspose = complexH := by
  apply Matrix.ext
  intro s t
  have h : H t s = H s t := congrFun (congrFun concrete_H_symmetric s) t
  simp [complexH, Matrix.conjTranspose_apply, h]

theorem concrete_hop_preserves_sector (s : State) (e : Link) (he : e ∈ links)
    (ha : active s.val e = true) : validRaw (target s.val e) = true :=
  ((checked_step all_sector_checked s e he).2 ha).1

theorem concrete_canonical_fermion_sign (s : State) (e : Link) (he : e ∈ links)
    (ha : active s.val e=true) : canonicalSign s.val e=sign s.val e :=
  ((checked_step all_sector_checked s e he).2 ha).2.2.2.2.2

theorem concrete_row_bound (s : State) : (∑ t : State, |K s t|) ≤ 40 :=
  K_row_bound all_sector_checked s

attribute [local instance] Matrix.linftyOpSeminormedAddCommGroup
  Matrix.linftyOpNormedAddCommGroup Matrix.linftyOpNormedRing

theorem concrete_shifted_norm : ‖K‖ ≤ 40 :=
  MatrixRemainder.row_sum_norm_bound K 40 (by norm_num) concrete_row_bound

theorem concrete_shifted_H_norm : ‖H - (16 : ℝ) • (1 : Matrix State State ℝ)‖ ≤ 40 := by
  rw [← K_is_H_minus_16]
  exact concrete_shifted_norm

theorem concrete_even_charge_remainder (v : State → ℝ) (s : State) (T : ℝ)
    (hv : ∀ i, |v i| ≤ 2) (hT : |T| ≤ 2/5) :
    |(∑' n, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient K (Matrix.diagonal v) (fun X => X s s)) T n) -
      ∑ n ∈ Finset.range 55, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient K (Matrix.diagonal v) (fun X => X s s)) T n| < 5058/10^16 :=
  MatrixRemainder.matrix_charge_remainder K v s T concrete_row_bound hv hT

theorem concrete_H_charge_remainder (v : State → ℝ) (s : State) (T : ℝ)
    (hv : ∀ i, |v i| ≤ 2) (hT : |T| ≤ 2/5) :
    |(∑' n, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient H (Matrix.diagonal v) (fun X => X s s)) T n) -
      ∑ n ∈ Finset.range 55, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient H (Matrix.diagonal v) (fun X => X s s)) T n| < 5058/10^16 := by
  simpa only [concrete_coefficient_shift] using concrete_even_charge_remainder v s T hv hT

theorem concrete_H_unit_remainder (v : State → ℝ) (s : State) (T : ℝ)
    (hv : ∀ i, |v i| ≤ 1) (hT : |T| ≤ 2/5) :
    |(∑' n, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient H (Matrix.diagonal v) (fun X => X s s)) T n) -
      ∑ n ∈ Finset.range 55, EvenTaylorRemainder.evenTerm
        (CommutatorRemainder.coefficient H (Matrix.diagonal v) (fun X => X s s)) T n| < 2529/10^16 := by
  simpa only [concrete_coefficient_shift] using
    MatrixRemainder.matrix_unit_remainder K v s T concrete_row_bound hv hT

theorem concrete_H_odd_terms_zero (v : State → ℝ) (s : State) (n : ℕ) :
    CommutatorRemainder.ad H (Matrix.diagonal v) (2*n+1) s s = 0 :=
  MatrixRemainder.odd_diagonal_commutator_zero H v s concrete_H_symmetric n

def observableRemainder (v : State → ℝ) (T : ℝ) : ℝ :=
  |(∑' n, EvenTaylorRemainder.evenTerm
      (CommutatorRemainder.coefficient H (Matrix.diagonal v) (fun X => X initialState initialState)) T n) -
    ∑ n ∈ Finset.range 55, EvenTaylorRemainder.evenTerm
      (CommutatorRemainder.coefficient H (Matrix.diagonal v) (fun X => X initialState initialState)) T n|

theorem concrete_site_charge_remainder (i : Fin 9) (T : ℝ) (hT : |T| ≤ 2/5) :
    observableRemainder (siteCharge i) T < 5058/10^16 :=
  concrete_H_charge_remainder (siteCharge i) initialState T (site_charge_bound i) hT

theorem concrete_site_spin_remainder (i : Fin 9) (T : ℝ) (hT : |T| ≤ 2/5) :
    observableRemainder (siteSpin i) T < 2529/10^16 :=
  concrete_H_unit_remainder (siteSpin i) initialState T (site_spin_bound i) hT

theorem concrete_site_doublon_remainder (i : Fin 9) (T : ℝ) (hT : |T| ≤ 2/5) :
    observableRemainder (siteDoublon i) T < 2529/10^16 :=
  concrete_H_unit_remainder (siteDoublon i) initialState T (site_doublon_bound i) hT

end ConcreteH
