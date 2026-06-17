"""
============================================
Step 13 — zip & enumerate：两个遍历神器
============================================
概念清单:
  1. enumerate — 遍历时顺便拿序号
  2. zip — 把多个列表"拉链"到一起
  3. zip(*) — 解压缩
  4. enumerate + zip 组合使用
  5. d2l 中的常见场景
============================================
"""


# ========== 1. enumerate：边遍历边计数 ==========
print("=" * 60)
print("1. enumerate — 遍历时带上编号")
print("=" * 60)

menu = ["波霸奶茶", "四季春茶", "柠檬养乐多", "杨枝甘露"]

# --- 传统写法：手动计数 ---
print("【传统写法】")
i = 0
for drink in menu:
    print(f"  {i+1}. {drink}")
    i += 1

# --- enumerate 写法 ---
print("\n【enumerate 写法】")
for i, drink in enumerate(menu):
    print(f"  {i+1}. {drink}")

# 从 1 开始计数
print("\n【从1开始计数】")
for i, drink in enumerate(menu, start=1):
    print(f"  {i}. {drink}")


# ========== 2. zip：把多个列表并排遍历 ==========
print("\n" + "=" * 60)
print("2. zip — 像拉链一样把列表合在一起")
print("=" * 60)

drink_names = ["波霸奶茶", "四季春茶", "柠檬养乐多", "杨枝甘露"]
drink_prices = [15, 10, 18, 22]
sales_today = [42, 38, 15, 27]

# --- 传统写法：用索引 ---
print("【传统索引写法】")
for i in range(len(drink_names)):
    print(f"  {drink_names[i]}: ¥{drink_prices[i]}, 今日售{sales_today[i]}杯")

# --- zip 写法 ---
print("\n【zip 写法】")
for name, price, sales in zip(drink_names, drink_prices, sales_today):
    print(f"  {name}: ¥{price}, 今日售{sales}杯")

print("\n  → 少了 range(len(...)) 和索引，更清晰")


# ========== 3. zip 构建字典 ==========
print("\n" + "=" * 60)
print("3. zip → dict：快速配对")
print("=" * 60)

# 两列数据合成字典
menu_dict = dict(zip(drink_names, drink_prices))
print(f"菜单字典: {menu_dict}")

# 三列也能配对
sales_report = list(zip(drink_names, drink_prices, sales_today))
print(f"销售报表: {sales_report}")


# ========== 4. zip(*) 解压缩 ==========
print("\n" + "=" * 60)
print("4. zip(*) — 反向操作：把配对的数据拆开")
print("=" * 60)

# 假设你有一组配对数据
pairs = [("波霸奶茶", 15), ("四季春茶", 10), ("柠檬养乐多", 18)]
names, prices = zip(*pairs)  # * 表示"拆开这个列表"

print(f"配对数据: {pairs}")
print(f"拆出名字: {names}")
print(f"拆出价格: {prices}")

# 这个在 d2l 里常见：从 DataLoader 拿到 (features, labels) 对
data_pairs = [
    ([1.0, 2.0], 0),
    ([2.0, 3.0], 1),
    ([3.0, 4.0], 0),
]
features, labels = zip(*data_pairs)
print(f"\n[d2l 场景] features: {list(features)}")
print(f"[d2l 场景] labels:   {list(labels)}")


# ========== 5. enumerate + zip 组合 ==========
print("\n" + "=" * 60)
print("5. 组合拳：同时取序号 + 多列表遍历")
print("=" * 60)

for i, (name, price) in enumerate(zip(drink_names, drink_prices), 1):
    print(f"  #{i}. {name} — ¥{price}")

# d2l 场景：打印每个 epoch 的 loss
epochs = [1, 2, 3, 4, 5]
train_loss = [0.85, 0.62, 0.41, 0.33, 0.28]
val_loss = [0.92, 0.71, 0.53, 0.44, 0.38]

print("\n[d2l 场景] 训练日志:")
for epoch, tl, vl in zip(epochs, train_loss, val_loss):
    print(f"  Epoch {epoch}: train_loss={tl:.4f}, val_loss={vl:.4f}")


# ========== 小结 ==========
print("\n" + "=" * 60)
print("✅ 一句话记住")
print("=" * 60)
print("""
  enumerate → 遍历时带编号         for i, x in enumerate(list):
  zip       → 把多个列表并排遍历    for a, b in zip(list1, list2):
  zip(*zip) → 把配对数据拆回多列    list1, list2 = zip(*pairs):

  你会在 d2l 的每一页看到它们 ✨
""")
