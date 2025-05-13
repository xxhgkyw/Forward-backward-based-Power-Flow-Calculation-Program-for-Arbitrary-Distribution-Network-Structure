# 主脚本,计算教材3-3题潮流
# 全程采用标幺值计算,基值：SB=10MVA,VB=35kV=>ZB=122.5Ω
# 首节点电压为35kV,其余节点初始电压不妨按0.95(p.u.)参与计算

import numpy as np
import supplement_code

# 3-3题的节点负荷、支路阻抗信息
# 由于没有考虑对地并联支路,故直接用负荷没问题
load_information = np.array([
    [1, 0.0, 0.0],
    [2, 0.3, 0.2],
    [3, 0.5, 0.3],
    [4, 0.2, 0.3]
])  # 单位：MW
load_information[:, 1:3] = load_information[:, 1:3] / 10    # 取标幺值
branch_matrix = np.array([
    [1, 2, 1.2, 2.4],
    [2, 3, 1.0, 2.0],
    [2, 4, 2.0, 4.0]
])  # 单位：Ω
branch_matrix[:, 2:4] = branch_matrix[:, 2:4] / 122.5    # 取标幺值

# 设置收敛精度
episilon = 1e-20

# 初始化实例
calculator = supplement_code.PowerFlowCalculator(branch_matrix, load_information, episilon)
V, angle, Sij = calculator.Power_flow_calculation()
print(V)
print(angle)
print(Sij)
