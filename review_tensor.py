# ============================================
# 复习：d2l Ch2 §2.1~2.3 — 4 个核心概念
# ============================================
# 🖥 在 Windows 的 d2l conda 环境里跑
# ============================================

import torch

print("═" * 50)
print("1️⃣  axis 方向 — axis=N 去掉 shape 的第 N 个数字")
print("═" * 50)

# ── 创建个 3 维张量方便理解 ──
t = torch.tensor([
    [[1, 2], [3, 4]],
    [[5, 6], [7, 8]]
])
# shape: [2, 2, 2]
#          ↑  ↑  ↑
#      axis=0 axis=1 axis=2

print(f"t = {t.tolist()}")
print(f"t.shape = {t.shape}")
print()

# axis=0: 去掉最外层括号 → [2, 2]
print(f"t.sum(axis=0) = {t.sum(axis=0).tolist()}")
print(f"  shape: {t.sum(axis=0).shape}")
print(f"  说明：把 2 个 [2×2] 矩阵对应位置相加")
print()

# axis=1: 去掉中间层括号 → [2, 2]
print(f"t.sum(axis=1) = {t.sum(axis=1).tolist()}")
print(f"  shape: {t.sum(axis=1).shape}")
print(f"  说明：在每个矩阵内，把 2 行相加")
print()

# axis=2: 去掉最内层括号 → [2, 2]
print(f"t.sum(axis=2) = {t.sum(axis=2).tolist()}")
print(f"  shape: {t.sum(axis=2).shape}")
print(f"  说明：在每个矩阵内，把 2 列相加")
print()
print("口诀：axis=0 跨行，axis=1 跨列")
print("      axis=N → 去掉 shape 的第 N 个数字")
print()

print("═" * 50)
print("2️⃣  矩阵乘法形状规则")
print("═" * 50)

A = torch.randn(3, 4)
B = torch.randn(4, 5)
C = A @ B
print(f"A.shape = {A.shape}")
print(f"B.shape = {B.shape}")
print(f"A @ B.shape = {C.shape}")
print()
print("公式：A[m, n] @ B[n, p] → [m, p]")
print("  A 的列(4) == B 的行(4) → 可以乘")
print("  结果形状：A 的行(3) × B 的列(5) → [3, 5]")
print()

print("═" * 50)
print("3️⃣  广播机制")
print("═" * 50)

a = torch.tensor([[1], [2], [3]])  # [3, 1]
b = torch.tensor([10, 20, 30])     # [3] → 视为 [1, 3]
print(f"a.shape = {a.shape}")
print(f"b.shape = {b.shape}")
print(f"a + b = ")
print((a + b).tolist())
print()
print("过程：")
print("  a: [3, 1] → 复制列 → [3, 3]")
print("  b:    [3] → [1, 3] → 复制行 → [3, 3]")
print("  然后逐元素加")
print()
print("规则：维度为 1 的轴自动复制补齐到和目标一样长")
print()

print("═" * 50)
print("4️⃣  转置 .T")
print("═" * 50)

m = torch.tensor([[1, 2, 3],
                  [4, 5, 6]])
print(f"m.shape = {m.shape} → m.T.shape = {m.T.shape}")
print(f"m = {m.tolist()}")
print(f"m.T = {m.T.tolist()}")
print()
print("效果：shape [2, 3] → [3, 2]")
print("      行变列，列变行")
print()

print("═" * 50)
print("✅  复习完毕")
print("═" * 50)
