import ConcreteConstants
import Mathlib.Data.Fintype.Powerset
import Mathlib.Data.Nat.Bitwise
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.Ring

/- ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic
Matrix indices are full 4-up/4-down Fock states, not lattice sites. -/
set_option autoImplicit false
set_option maxRecDepth 100000
set_option maxHeartbeats 20000000
namespace ConcreteH

def bitCount : ℕ → ℕ → ℕ
  | _, 0 => 0
  | m, w+1 => m%2 + bitCount (m/2) w
def validMask (m : ℕ) : Bool := decide (m<512) && (bitCount m 9 == 4)
def validRaw (s : Raw) : Bool := validMask s.1 && validMask s.2
def mask (s : Raw) (spin : ℕ) : ℕ := if spin=0 then s.1 else s.2
def spreadSlow (m : ℕ) : ℕ := ((List.range 9).map (fun i => if m.testBit i then 2^(2*i) else 0)).sum
def spread (m : ℕ) : ℕ :=
  let x := Nat.land m 511
  let x := Nat.land (Nat.lor x (x*256)) 16711935
  let x := Nat.land (Nat.lor x (x*16)) 252645135
  let x := Nat.land (Nat.lor x (x*4)) 858993459
  Nat.land (Nat.lor x (x*2)) 1431655765
def packed (s : Raw) : ℕ := spread s.1 + 2*spread s.2
theorem spread_correct : ∀ m : Fin 512, spread m.val = spreadSlow m.val := by decide +kernel
theorem bitcount_nine_correct : ∀ m : Fin 512,
    bitCount m.val 9 = ((List.range 9).filter m.val.testBit).length := by decide +kernel
def unpacked (m : ℕ) : Raw :=
  (((List.range 9).map (fun i => if m.testBit (2*i) then 2^i else 0)).sum,
   ((List.range 9).map (fun i => if m.testBit (2*i+1) then 2^i else 0)).sum)
def active (s : Raw) (e : Link) : Bool := (mask s e.spin).testBit e.i != (mask s e.spin).testBit e.j
def target (s : Raw) (e : Link) : Raw :=
  if e.spin=0 then (Nat.xor s.1 (2^e.i+2^e.j),s.2)
  else (s.1,Nat.xor s.2 (2^e.i+2^e.j))
def weight4 (e : Link) : ℤ :=
  if (e.i%3-e.j%3)+(e.j%3-e.i%3)+(e.i/3-e.j/3)+(e.j/3-e.i/3)=1 then -4 else 1
def sign (s : Raw) (e : Link) : ℤ :=
  if bitCount ((packed s) >>> (2*e.i+e.spin+1))
      ((2*e.j+e.spin)-(2*e.i+e.spin)-1)%2=0 then 1 else -1
def amplitude (s : Raw) (e : Link) : ℤ := if active s e then weight4 e * sign s e else 0
def annihilateMode (s : Raw) (e : Link) : ℕ :=
  if (packed s).testBit (2*e.i+e.spin) then 2*e.i+e.spin else 2*e.j+e.spin
def createMode (s : Raw) (e : Link) : ℕ :=
  if (packed s).testBit (2*e.i+e.spin) then 2*e.j+e.spin else 2*e.i+e.spin
def canonicalActive (s : Raw) (e : Link) : Bool :=
  (packed s).testBit (2*e.i+e.spin) != (packed s).testBit (2*e.j+e.spin)
def canonicalPackedTarget (s : Raw) (e : Link) : ℕ :=
  Nat.lor (Nat.xor (packed s) (2^(annihilateMode s e))) (2^(createMode s e))
def canonicalSign (s : Raw) (e : Link) : ℤ :=
  (if bitCount (packed s) (annihilateMode s e)%2=0 then 1 else -1) *
  (if bitCount (Nat.xor (packed s) (2^(annihilateMode s e))) (createMode s e)%2=0 then 1 else -1)
def doublons (s : Raw) : ℕ := bitCount (Nat.land s.1 s.2) 9
def shiftedDiagonal (s : Raw) : ℤ := 32*(doublons s : ℤ)-64
def cost (s : Raw) : ℕ := (shiftedDiagonal s).natAbs +
  (links.map (fun e => if active s e then (weight4 e).natAbs else 0)).sum

