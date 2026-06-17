"""
从零实现线性回归 —— 你刚学的四步循环写成代码
"""

# ── 1. 造一些假数据（真实关系：价格 = 2×面积 + 10） ──
data = [
    (1, 12),   # 面积1平 → 真实价12万
    (2, 14),   # 面积2平 → 真实价14万
    (3, 16),
    (4, 18),
    (5, 20),
    (6, 22),
]

# ── 2. 初始化参数 ──
w = 0.0
b = 0.0
eta = 0.01  # 学习率

# ── 3. 训练循环（跑 20 轮） ──
print(f"{'轮次':>4} | {'w':>8} | {'b':>8} | {'总损失':>10}")
print("-" * 40)

for epoch in range(1, 21):
    total_loss = 0.0
    grad_w = 0.0
    grad_b = 0.0

    # 遍历每一条数据
    for x, y_true in data:
        # ① 前向：预测
        y_pred = w * x + b

        # ② 损失（MSE 单样本）
        loss = (y_pred - y_true) ** 2 / 2
        total_loss += loss

        # ③ 梯度（累加所有样本的梯度）
        grad_w += (y_pred - y_true) * x
        grad_b += (y_pred - y_true) * 1

    # ④ 更新参数（用平均梯度）
    n = len(data)
    w = w - eta * (grad_w / n)
    b = b - eta * (grad_b / n)

    print(f"{epoch:>4} | {w:>8.4f} | {b:>8.4f} | {total_loss:>10.4f}")

# ── 4. 验证模型 ──
print("\n验证模型：")
for x, y_true in data:
    y_pred = w * x + b
    print(f"  面积 {x}平 → 预测 {y_pred:.1f}万（真实 {y_true}万）")
