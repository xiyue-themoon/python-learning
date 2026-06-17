"""
学习率衰减对比 —— PyTorch 版
固定 η vs 逐步衰减 η，哪个学得更快更准？
"""
import torch
import random

N = 10                       # 特征数
num_samples = 1000
true_w = torch.randn(N) * 2
true_b = 4.2

X = torch.randn(num_samples, N)
y = X @ true_w + true_b + torch.randn(num_samples) * 0.01
y = y.reshape(-1, 1)

batch_size = 10


def data_iter(batch_size, features, labels):
    num = len(features)
    indices = list(range(num))
    random.shuffle(indices)
    for i in range(0, num, batch_size):
        batch_indices = indices[i: min(i + batch_size, num)]
        yield features[batch_indices], labels[batch_indices]


def squared_loss(y_pred, y_true):
    return (y_pred - y_true) ** 2 / 2


def train(use_decay, num_epochs=100):
    w = torch.normal(0, 0.01, (N, 1), requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    eta = 0.1                # 初始学习率（设大一点，对比更明显）
    loss_record = []

    for epoch in range(1, num_epochs + 1):
        # ── 学习率衰减：每 20 轮衰减一次 ──
        if use_decay and epoch % 20 == 0:
            eta *= 0.5       # 减半

        for X_batch, y_batch in data_iter(batch_size, X, y):
            y_pred = X_batch @ w + b
            loss = squared_loss(y_pred, y_batch)
            loss.sum().backward()
            with torch.no_grad():
                w -= eta * w.grad / batch_size
                b -= eta * b.grad / batch_size
                w.grad.zero_()
                b.grad.zero_()

        with torch.no_grad():
            current_loss = squared_loss(X @ w + b, y).mean().item()
            loss_record.append(current_loss)

    return w, b, eta, loss_record


# ── 训练 ──
num_epochs = 100
w_fixed, b_fixed, eta_fixed, loss_fixed = train(use_decay=False, num_epochs=num_epochs)
w_decay, b_decay, eta_decay, loss_decay = train(use_decay=True, num_epochs=num_epochs)

# ── 分析 ──
print("=" * 65)
print(f"{'':>30} | {'固定 η':>10} | {'衰减 η':>10}")
print("=" * 65)
print(f"{'最终损失:':>30} | {loss_fixed[-1]:>10.6f} | {loss_decay[-1]:>10.6f}")
print(f"{'首轮损失:':>30} | {loss_fixed[0]:>10.6f} | {loss_decay[0]:>10.6f}")
print(f"{'最终 η:':>30} | {eta_fixed:>10.4f} | {eta_decay:>10.4f}")
print()

# ── 找到拐点：固定 η 在哪轮开始震荡 ──
print("损失变化趋势（每 10 轮截取）：")
print(f"{'轮次':>6} | {'固定 η':>12} | {'衰减 η':>12} | 说明")
print("-" * 55)
for i in range(0, num_epochs, 10):
    fixed_val = loss_fixed[i]
    decay_val = loss_decay[i]
    note = ""
    if i >= 20 and decay_val < fixed_val:
        note = "← 衰减开始超越"
    elif i >= 20 and fixed_val < decay_val:
        note = "← 固定领先（但可能震荡）"
    print(f"{i:>4} 轮 | {fixed_val:>10.6f} | {decay_val:>10.6f}  {note}")

print()
# ── 尾部 10 轮看震荡 ──
fixed_tail = loss_fixed[-10:]
decay_tail = loss_decay[-10:]
fixed_stable = max(fixed_tail) - min(fixed_tail)
decay_stable = max(decay_tail) - min(decay_tail)
print(f"尾部 10 轮波动幅度（越小越稳定）：")
print(f"  固定 η: {fixed_stable:.8f}")
print(f"  衰减 η: {decay_stable:.8f}")
print(f"  {'衰减更稳定 ✅' if decay_stable < fixed_stable else '固定更稳定'}")
