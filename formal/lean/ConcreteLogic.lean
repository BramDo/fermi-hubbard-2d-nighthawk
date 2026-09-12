import ConcreteDefs
import MatrixRemainder

noncomputable section
set_option autoImplicit false
set_option maxRecDepth 100000
set_option maxHeartbeats 5000000
open scoped BigOperators
namespace ConcreteH

def Checked := ∀ s : State, rowCheck s.val = true

theorem packed_matches_interleaved_bits (s : State) :
    packed s.val = spreadSlow s.val.1 + 2*spreadSlow s.val.2 := by
  exact congrArg₂ (fun a b : ℕ => a+2*b) (spread_correct s.pair.1.val) (spread_correct s.pair.2.val)

theorem checked_cost (hc : Checked) (s : State) : cost s.val ≤ 160 := by
  have h := hc s
  simp only [rowCheck, Bool.and_eq_true, decide_eq_true_eq, beq_iff_eq] at h
  exact h.1.1

theorem checked_step (hc : Checked) (s : State) (e : Link) (he : e ∈ links) : GoodStep s.val e := by
  have h := hc s
  simp only [rowCheck, Bool.and_eq_true, decide_eq_true_eq, beq_iff_eq, List.all_eq_true] at h
  exact (stepCheck_correct s.val e).mp (h.2 e he)

theorem checked_decode (hc : Checked) (s : State) : unpacked (packed s.val)=s.val := by
  have h := hc s
  simp only [rowCheck, Bool.and_eq_true, decide_eq_true_eq, beq_iff_eq] at h
  exact h.1.2

theorem state_of_valid (r : Raw) (hr : validRaw r=true) : ∃ s : State, s.val=r := by
  simp only [validRaw, validMask, Bool.and_eq_true, decide_eq_true_eq, beq_iff_eq] at hr
  exact ⟨⟨(⟨⟨r.1,hr.1.1⟩,hr.1.2⟩,⟨⟨r.2,hr.2.1⟩,hr.2.2⟩)⟩,rfl⟩

theorem packed_valid_injective (hc : Checked) (t : State) (r : Raw) (hr : validRaw r=true) :
    packed t.val=packed r ↔ t.val=r := by
  obtain ⟨u,rfl⟩ := state_of_valid r hr
  constructor
  · intro h
    have he := congrArg unpacked h
    simpa only [checked_decode hc t, checked_decode hc u] using he
  · exact congrArg packed

theorem canonical_bond_eq (hc : Checked) (e : Link) (he : e ∈ links) (s t : State) :
    canonicalBond e s t = bond e s t := by
  obtain ⟨ha, hl⟩ := checked_step hc s e he
  by_cases hs : active s.val e = true
  · obtain ⟨hv, _, _, _, htar, hsign⟩ := hl hs
    simp [canonicalBond, bond, amplitude, ha, hs, htar, hsign, packed_valid_injective hc t _ hv]
  · simp [canonicalBond, bond, amplitude, ha, hs]

theorem canonical_H4_eq (hc : Checked) (s t : State) : canonicalH4 s t = H4 s t := by
  unfold canonicalH4 H4
  congr 1
  congr 1
  apply List.map_congr_left
  intro e he
  exact canonical_bond_eq hc e he s t

theorem bond_symmetric (hc : Checked) (e : Link) (he : e ∈ links) (s t : State) :
    bond e s t = bond e t s := by
  by_cases hs : active s.val e = true
  · obtain ⟨_, hsa, hsb, hss, _, _⟩ := (checked_step hc s e he).2 hs
    by_cases hst : t.val = target s.val e
    · have ht : active t.val e = true := by rw [hst]; exact hsa
      have hts : s.val = target t.val e := by rw [hst]; exact hsb.symm
      have hsg : sign t.val e = sign s.val e := by rw [hst]; exact hss
      unfold bond
      rw [if_pos hst, if_pos hts]
      simp [amplitude, hs, ht, hsg]
    · by_cases ht : active t.val e = true
      · obtain ⟨_, _, htb, _, _, _⟩ := (checked_step hc t e he).2 ht
        have hts : s.val ≠ target t.val e := by
          intro eq
          apply hst
          rw [eq]
          exact htb.symm
        simp [bond, hst, hts]
      · simp [bond, amplitude, ht, hst]
  · by_cases ht : active t.val e = true
    · obtain ⟨_, hta, _, _, _, _⟩ := (checked_step hc t e he).2 ht
      have hts : s.val ≠ target t.val e := by
        intro eq
        apply hs
        rw [eq]
        exact hta
      simp [bond, amplitude, hs, hts]
    · simp [bond, amplitude, hs, ht]

theorem H4_symmetric (hc : Checked) (s t : State) : H4 s t = H4 t s := by
  have hm : links.map (fun e => bond e s t) = links.map (fun e => bond e t s) :=
    List.map_congr_left (fun e he => bond_symmetric hc e he s t)
  unfold H4
  rw [hm]
  by_cases h : s=t
  · subst t; rfl
  · simp [h, Ne.symm h]

theorem A4_shift (s t : State) : A4 s t = H4 s t - if s=t then 64 else 0 := by
  unfold A4 H4 shiftedDiagonal
  split_ifs <;> ring

def H : Matrix State State ℝ := fun s t => (H4 s t : ℝ)/4
def K : Matrix State State ℝ := fun s t => (A4 s t : ℝ)/4

