"""
手写版 → 框架版 逐行对比
"""
import torch
import torch.nn as nn          # nn.Linear, nn.MSELoss
import torch.optim as optim    # optim.SGD
import random

N = 10
num_samples = 1000
true_w = torch.randn(N) * 2
true_b = 4.2

X = torch.randn(num_samples, N)
y = X @ true_w + true_b + torch.randn(num_samples) * 0.01
y = y.reshape(-1, 1)

batch_size = 10

# ════════════════════════════════════════════════
# 方案 A：手写版（你目前的样子）
# ════════════════════════════════════════════════

def data_iter(batch_size, features, labels):
    num = len(features)
    indices = list(range(num))
    random.shuffle(indices)
    for i in range(0, num, batch_size):
        batch_indices = indices[i: min(i + batch_size, num)]
        yield features[batch_indices], labels[batch_indices]


def squared_loss(y_pred, y_true):
    return (y_pred - y_true) ** 2 / 2


def train_manual():
    w = torch.normal(0, 0.01, (N, 1), requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    eta = 0.03

    for epoch in range(5):
        for X_batch, y_batch in data_iter(batch_size, X, y):
            y_pred = X_batch @ w + b                     # 前向
            loss = squared_loss(y_pred, y_batch)          # 损失
            loss.sum().backward()                         # 反向
            with torch.no_grad():
                w -= eta * w.grad / batch_size             # 更新 w
                b -= eta * b.grad / batch_size             # 更新 b
                w.grad.zero_()
                b.grad.zero_()
    return w, b


# ════════════════════════════════════════════════
# 方案 B：框架版（PyTorch 替你管了 5 件事）
# ════════════════════════════════════════════════

def train_framework():
    model = nn.Linear(N, 1)                        # ① 模型：ŷ = wx + b
    criterion = nn.MSELoss()                        # ② 损失：MSE
    optimizer = optim.SGD(model.parameters(), lr=0.03)  # ③ 优化器：梯度下降

    for epoch in range(5):
        for X_batch, y_batch in data_iter(batch_size, X, y):
            y_pred = model(X_batch)                  # ① 前向
            loss = criterion(y_pred, y_batch)         # ② 损失
            optimizer.zero_grad()                    # ③ 清梯度
            loss.backward()                          # ④ 反向传播
            optimizer.step()                         # ⑤ 更新参数
    return model.weight, model.bias


# ════════════════════════════════════════════════
# 跑起来对比
# ════════════════════════════════════════════════

w_man, b_man = train_manual()
w_frm, b_frm = train_framework()

print("方案 A：手写版")
print(f"  w: {w_man.reshape(-1).detach().numpy()}")
print(f"  b: {b_man.item():.4f}")

print("\n方案 B：框架版")
print(f"  w: {w_frm.reshape(-1).detach().numpy()}")
print(f"  b: {b_frm.item():.4f}")

print("\n真实值")
print(f"  w: {true_w}")
print(f"  b: {true_b}")

print("\n差异对比（手写 vs 框架）：")
w_diff = (w_man - w_frm.T).abs().max().item()
b_diff = abs(b_man.item() - b_frm.item())
print(f"  w 最大差异: {w_diff:.8f}")
print(f"  b 差异:     {b_diff:.8f}")
if w_diff < 0.01 and b_diff < 0.01:
    print("  ✅ 两种写法等价")
