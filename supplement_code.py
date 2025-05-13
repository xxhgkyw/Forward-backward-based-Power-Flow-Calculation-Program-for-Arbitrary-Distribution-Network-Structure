import numpy as np
import math

def get_row_number1(J, S):
    """查找以J为末节点的支路行索引"""
    condition = (S[:, 1] == J)
    row_number = np.where(condition)[0]
    # 确保返回的是单个元素
    if len(row_number) > 0:
        row_number = row_number[0]
    return row_number

def get_row_number2(I, J, S):
    """输入支路(I,J)、需要查找的列表S,返回(I,J)在S中的行索引"""
    condition = (S[:, 0] == I) & (S[:, 1] == J)  # 布尔查找
    row_number = np.where(condition)[0]
    return row_number

def get_row_number3(I, S):
    """查找所有以I为始节点的支路行索引(会返回一个数组,可能有很多)"""
    condition = (S[:, 0] == I)  # 布尔查找
    row_number = np.where(condition)[0]
    return row_number

class PowerFlowCalculator:
    # 一个潮流计算器的类,其实例在main_code.py中初始化
    def __init__(self, branch_matrix, load_information, eps=1e-6):
        self.branch_matrix = branch_matrix  # 支路矩阵 [首节点, 末节点, 电阻, 电抗],在main_code.py中传入
        self.load_information = load_information  # 负荷矩阵 [节点编号, 有功, 无功],在main_code.py中传入
        self.eps = eps  # 收敛精度,可在main_code.py中设置

        # 获取节点总数
        self.node_count = int(max(np.max(branch_matrix[:, 0]), np.max(branch_matrix[:, 1])))

        # 初始化节点电压和相角
        self.V = np.full(self.node_count, 0.95)  # 电压幅值，默认0.95
        self.V[0] = 1.0  # 首节点电压固定为1.0
        self.angle = np.zeros(self.node_count)  # 电压相角，默认0

        # 初始化支路首端功率数组和标志位
        self.Sij_with_indicator = np.zeros((len(branch_matrix), 5))  # len(branch_matrix)是行数,“5”是"搞5列这样的"
        self.Sij_with_indicator[:, 0:2] = branch_matrix[:, 0:2]  # 复制首末节点信息
        # 初始化支路末端功率数组(合并了负荷和子支路首端功率的值)
        self.Sij_end = np.zeros((len(branch_matrix), 4))     # 4列,依次为始节点、末节点、末端有功、末端无功
        self.Sij_end[:, 0:2] = branch_matrix[:, 0:2]        # 复制首末节点信息

        # 先自动获得该配电网算例的叶节点编号
        self.leaf_nodes = self._identify_leaf_nodes()   # leaf_nodes为列表

    def _identify_leaf_nodes(self): # 获取所有叶节点的编号
        leaf_nodes = []

        # 1、遍历所有节点,找出所有叶节点的编号
        for I in range(1, self.node_count + 1):
            child_branches = get_row_number3(I, self.branch_matrix)   # 所有以节点I为始节点的支路行号
            if len(child_branches) == 0:    # 如果节点I不是任何支路的首节点,则必然是叶节点
                leaf_nodes.append(I)

        # 2、为后续后推前方便,这里先把每个叶节点的负荷对应存入Sij_end
        for J in leaf_nodes:
            # 读取叶节点有功、无功负荷
            P_load_leaf_node = self.load_information[J - 1][1]
            Q_load_leaf_node = self.load_information[J - 1][2]

            # 找到以叶节点J作为末节点的支路行号,存入有功、无功负荷值
            branch_idx = get_row_number1(J, self.branch_matrix)
            self.Sij_end[branch_idx][2] = P_load_leaf_node
            self.Sij_end[branch_idx][3] = Q_load_leaf_node

        return leaf_nodes

    def Power_flow_calculation(self):   # 潮流计算主函数,在main_code.py中单独调用
        # 初始化迭代次数和收敛标志
        iteration = 0
        converged = False

        while not converged:
            iteration += 1

            # 1. 后推前
            self._backward_sweep()  # self.V、self.angle旧; self.Sij_with_indicator新
            V_last_iteration = self.V.copy()

            # 2. 前推后
            self._forward_sweep()   # self.V、self.angle新; self.Sij_with_indicator旧
            V_current_iteration = self.V.copy()

            # 3. 检查收敛性(相邻两次迭代,各节点电压幅值之差的绝对值,其中的最大值,是否<self.eps)
            converged = self._check_convergence(V_last_iteration, V_current_iteration)

            # 打印迭代信息
            print(f"迭代次数: {iteration}")

        print("潮流计算收敛！")
        return self.V, self.angle, self.Sij_with_indicator

    # 【1】后推前,从叶节点开始，向根节点计算各支路首端注入功率
    def _backward_sweep(self):
        print("执行后推前推过程...")

        # 重置所有支路标志位为0
        self.Sij_with_indicator[:, 4] = 0

        # 初始化叶节点列表、交叉路口节点列表
        current_leaf_nodes = self.leaf_nodes.copy()     # 【current_leaf_nodes会不断更新】
        crossroads_nodes = []                           # 【crossroads_nodes会不断更新】

        # 只要叶节点列表或分岔节点列表不为空,就继续死循环
        while current_leaf_nodes or crossroads_nodes:  # 这两个列表都会不断更新
            # 1、当前叶节点支路往前算
            while current_leaf_nodes:   # 只要还有叶节点(无论是原始的,还是新加进去的分岔节点)
                leaf_node = current_leaf_nodes.pop(0)   # 从叶节点列表中取出一个,向前计算
                self._process_leaf_node(leaf_node, crossroads_nodes)
                    # 【更新crossroads_nodes列表】函数内部会将叶节点leaf_node前推找到的分岔节点压入之(重复则不压入)

            # 2、检查当前每个分岔节点,是否能够被转化为叶节点
            processed_crossroads = []   # 中转站,后续剔除分岔节点的参考
            for crossroad_node in crossroads_nodes:     # 对于目前已知的所有分岔节点
                # 如果交叉路口节点crossroad_node的所有子支路都被算过了,则执行if语句
                if self._can_process_crossroad(crossroad_node):
                    self._process_crossroad_node(crossroad_node, current_leaf_nodes)
                        # 【更新current_leaf_nodes列表】函数内部会把分岔路口节点crossroad_node作为新的叶节点存入
                    processed_crossroads.append(crossroad_node)
                        # 存入已不再是分岔节点的crossroad_node,指引下面删除

            # 【更新crossroads_nodes列表】将processed_crossroads中记录的分岔路口节点从crossroads_nodes中删除
            for node in processed_crossroads:
                crossroads_nodes.remove(node)

    # 【1-1】从叶节点向前计算，直到遇到交叉路口
    def _process_leaf_node(self, leaf_node, crossroads_nodes):
        current_node = leaf_node    # 初始时,current_node取叶节点

        while True:
            # 获取以current_node为末节点的支路行号
            branch_idx = get_row_number1(current_node, self.branch_matrix)

            # 如果找不到这样的支路，说明已经到达首节点，退出循环
            if branch_idx is None or branch_idx.size == 0:
                break

            # 获取支路信息
            branch = self.branch_matrix[branch_idx]
            from_node = int(branch[0])  # 支路首节点
            to_node = int(branch[1])  # 支路末节点
            rij = branch[2]    # 支路阻抗
            xij = branch[3]
            # 检查该支路是否已处理
            if self.Sij_with_indicator[branch_idx, 4] == 1:
                break

            # 【核心】计算支路首端流入功率
            Pij_sum_end = self.Sij_end[branch_idx][2]     # 获得该支路末端流出功率
            Qij_sum_end = self.Sij_end[branch_idx][3]
            # 后推前,用到Pij_sum_end、Qij_sum_end、V、rij、xij
            Pij_loss = (Pij_sum_end ** 2 + Qij_sum_end ** 2) / (self.V[to_node - 1]) ** 2 * rij # 支路阻抗消耗的有功、无功
            Qij_loss = (Pij_sum_end ** 2 + Qij_sum_end ** 2) / (self.V[to_node - 1]) ** 2 * xij
            Pij = Pij_sum_end + Pij_loss    # 支路首端流入功率
            Qij = Qij_sum_end + Qij_loss
            self.Sij_with_indicator[branch_idx][2] = Pij    # 将支路始端潮流存入self.Sij_with_indicator
            self.Sij_with_indicator[branch_idx][3] = Qij
            # 标记该支路为已处理
            self.Sij_with_indicator[branch_idx, 4] = 1

            # 检查from_node是否为交叉路口节点:
                # 是,则不进行父支路末端功率计算(因为涉及多个子支路),等出去后有专门处理分岔节点的函数帮忙计算
                # 否,则更新Sij_end
            child_branches = get_row_number3(from_node, self.branch_matrix)
            if len(child_branches) > 1:     # from_node是分岔节点
                # 如果是交叉路口且未在列表中，则添加到交叉路口列表(此处的更新会同步到外面crossroads_nodes中)
                if from_node not in crossroads_nodes:   # 如果有重复的,那就不要重复压入了
                    crossroads_nodes.append(from_node)
                break
            else:
                # 更新下一个支路(以from_node为末节点的支路)的末端流出功率
                branch_idx_new = get_row_number1(from_node, self.branch_matrix)
                if branch_idx_new is None or branch_idx_new.size == 0:
                    break
                self.Sij_end[branch_idx_new][2] = Pij + self.load_information[from_node - 1][1]  # 更新Sij_end
                self.Sij_end[branch_idx_new][3] = Qij + self.load_information[from_node - 1][2]

            # 递推,将from_node作为下一次的支路末节点
            current_node = from_node

    # 【1-2】对于某个交叉路口节点crossroad_node,判断它的子支路是否都被算过了
    def _can_process_crossroad(self, crossroad_node):
        child_branches = get_row_number3(crossroad_node, self.branch_matrix)    # 获得所有子支路所在行号

        # 逐个子支路检查其标志位是否已被置为1
        for branch_idx in child_branches:
            if self.Sij_with_indicator[branch_idx, 4] == 0: # 只要有任何一个子支路flag不是1,该交叉路口就不能算！直接返回False
                return False

        # 如果该交叉路口节点的所有子支路都被算过了,则返回True
        return True

    # 【1-3】计算给定交叉路口节点crossroad_node的流出功率，并将其作为新的叶节点存入leaf_nodes中
    def _process_crossroad_node(self, crossroad_node, leaf_nodes):

        # 1-1、获取交叉路口节点crossroad_node的负荷
        load_idx = int(crossroad_node - 1)  # 行索引：节点编号减1
        load = self.load_information[load_idx]  # 读取该行数据(一维列表)
        P_load = load[1]  # 有功负荷
        Q_load = load[2]  # 无功负荷

        # 1-2、计算所有子支路的首端流入功率之和
        Pij = 0
        Qij = 0
        child_branches = get_row_number3(crossroad_node, self.branch_matrix)    # 所有子支路的行索引
        for branch_idx in child_branches:   # 对于每个子支路,将其始端潮流叠加进去
            Pij += self.Sij_with_indicator[branch_idx][2]
            Qij += self.Sij_with_indicator[branch_idx][3]

        # 1-3、叠加上负荷数据,得到分岔节点充当末节点的支路的末端流出功率
        Pij += P_load
        Qij += Q_load

        # 2、将该节点添加到叶节点列表（如果它有父节点）,并将Pij、Qij存入self.Sij_end
        parent_branch_idx = get_row_number1(crossroad_node, self.branch_matrix) # 以分岔节点为末节点的支路行索引
        if parent_branch_idx is not None and parent_branch_idx.size > 0:    # 双重保证
            leaf_nodes.append(crossroad_node)
            self.Sij_end[parent_branch_idx][2] = Pij    # 将Pij、Qij存入self.Sij_end
            self.Sij_end[parent_branch_idx][3] = Qij

    # 【2】# 前推回代过程：从首节点开始,往后更新各节点电压、相角; 会用到前面更新过的self.Sij_with_indicator(各支路首端流入功率)
    def _forward_sweep(self):
        print("执行前推回代过程...")

        # 重置所有支路标志位为0
        self.Sij_with_indicator[:, 4] = 0

        # 从首节点开始
        current_node = 1  # 首节点编号为1
        nodes_to_process = [current_node]

        while nodes_to_process: # 当这个列表不为空时,执行死循环
            node = nodes_to_process.pop(0)

            # 获取以该节点为始节点的所有支路的行索引
            child_branches = get_row_number3(node, self.branch_matrix)

            for branch_idx in child_branches:
                # 检查该支路是否已处理
                if self.Sij_with_indicator[branch_idx, 4] == 1:
                    continue

                # 获取支路信息
                branch = self.branch_matrix[branch_idx]
                from_node = int(branch[0])  # 支路首节点
                to_node = int(branch[1])  # 支路末节点
                rij = branch[2]     # 支路阻抗信息
                xij = branch[3]

                # 【核心】根据首节点电压和支路首端流入功率计算末节点电压、相角
                # 会用到rij、xij、self.Sij_with_indicator、V、angle
                Pij = self.Sij_with_indicator[branch_idx][2]    # 获取“后推前”环节求过的各支路首端流入功率
                Qij = self.Sij_with_indicator[branch_idx][3]
                horizontal_Vij = (Pij * rij + Qij * xij) / self.V[from_node - 1]    # 电压降落纵分量
                vertical_Vij = (Pij * xij - Qij * rij) / self.V[from_node - 1]      # 电压降落横分量
                delta_angleij = math.atan(vertical_Vij / (self.V[from_node - 1] - horizontal_Vij))    # 相角变化(rad)
                # 计算支路末节点的电压幅值、相角
                self.V[to_node - 1] = math.sqrt((self.V[from_node - 1] - horizontal_Vij) ** 2 + vertical_Vij ** 2)
                self.angle[to_node - 1] = self.angle[from_node - 1] - delta_angleij

                # 标记该支路为已处理
                self.Sij_with_indicator[branch_idx, 4] = 1

                # 将to_node添加到待处理列表
                nodes_to_process.append(to_node)

    # 【3】检查收敛性
    def _check_convergence(self, V_last_iteration, V_current_iteration):
        abs_deviation = []  # 记录除首节点以外所有节点在相邻两次迭代中电压幅值差的绝对值
        for i in range(len(V_last_iteration)):
            abs_V = abs(V_last_iteration[i - 1] - V_current_iteration[i - 1])
            abs_deviation.append(abs_V)
        # 如果最大者<给定的收敛精度,则可判定收敛
        if max(abs_deviation) < self.eps:
            return True
        return False