"""
PyTorch 启动模板 —— 每次写 PyTorch 代码前复制这个
"""

# ── 1. 导入 ──
import torch
import torch.nn as nn          # 神经网络模块
import torch.optim as optim    # 优化器（梯度下降的各种变体）
import numpy as np

# ── 2. 检查环境 ──
print(f"PyTorch 版本: {torch.__version__}")
print(f"CUDA 可用: {torch.cuda.is_available()}")

# 如果有 GPU 就用 GPU，没有就用 CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {device}")

# ── 3. 常用操作速查 ──

# 创建张量
x = torch.tensor([1, 2, 3])               # 从列表创建
x = torch.zeros(3, 4)                     # 全 0 矩阵 3×4
x = torch.ones(3, 4)                      # 全 1 矩阵 3×4
x = torch.randn(3, 4)                     # 随机正态分布 3×4

# 形状操作
print(x.shape)                            # 形状
print(x.size())                           # 同上

# 基本运算
y = x + 1                                 # 逐元素加法
z = x @ y.T                               # 矩阵乘法（@ 符号）
z = torch.matmul(x, y.T)                  # 矩阵乘法（显式写法）

# 梯度相关
w = torch.tensor([2.0], requires_grad=True)   # 需要追踪梯度
loss = (w - 5) ** 2                           # 定义损失
loss.backward()                               # 自动算梯度
print(w.grad)                                 # 打印梯度 → tensor([-6.])


# ── 4. 最简单的训练循环模板 ──
"""
x = torch.tensor([[1.0], [2.0], [3.0]])
y = torch.tensor([[3.0], [5.0], [7.0]])    # 真实关系: y = 2x + 1

model = nn.Linear(1, 1)                    # 模型: ŷ = wx + b
criterion = nn.MSELoss()                   # 损失: MSE
optimizer = optim.SGD(model.parameters(), lr=0.01)  # 优化器: 梯度下降

for epoch in range(100):
    y_pred = model(x)                      # ① 前向
    loss = criterion(y_pred, y)            # ② 损失
    optimizer.zero_grad()                  # ③ 清梯度
    loss.backward()                        # ④ 反向传播（算梯度）
    optimizer.step()                       # ⑤ 更新参数（梯度下降）
"""
