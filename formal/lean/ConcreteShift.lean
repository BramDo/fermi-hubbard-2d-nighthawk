import ConcreteLogic

noncomputable section
set_option autoImplicit false
open scoped BigOperators
namespace ConcreteH
attribute [local instance] Matrix.linftyOpSeminormedAddCommGroup
  Matrix.linftyOpNormedAddCommGroup Matrix.linftyOpNormedRing

theorem ad_scalar_shift {ι : Type} [Fintype ι] [DecidableEq ι]
    (A O : Matrix ι ι ℝ) (c : ℝ) (n : ℕ) :
    CommutatorRemainder.ad (A-c • (1 : Matrix ι ι ℝ)) O n =
      CommutatorRemainder.ad A O n := by
  induction n with
  | zero => rfl
  | succ n ih =>
    simp only [CommutatorRemainder.ad, ih, sub_mul, mul_sub,
      Matrix.smul_mul, Matrix.mul_smul, one_mul, mul_one]
    abel

theorem concrete_ad_shift (O : Matrix State State ℝ) (n : ℕ) :
    CommutatorRemainder.ad K O n = CommutatorRemainder.ad H O n := by
  rw [K_is_H_minus_16]
  exact ad_scalar_shift H O 16 n

theorem concrete_coefficient_shift (O : Matrix State State ℝ)
    (evaluate : Matrix State State ℝ → ℝ) :
    CommutatorRemainder.coefficient K O evaluate =
      CommutatorRemainder.coefficient H O evaluate := by
  funext n
  simp only [CommutatorRemainder.coefficient, concrete_ad_shift]

theorem concrete_particle_number (s : State) :
    bitCount s.val.1 9 + bitCount s.val.2 9 = 8 := by
  change bitCount s.pair.1.val.val 9 + bitCount s.pair.2.val.val 9 = 8
  rw [s.pair.1.property, s.pair.2.property]

end ConcreteH
