"""
学习率衰减对比：固定 η vs 逐步衰减 η
"""

data = [
    (1, 12),
    (2, 14),
    (3, 16),
    (4, 18),
    (5, 20),
    (6, 22),
]

epochs = 200
n = len(data)


def train(use_decay):
    w, b = 0.0, 0.0
    eta = 0.1  # 初始学习率（大一点，看得更清楚）

    for epoch in range(1, epochs + 1):
        # ── 学习率衰减：每 30 轮减半 ──
        if use_decay and epoch % 50 == 0:
            eta = eta * 0.7

        total_loss = 0.0
        grad_w, grad_b = 0.0, 0.0

        for x, y_true in data:
            y_pred = w * x + b
            total_loss += (y_pred - y_true) ** 2 / 2
            grad_w += (y_pred - y_true) * x
            grad_b += (y_pred - y_true) * 1

        w = w - eta * (grad_w / n)
        b = b - eta * (grad_b / n)

    return w, b, eta, total_loss


# ── 训练：固定 η ──
w_fixed, b_fixed, eta_fixed, loss_fixed = train(use_decay=False)

# ── 训练：衰减 η ──
w_decay, b_decay, eta_decay, loss_decay = train(use_decay=True)

print("=" * 60)
print(f"{'':>25} | 固定 η   | 衰减 η")
print("=" * 60)
print(f"{'最终 w (真值=2):':>25} | {w_fixed:>8.4f} | {w_decay:>8.4f}")
print(f"{'最终 b (真值=10):':>25} | {b_fixed:>8.4f} | {b_decay:>8.4f}")
print(f"{'最终损失:':>25} | {loss_fixed:>8.2f} | {loss_decay:>8.2f}")
print(f"{'最终 η:':>25} | {eta_fixed:>8.4f} | {eta_decay:>8.4f}")
print()

print("验证（衰减 η 的模型）：")
for x, y_true in data:
    y_pred = w_decay * x + b_decay
    ok = abs(y_pred - y_true) < 0.5
    mark = " ✅" if ok else " ❌"
    print(f"  面积 {x}平 → 预测 {y_pred:.2f}万（真实 {y_true}万）{mark}")