theorem real_H_symmetric (hc : Checked) : H.transpose = H := by
  apply Matrix.ext
  intro s t
  simp only [Matrix.transpose_apply, H, H4_symmetric hc t s]

theorem K_is_H_minus_16 : K = H - (16 : ℝ) • (1 : Matrix State State ℝ) := by
  apply Matrix.ext
  intro s t
  simp only [K, H, A4_shift, Int.cast_sub, Matrix.sub_apply, Matrix.smul_apply, smul_eq_mul]
  by_cases h : s=t
  · subst t; simp; ring
  · simp [h]

theorem amplitude_abs (s : Raw) (e : Link) : (amplitude s e).natAbs =
    if active s e then (weight4 e).natAbs else 0 := by
  unfold amplitude sign
  split_ifs <;> simp

theorem int_abs_cast (z : ℤ) : |(z : ℝ)| = (z.natAbs : ℝ) := by
  rw [Nat.cast_natAbs, Int.cast_abs]

theorem onehot_row_bound (r : Raw) (a : ℝ) :
    (∑ t : State, |if t.val=r then a else 0|) ≤ |a| := by
  by_cases hr : ∃ t : State, t.val=r
  · obtain ⟨t, rfl⟩ := hr
    have he : ∀ u : State, u.val=t.val ↔ u=t := fun u => ⟨fun h => state_val_injective h, congrArg State.val⟩
    simp [he, apply_ite]
  · have hn : ∀ t : State, t.val≠r := by simpa using hr
    simp [hn]

theorem bond_row_bound (e : Link) (s : State) :
    (∑ t : State, |(bond e s t : ℝ)|) ≤ (amplitude s.val e).natAbs := by
  simpa only [bond, Int.cast_ite, Int.cast_zero, int_abs_cast] using
    onehot_row_bound (target s.val e) (amplitude s.val e : ℝ)

theorem cast_sum_list (xs : List ℤ) : ((xs.sum : ℤ) : ℝ) = (xs.map (fun (z : ℤ) => (z : ℝ))).sum := by
  induction xs with
  | nil => simp
  | cons x xs ih => simp [ih]

theorem cast_nat_sum_list (xs : List ℕ) : ((xs.sum : ℕ) : ℝ) = (xs.map (fun (z : ℕ) => (z : ℝ))).sum := by
  induction xs with
  | nil => simp
  | cons x xs ih => simp [ih]

theorem kinetic_row_bound (es : List Link) (s : State) :
    (∑ t : State, |(((es.map (fun e => bond e s t)).sum : ℤ) : ℝ)|) ≤
      (es.map (fun e => ((amplitude s.val e).natAbs : ℝ))).sum := by
  induction es with
  | nil => simp
  | cons e es ih =>
    simp only [List.map_cons, List.sum_cons, Int.cast_add]
    calc
      _ ≤ ∑ t : State, (|(bond e s t : ℝ)| + |(((es.map (fun e => bond e s t)).sum : ℤ) : ℝ)|) :=
        Finset.sum_le_sum (fun t _ => abs_add_le _ _)
      _ = _ := Finset.sum_add_distrib
      _ ≤ _ := add_le_add (bond_row_bound e s) ih

theorem A4_row_bound (hc : Checked) (s : State) :
    (∑ t : State, |(A4 s t : ℝ)|) ≤ 160 := by
  have hd : (∑ t : State, |(if s=t then (shiftedDiagonal s.val : ℝ) else 0)|) =
      |(shiftedDiagonal s.val : ℝ)| := by simp [apply_ite]
  have hbudget : |(shiftedDiagonal s.val : ℝ)| +
      (links.map (fun e => ((amplitude s.val e).natAbs : ℝ))).sum = (cost s.val : ℝ) := by
    unfold cost
    rw [Nat.cast_add, ← int_abs_cast]
    rw [cast_nat_sum_list (links.map (fun e => if active s.val e then (weight4 e).natAbs else 0))]
    congr 1
    rw [List.map_map]
    congr 1
    apply List.map_congr_left
    intro e _
    simp [amplitude_abs]
  calc
    _ ≤ ∑ t : State, (|if s=t then (shiftedDiagonal s.val : ℝ) else 0| +
        |(((links.map (fun e => bond e s t)).sum : ℤ) : ℝ)|) := by
      apply Finset.sum_le_sum
      intro t _
      simpa only [A4, Int.cast_add, Int.cast_ite, Int.cast_zero] using
        abs_add_le ((if s=t then shiftedDiagonal s.val else 0 : ℤ) : ℝ)
          (((links.map (fun e => bond e s t)).sum : ℤ) : ℝ)
    _ = _ := Finset.sum_add_distrib
    _ ≤ |(shiftedDiagonal s.val : ℝ)| +
        (links.map (fun e => ((amplitude s.val e).natAbs : ℝ))).sum := by
      rw [hd]
      exact add_le_add le_rfl (kinetic_row_bound links s)
    _ = (cost s.val : ℝ) := hbudget
    _ ≤ 160 := by exact_mod_cast checked_cost hc s

theorem K_row_bound (hc : Checked) (s : State) : (∑ t : State, |K s t|) ≤ 40 := by
  have h := A4_row_bound hc s
  simp only [K, abs_div, show |(4 : ℝ)|=4 by norm_num]
  rw [← Finset.sum_div]
  linarith

end ConcreteH
