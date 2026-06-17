"""
d2l §3.2 线性回归的从零开始实现
—— 用 PyTorch 写出你刚手算的四步循环

运行方式：在 Windows 的 d2l 环境下，用 Jupyter Notebook 或直接 python 跑
"""

import torch
import random

# ==========================================
# 第1步：生成数据
# ==========================================

# 真实关系：y = 2 * x1 - 3.4 * x2 + 4.2 + 噪声
true_w = torch.tensor([2.0, -3.4])
true_b = 4.2

# 生成 1000 个样本，每个样本有 2 个特征
num_samples = 1000
X = torch.randn(num_samples, 2)                     # 特征：1000×2 的随机矩阵

# ① 前向：ŷ = Xw + b（矩阵乘法）
y = X @ true_w + true_b                             # 真实值（无噪声）

# ② 加一点噪声（模拟真实数据不可能完美）
noise = torch.randn(num_samples) * 0.01             # 小噪声
y = y + noise                                       # 真实值（有噪声）


# ==========================================
# 第2步：初始化参数
# ==========================================

w = torch.normal(0, 0.01, (2, 1), requires_grad=True)   # w：随机初始化，追踪梯度
b = torch.zeros(1, requires_grad=True)                  # b：从 0 开始，追踪梯度

# 把 y 变成 1000×1 的形状，方便后续矩阵运算
y = y.reshape(-1, 1)

eta = 0.03                                           # 学习率（你学的 η）


# ==========================================
# 第3步：定义工具函数
# ==========================================

def data_iter(batch_size, features, labels):
    """
    小批量数据生成器
    作用：从 1000 个样本中，每次随机取 batch 个出来训练
    原因：一次算全部 1000 个太慢，每次算一批更高效
    """
    num = len(features)
    indices = list(range(num))
    random.shuffle(indices)                          # 打乱顺序
    for i in range(0, num, batch_size):
        batch_indices = indices[i: min(i + batch_size, num)]
        yield features[batch_indices], labels[batch_indices]


def squared_loss(y_pred, y_true):
    """MSE 损失：ℓ = (ŷ - y)² / 2"""
    return (y_pred - y_true) ** 2 / 2


def sgd(params, lr, batch_size):
    """
    梯度下降更新参数
    params: 所有要更新的参数（w 和 b）
    lr: 学习率 η
    batch_size: 这批数据的大小（用于算平均梯度）
    """
    with torch.no_grad():                            # 更新参数时不追踪梯度
        for param in params:
            param -= lr * param.grad / batch_size    # ④ 更新：w = w - η·grad
            param.grad.zero_()                       # ③ 清梯度（下次累积用新的）


# ==========================================
# 第4步：训练循环（核心！对应你手算的四步）
# ==========================================

batch_size = 10      # 每次取 10 个样本训练
num_epochs = 5       # 跑 5 轮

for epoch in range(num_epochs):
    for X_batch, y_batch in data_iter(batch_size, X, y):

        # ── ① 前向：预测 ──
        y_pred = X_batch @ w + b                     # ŷ = wx + b

        # ── ② 损失：算错了多少 ──
        loss = squared_loss(y_pred, y_batch)

        # ── ③ 反向传播：自动算梯度 ──
        loss.sum().backward()                        # PyTorch 自动算 ∂ℓ/∂w 和 ∂ℓ/∂b

        # ── ④ 更新参数：梯度下降 ──
        sgd([w, b], eta, batch_size)

    # 每轮结束算一下整体 loss
    with torch.no_grad():
        train_loss = squared_loss(X @ w + b, y).mean()
    print(f"第 {epoch + 1} 轮 → 损失: {train_loss:.6f}")

# ==========================================
# 第5步：查看结果
# ==========================================

print("\n真实 w:   ", true_w)
print("学到的 w:", w.reshape(-1).detach().numpy())
print("\n真实 b:   ", true_b)
print("学到的 b:", b.item())
