import DynamicsPilot
open CentralDynamics
example : scalarCoefficient 2 = 1 := by
  rw [coefficient_two]
  norm_num
