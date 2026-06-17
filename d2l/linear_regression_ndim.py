"""
N 维线性回归 —— 改 N 的值就能扩展特征数
"""
import torch
import random

# ═══════════════════════════════════════
#  改这里：想用几个特征就把 N 改成几
# ═══════════════════════════════════════
N = 10  # ← 改成任意数字

# 真实 w：N 个权重（随机生成，不再硬编码）
true_w = torch.randn(N) * 2    # N 个随机权重
true_b = 4.2

# 生成 N 个特征、1000 个样本
num_samples = 1000
X = torch.randn(num_samples, N)                     # 1000×N
y = X @ true_w + true_b                             # 真实值
noise = torch.randn(num_samples) * 0.01
y = y + noise
y = y.reshape(-1, 1)

# 初始化参数
w = torch.normal(0, 0.01, (N, 1), requires_grad=True)
b = torch.zeros(1, requires_grad=True)

eta = 0.03
batch_size = 10
num_epochs = 5


def data_iter(batch_size, features, labels):
    num = len(features)
    indices = list(range(num))
    random.shuffle(indices)
    for i in range(0, num, batch_size):
        batch_indices = indices[i: min(i + batch_size, num)]
        yield features[batch_indices], labels[batch_indices]


def squared_loss(y_pred, y_true):
    return (y_pred - y_true) ** 2 / 2


def sgd(params, lr, batch_size):
    with torch.no_grad():
        for param in params:
            param -= lr * param.grad / batch_size
            param.grad.zero_()


# 训练循环（和 2 维时完全一样！）
for epoch in range(num_epochs):
    for X_batch, y_batch in data_iter(batch_size, X, y):
        y_pred = X_batch @ w + b                      # ① 前向
        loss = squared_loss(y_pred, y_batch)          # ② 损失
        loss.sum().backward()                         # ③ 反向传播
        sgd([w, b], eta, batch_size)                   # ④ 更新参数

    with torch.no_grad():
        train_loss = squared_loss(X @ w + b, y).mean()
    print(f"第 {epoch + 1} 轮 → 损失: {train_loss:.6f}")

print(f"\n真实 w ({N} 个):", true_w)
print(f"学到的 w:     ", w.reshape(-1).detach().numpy())
print(f"\n真实 b:       {true_b}")
print(f"学到的 b:     {b.item():.4f}")
