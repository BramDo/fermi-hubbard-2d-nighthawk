import DynamicsPilot
open CentralDynamics
example : scalarCoefficient 4 = 2 := by
  rw [coefficient_four]
  norm_num
