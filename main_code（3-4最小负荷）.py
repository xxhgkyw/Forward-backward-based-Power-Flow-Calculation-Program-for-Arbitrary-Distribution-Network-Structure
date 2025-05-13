# 主脚本,计算教材3-4题潮流.最小负荷情形
# 全程采用标幺值计算,基值：SB=10MVA,VB=113kV=>ZB=1276.9Ω
# 首节点电压：最小负荷时为113kV, 其余节点初始电压不妨按0.95(p.u.)参与计算

import numpy as np
import supplement_code

# 3-4题的节点负荷、支路阻抗信息
# 考虑了对地并联支路
load_information_min = np.array([   # 最小负荷情形
    [1, 0.0, -3.600858],
    [2, 0.17, -1.900858],
    [3, 20, 15]
])  # 单位：MW
load_information_min[:, 1:3] = load_information_min[:, 1:3] / 10    # 取标幺值
branch_matrix = np.array([  # 3、支路阻抗
    [1, 2, 8.5, 20.5],
    [2, 3, 1.22, 20.2]
])  # 单位：Ω
branch_matrix[:, 2:4] = branch_matrix[:, 2:4] / 1276.9    # 取标幺值

# 设置收敛精度
episilon = 1e-20

# 初始化实例
calculator_max_load = supplement_code.PowerFlowCalculator(branch_matrix, load_information_min, episilon)
V, angle, Sij = calculator_max_load.Power_flow_calculation()
print("最小负荷情形下，潮流计算的结果(p.u.)：")
print(V)
print(angle)
print(Sij)