import ConcreteDefs

set_option autoImplicit false
namespace ConcreteH

theorem bitcount_correct (m w : ℕ) :
    bitCount m w = ((List.range w).filter m.testBit).length := by
  induction w generalizing m with
  | zero => simp [bitCount]
  | succ w ih =>
    rw [bitCount, List.range_succ_eq_map]
    have hm := Nat.mod_two_eq_zero_or_one m
    rcases hm with hm | hm <;>
      simp [List.filter_map, Function.comp_def,
        Nat.testBit_succ, Nat.testBit_zero, hm, ← ih, Nat.add_comm]

theorem sign_matches_between_bits (s : Raw) (e : Link) :
    sign s e = if (((List.range ((2*e.j+e.spin)-(2*e.i+e.spin)-1)).filter
      (fun k => (packed s).testBit (2*e.i+e.spin+1+k))).length)%2=0 then 1 else -1 := by
  unfold sign
  rw [bitcount_correct]
  have hp : ((packed s) >>> (2*e.i+e.spin+1)).testBit =
      (fun k => (packed s).testBit (2*e.i+e.spin+1+k)) := by
    funext k
    exact Nat.testBit_shiftRight _
  rw [hp]

end ConcreteH