def GoodStep (s : Raw) (e : Link) : Prop :=
  canonicalActive s e = active s e ∧
  (active s e = true → validRaw (target s e) = true ∧ active (target s e) e = true ∧
    target (target s e) e = s ∧ sign (target s e) e = sign s e ∧
    canonicalPackedTarget s e = packed (target s e) ∧ canonicalSign s e = sign s e)
instance (s : Raw) (e : Link) : Decidable (GoodStep s e) := by unfold GoodStep; infer_instance
def stepCheck (s : Raw) (e : Link) : Bool :=
  (canonicalActive s e == active s e) &&
  if active s e then
    validRaw (target s e) && active (target s e) e &&
    (target (target s e) e == s) && (sign (target s e) e == sign s e) &&
    (canonicalPackedTarget s e == packed (target s e)) && (canonicalSign s e == sign s e)
  else true
theorem stepCheck_correct (s : Raw) (e : Link) : stepCheck s e=true ↔ GoodStep s e := by
  by_cases ha : active s e=true <;>
    simp [stepCheck, GoodStep, ha, Bool.and_eq_true, and_assoc]
def rowCheck (s : Raw) : Bool := (cost s ≤ 160) &&
  (unpacked (packed s)==s) && links.all (stepCheck s)
def checkUp (u : ℕ) : Bool := masks.all (fun d => rowCheck (u,d))

def geometricLinks : List Link := (List.range 9).flatMap (fun i =>
  (List.range 9).flatMap (fun j =>
    let dx := (i%3-j%3)+(j%3-i%3)
    let dy := (i/3-j/3)+(j/3-i/3)
    if i<j ∧ (dx+dy=1 ∨ (dx=1 ∧ dy=1)) then [⟨i,j,0⟩,⟨i,j,1⟩] else []))
theorem links_match_geometry : links=geometricLinks := by decide +kernel

theorem masks_complete : ∀ m : Fin 512, m.val ∈ masks ↔ bitCount m.val 9=4 := by
  decide +kernel
theorem masks_nodup : masks.Nodup := by decide +kernel
theorem masks_card : masks.toFinset.card = 126 := by decide +kernel
theorem links_length : links.length=40 := by decide +kernel
theorem link_weights : (links.filter (fun e => weight4 e == -4)).length=24 ∧
    (links.filter (fun e => weight4 e == 1)).length=16 := by decide +kernel

abbrev SpinMask := {m : Fin 512 // bitCount m.val 9=4}
structure State where
  pair : SpinMask × SpinMask
  deriving DecidableEq
def stateEquiv : (SpinMask × SpinMask) ≃ State :=
  ⟨State.mk, State.pair, (by intro s; rfl), (by intro s; cases s; rfl)⟩
instance : Fintype State := Fintype.ofEquiv (SpinMask × SpinMask) stateEquiv
def State.val (s : State) : Raw := (s.pair.1.val.val,s.pair.2.val.val)
theorem state_val_injective : Function.Injective State.val := by
  intro s t h
  cases s with
  | mk s =>
    cases t with
    | mk t =>
      congr 1
      exact Prod.ext (Subtype.ext (Fin.ext (congrArg Prod.fst h)))
        (Subtype.ext (Fin.ext (congrArg Prod.snd h)))
theorem spinmask_card : Fintype.card SpinMask = 126 := by decide +kernel
theorem sector_card : Fintype.card State = 15876 := by
  rw [← Fintype.card_congr stateEquiv, Fintype.card_prod, spinmask_card]

def bond (e : Link) (s t : State) : ℤ := if t.val=target s.val e then amplitude s.val e else 0
def canonicalBond (e : Link) (s t : State) : ℤ :=
  if canonicalActive s.val e then
    if packed t.val=canonicalPackedTarget s.val e then weight4 e*canonicalSign s.val e else 0 else 0
def H4 (s t : State) : ℤ := (if s=t then 32*(doublons s.val : ℤ) else 0) +
  (links.map (fun e => bond e s t)).sum
def A4 (s t : State) : ℤ := (if s=t then shiftedDiagonal s.val else 0) +
  (links.map (fun e => bond e s t)).sum
def canonicalH4 (s t : State) : ℤ := (if s=t then 32*(doublons s.val : ℤ) else 0) +
  (links.map (fun e => canonicalBond e s t)).sum

theorem initial_valid : validRaw (325,170) = true := by decide +kernel
theorem initial_doublons : doublons (325,170) = 0 := by decide +kernel
theorem initial_packed : unpacked (packed (325,170)) = (325,170) := by decide +kernel

end ConcreteH
