# 主脚本,计算教材3-4题潮流.最大负荷情形
# 全程采用标幺值计算,基值：SB=10MVA,VB=118kV=>ZB=1392.4Ω
# 首节点电压：最大负荷时为118kV, 其余节点初始电压不妨按0.95(p.u.)

import numpy as np
import supplement_code

# 3-4题的节点负荷、支路阻抗信息
# 考虑了对地并联支路
load_information_max = np.array([   # 最大负荷情形
    [1, 0.0, -3.926568],
    [2, 0.17, -2.226568],
    [3, 40, 30]
])  # 单位：MW
load_information_max[:, 1:3] = load_information_max[:, 1:3] / 10    # 取标幺值
branch_matrix = np.array([  # 3、支路阻抗
    [1, 2, 8.5, 20.5],
    [2, 3, 1.22, 20.2]
])  # 单位：Ω
branch_matrix[:, 2:4] = branch_matrix[:, 2:4] / 1392.4    # 取标幺值

# 设置收敛精度
episilon = 1e-20

# 初始化实例
calculator_max_load = supplement_code.PowerFlowCalculator(branch_matrix, load_information_max, episilon)
V, angle, Sij = calculator_max_load.Power_flow_calculation()
print("最大负荷情形下，潮流计算的结果(p.u.)：")
print(V)
print(angle)
print(Sij)