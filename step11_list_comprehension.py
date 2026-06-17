"""
============================================
Step 11 — 列表推导式：一行生成列表
============================================
概念清单:
  1. 传统 for 循环 vs 列表推导式
  2. 基本语法 [表达式 for 变量 in 可迭代对象]
  3. 加条件筛选 [表达式 for 变量 in 可迭代对象 if 条件]
  4. 嵌套循环（等价于双重 for）
  5. 字典/集合推导式
  6. 什么时候该用，什么时候别用
============================================
"""

# ========== 1. 为什么需要列表推导式 ==========
print("=" * 60)
print("1. 传统写法 vs 列表推导式")
print("=" * 60)

# 场景：奶茶店菜单价格全部打 8 折
prices = [15, 18, 22, 10, 25]

# --- 传统写法 ---
discounted = []
for p in prices:
    discounted.append(round(p * 0.8, 1))
print(f"传统 for 循环: {discounted}")

# --- 列表推导式 ---
discounted2 = [round(p * 0.8, 1) for p in prices]
print(f"列表推导式:   {discounted2}")
print(f"结果一样，代码少一半 ✨")


# ========== 2. 基本语法拆解 ==========
print("\n" + "=" * 60)
print("2. 语法拆解：把 for 循环翻译成推导式")
print("=" * 60)

print("""
  [round(p * 0.8, 1)   for   p      in   prices]
   └─── 对每个元素做的事 ─┘ └变量┘ └── 数据源 ─┘

  中文翻译：
    "对于 prices 里的每个价格 p，给我算出 p * 0.8 四舍五入"
""")

# 例子 1: 生成 1~10 的平方
squares = [x**2 for x in range(1, 11)]
print(f"1~10 的平方: {squares}")

# 例子 2: 字符串处理
drinks = ["波霸奶茶", "四季春茶", "柠檬养乐多"]
tags = [f"🧋 {d}" for d in drinks]
print(f"加 emoji 标签: {tags}")

# d2l 里长什么样
batch_sizes = [32, 64, 128, 256]
batches = [f"batch_{b}" for b in batch_sizes]
print(f"ML 中常见:   {batches}")


# ========== 3. 加 if 筛选 ==========
print("\n" + "=" * 60)
print("3. 加条件：只要满足条件的元素")
print("=" * 60)

# 筛选出价格 >= 20 的饮品
prices = [15, 18, 22, 10, 25, 30, 12]
expensive = [p for p in prices if p >= 20]
print(f"原价: {prices}")
print(f">=20: {expensive}")

# 同时做筛选和变换
expensive_discounted = [round(p * 0.8, 1) for p in prices if p >= 20]
print(f"贵的打8折: {expensive_discounted}")

# d2l 场景：筛选出长度 > 224 像素的图片尺寸
sizes = [128, 256, 512, 64, 224, 480]
large = [s for s in sizes if s >= 224]
print(f"d2l 场景：>=224px 的图片: {large}")


# ========== 4. 嵌套循环 ==========
print("\n" + "=" * 60)
print("4. 嵌套循环：两个 for 等价于双重循环")
print("=" * 60)

# 菜单组合：奶茶 × 加料
teas = ["波霸", "四季春"]
toppings = ["椰果", "珍珠", "布丁"]

# --- 传统双重循环 ---
combos = []
for t in teas:
    for tp in toppings:
        combos.append(f"{t}+{tp}")
print(f"传统: {combos}")

# --- 列表推导式 ---
combos2 = [f"{t}+{tp}" for t in teas for tp in toppings]
print(f"推导: {combos2}")
print("顺序：从左到右，和传统 for 循环嵌套一致")


# ========== 5. 字典/集合推导式 ==========
print("\n" + "=" * 60)
print("5. 字典/集合推导式")
print("=" * 60)

# 字典推导式：{key: value for ...}
drinks = ["波霸奶茶", "四季春茶", "柠檬养多"]
# 用名字长度做字典
name_len = {d: len(d) for d in drinks}
print(f"字典推导: {name_len}")

# 集合推导式：{表达式 for ...}
scores = [85, 92, 85, 78, 92, 100]
unique_scores = {s for s in scores}
print(f"集合推导（自动去重）: {unique_scores}")


# ========== 6. 什么时候别用 ==========
print("\n" + "=" * 60)
print("6. 什么时候该用，什么时候别用")
print("=" * 60)

print("""
✅ 该用（一行能说清楚）：
  [x**2 for x in range(10)]                  ← 简单变换
  [x for x in data if x > 0]                ← 简单筛选
  {k: v for k, v in pairs}                  ← 字典转换

❌ 别用（写一行太长，反而不易读）：
  [complex_processing(x) for x in data 
   if another_complex_check(x)]              ← 超出了"一眼看懂"的范围

  如果推导式超过 80 个字符，拆成 for 循环吧。
""")

# 适度推导式
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
even_squares = [n**2 for n in numbers if n % 2 == 0]
print(f"偶数的平方: {even_squares} ← 一行清晰明了 ✅")

# 过长的推导式（这已经不太好了）
# result = [heavy_func(x, y) for x in list_a for y in list_b if cond1(x) and cond2(y)]
# print("这种太长了，拆成 for 循环吧")
