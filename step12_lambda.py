"""
============================================
Step 12 — lambda：一句话函数
============================================
概念清单:
  1. 为什么需要 lambda — 临时用一次的函数
  2. 基本语法 lambda 参数: 返回值
  3. 作为 sorted/map/filter 的参数
  4. lambda 的限制（只能写一行）
  5. 什么时候用 lambda，什么时候用 def
============================================
"""


# ========== 1. lambda 是什么 ==========
print("=" * 60)
print("1. lambda：不用起名字的函数")
print("=" * 60)

# 普通函数
def square(x):
    return x ** 2

# 等价 lambda
square_lambda = lambda x: x ** 2

print(f"def square(3) = {square(3)}")
print(f"lambda x: x**2 (3) = {square_lambda(3)}")
print()

print("""  语法拆解：
  lambda   x:      x ** 2
  └┬──┘  └┬┘      └──┬──┘
  关键字  参数     返回值（不需要写 return）

  lambda 就是"不需要 def 和 return 的一行函数"。
""")


# ========== 2. lambda 最常用的地方：sorted ==========
print("=" * 60)
print("2. 实战：sorted() + lambda 排序")
print("=" * 60)

# 按价格排序
drinks = [
    ("波霸奶茶", 15),
    ("四季春茶", 10),
    ("柠檬养乐多", 18),
    ("杨枝甘露", 22),
]

# 按价格升序（key 告诉 sorted"根据什么排序"）
sorted_by_price = sorted(drinks, key=lambda item: item[1])
print("按价格排序:")
for name, price in sorted_by_price:
    print(f"  {name}: ¥{price}")

# 按名字长度排序
sorted_by_name_len = sorted(drinks, key=lambda item: len(item[0]))
print("\n按名字长度排序:")
for name, price in sorted_by_name_len:
    print(f"  {name} ({len(name)}字)")

# 降序：加 reverse=True
sorted_desc = sorted(drinks, key=lambda item: item[1], reverse=True)
print("\n按价格降序:")
for name, price in sorted_desc:
    print(f"  {name}: ¥{price}")


# ========== 3. map — 对每个元素做变换 ==========
print("\n" + "=" * 60)
print("3. map(function, iterable)：批量变换")
print("=" * 60)

prices = [15, 18, 22, 10, 25]

# map 返回迭代器，用 list() 转成列表
discounted = list(map(lambda p: round(p * 0.8, 1), prices))
print(f"原价: {prices}")
print(f"8折:  {discounted}")

# 其实列表推导式也能做，而且更直观：
discounted2 = [round(p * 0.8, 1) for p in prices]
print(f"推导: {discounted2}")
print("→ Python 社区更倾向用列表推导式，map 用得少了")


# ========== 4. filter — 筛选符合条件的元素 ==========
print("\n" + "=" * 60)
print("4. filter(function, iterable)：筛选")
print("=" * 60)

# 筛选价格 >= 20 的
expensive = list(filter(lambda p: p >= 20, prices))
print(f"原价: {prices}")
print(f">=20: {expensive}")

# 同样可以用列表推导式：
expensive2 = [p for p in prices if p >= 20]
print(f"推导: {expensive2}")


# ========== 5. lambda 的局限 ==========
print("\n" + "=" * 60)
print("5. lambda 只能写一行")
print("=" * 60)

print("""
  ✅ lambda 适合：
    lambda x: x * 2              ← 一次运算
    lambda item: item[1]         ← 取值
    lambda x: x > 0              ← 简单条件

  ❌ lambda 不适合：
    # 以下代码会报语法错误：
    # lambda x:
    #     x = x * 2              ← 不能写语句
    #     return x + 1           ← 不能用 return

  如果需要多行逻辑，用 def：
    def process(x):
        x = x * 2
        return x + 1
""")

# 演示：lambda 只能写表达式，不能写语句
try:
    # 这行会报语法错误 —— 不是代码能解决的问题
    # eval("lambda x: x = 1")  # ← 语法错误
    pass
except SyntaxError:
    pass

print("💡 一句话判断：")
print("  如果逻辑要写超过一行 → 用 def")
print("  如果只是一次简单的变换 → 用 lambda")


# ========== 6. 什么时候用 lambda ==========
print("\n" + "=" * 60)
print("6. 判断准则")
print("=" * 60)

print("""
  用 lambda 的条件（缺一不可）：
    1. 函数体只有一行表达式
    2. 这个函数只用一次，不值得起名字
    3. 作为参数传给另一个函数（sorted/map/max...）

  你未来在 d2l 里最常见的 lambda 用法：
    # 对数据集做变换
    transformed = list(map(lambda x: x.float(), dataset))
""")

# d2l 预热：按张量维度排序
tensors_info = [
    ("conv1", (3, 64, 3, 3)),    # (batch, channel, h, w)
    ("fc1", (512, 256)),
    ("input", (3, 224, 224)),
    ("bias", (256,)),
]
# 按维度数量排序
sorted_by_ndim = sorted(tensors_info, key=lambda t: len(t[1]))
print("按张量维度数排序（d2l 预热）:")
for name, shape in sorted_by_ndim:
    print(f"  {name}: {shape} ({len(shape)}维)")
