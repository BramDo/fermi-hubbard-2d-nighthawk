import ConcreteDefs
set_option maxRecDepth 100000
set_option maxHeartbeats 20000000
namespace ConcreteH
theorem checked_up_216_chunk_0 : maskChunk0.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_1 : maskChunk1.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_2 : maskChunk2.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_3 : maskChunk3.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_4 : maskChunk4.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_5 : maskChunk5.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_6 : maskChunk6.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_7 : maskChunk7.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_8 : maskChunk8.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_9 : maskChunk9.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_10 : maskChunk10.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_11 : maskChunk11.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_12 : maskChunk12.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_13 : maskChunk13.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_14 : maskChunk14.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216_chunk_15 : maskChunk15.all (fun d => rowCheck (216,d)) = true := by decide +kernel
theorem checked_up_216 : checkUp 216 = true := by
  unfold checkUp
  rw [masks_chunks]
  simp only [List.all_append, checked_up_216_chunk_0, checked_up_216_chunk_1, checked_up_216_chunk_2, checked_up_216_chunk_3, checked_up_216_chunk_4, checked_up_216_chunk_5, checked_up_216_chunk_6, checked_up_216_chunk_7, checked_up_216_chunk_8, checked_up_216_chunk_9, checked_up_216_chunk_10, checked_up_216_chunk_11, checked_up_216_chunk_12, checked_up_216_chunk_13, checked_up_216_chunk_14, checked_up_216_chunk_15, Bool.and_true]
end ConcreteH
