import Mathlib.Data.Fintype.Prod
import Mathlib.Data.Finset.Prod
import Mathlib.Tactic.NormNum
set_option autoImplicit false
namespace ConcreteH
abbrev Raw := ℕ × ℕ
structure Link where
  i : ℕ
  j : ℕ
  spin : ℕ
  deriving DecidableEq, Repr
def masks : List ℕ := [15, 23, 39, 71, 135, 263, 27, 43, 75, 139, 267, 51, 83, 147, 275, 99, 163, 291, 195, 323, 387, 29, 45, 77, 141, 269, 53, 85, 149, 277, 101, 165, 293, 197, 325, 389, 57, 89, 153, 281, 105, 169, 297, 201, 329, 393, 113, 177, 305, 209, 337, 401, 225, 353, 417, 449, 30, 46, 78, 142, 270, 54, 86, 150, 278, 102, 166, 294, 198, 326, 390, 58, 90, 154, 282, 106, 170, 298, 202, 330, 394, 114, 178, 306, 210, 338, 402, 226, 354, 418, 450, 60, 92, 156, 284, 108, 172, 300, 204, 332, 396, 116, 180, 308, 212, 340, 404, 228, 356, 420, 452, 120, 184, 312, 216, 344, 408, 232, 360, 424, 456, 240, 368, 432, 464, 480]
def links : List Link := [⟨0, 1, 0⟩, ⟨0, 1, 1⟩, ⟨0, 3, 0⟩, ⟨0, 3, 1⟩, ⟨0, 4, 0⟩, ⟨0, 4, 1⟩, ⟨1, 2, 0⟩, ⟨1, 2, 1⟩, ⟨1, 3, 0⟩, ⟨1, 3, 1⟩, ⟨1, 4, 0⟩, ⟨1, 4, 1⟩, ⟨1, 5, 0⟩, ⟨1, 5, 1⟩, ⟨2, 4, 0⟩, ⟨2, 4, 1⟩, ⟨2, 5, 0⟩, ⟨2, 5, 1⟩, ⟨3, 4, 0⟩, ⟨3, 4, 1⟩, ⟨3, 6, 0⟩, ⟨3, 6, 1⟩, ⟨3, 7, 0⟩, ⟨3, 7, 1⟩, ⟨4, 5, 0⟩, ⟨4, 5, 1⟩, ⟨4, 6, 0⟩, ⟨4, 6, 1⟩, ⟨4, 7, 0⟩, ⟨4, 7, 1⟩, ⟨4, 8, 0⟩, ⟨4, 8, 1⟩, ⟨5, 7, 0⟩, ⟨5, 7, 1⟩, ⟨5, 8, 0⟩, ⟨5, 8, 1⟩, ⟨6, 7, 0⟩, ⟨6, 7, 1⟩, ⟨7, 8, 0⟩, ⟨7, 8, 1⟩]
def maskChunk0 : List ℕ := [15, 23, 39, 71, 135, 263, 27, 43]
def maskChunk1 : List ℕ := [75, 139, 267, 51, 83, 147, 275, 99]
def maskChunk2 : List ℕ := [163, 291, 195, 323, 387, 29, 45, 77]
def maskChunk3 : List ℕ := [141, 269, 53, 85, 149, 277, 101, 165]
def maskChunk4 : List ℕ := [293, 197, 325, 389, 57, 89, 153, 281]
def maskChunk5 : List ℕ := [105, 169, 297, 201, 329, 393, 113, 177]
def maskChunk6 : List ℕ := [305, 209, 337, 401, 225, 353, 417, 449]
def maskChunk7 : List ℕ := [30, 46, 78, 142, 270, 54, 86, 150]
def maskChunk8 : List ℕ := [278, 102, 166, 294, 198, 326, 390, 58]
def maskChunk9 : List ℕ := [90, 154, 282, 106, 170, 298, 202, 330]
def maskChunk10 : List ℕ := [394, 114, 178, 306, 210, 338, 402, 226]
def maskChunk11 : List ℕ := [354, 418, 450, 60, 92, 156, 284, 108]
def maskChunk12 : List ℕ := [172, 300, 204, 332, 396, 116, 180, 308]
def maskChunk13 : List ℕ := [212, 340, 404, 228, 356, 420, 452, 120]
def maskChunk14 : List ℕ := [184, 312, 216, 344, 408, 232, 360, 424]
def maskChunk15 : List ℕ := [456, 240, 368, 432, 464, 480]
theorem masks_chunks : masks = maskChunk0 ++ maskChunk1 ++ maskChunk2 ++ maskChunk3 ++ maskChunk4 ++ maskChunk5 ++ maskChunk6 ++ maskChunk7 ++ maskChunk8 ++ maskChunk9 ++ maskChunk10 ++ maskChunk11 ++ maskChunk12 ++ maskChunk13 ++ maskChunk14 ++ maskChunk15 := by decide +kernel
end ConcreteH
