"""
============================================
Step 16 — 生成器：按需生成，不占内存
============================================
概念清单:
  1. 列表一次性全生成 vs 生成器逐个生成
  2. yield — 生成器的核心
  3. 生成器表达式 (x for x in ...)
  4. 为什么 ML 里需要生成器（大数据集）
============================================
"""


# ========== 1. 问题：列表爆内存 ==========
print("=" * 60)
print("1. 列表 vs 生成器 — 内存差异")
print("=" * 60)

# 列表：一口气生成所有数据
big_list = [x**2 for x in range(10)]
print(f"  列表: {big_list}")
print(f"  列表大小: {big_list.__sizeof__()} 字节")

# 生成器：现用现算
big_gen = (x**2 for x in range(10))
print(f"  生成器: {big_gen}")    # 不是一个列表，是一个生成器对象
print(f"  生成器大小: {big_gen.__sizeof__()} 字节")

print(f"""
  列表             生成器
  ────────────     ────────────
  一次性全算好     等你要的时候才算
  占完整内存       只占几十字节
  可以用索引访问   只能按顺序一个一个拿

  当数据量是 100 万条时：
    列表 → 可能吃掉几个 Gi 内存 ❌
    生成器 → 还是几十个字节 ✅
""")


# ========== 2. yield：生成器的核心 ==========
print("\n" + "=" * 60)
print("2. yield — 函数的'暂停键'")
print("=" * 60)


def count_up_to(n):
    """从 1 数到 n，但每次只给一个数"""
    i = 1
    while i <= n:
        print(f"    → yield {i}")
        yield i  # 暂停，返回 i，等下次被调用
        i += 1
        print(f"    ← 继续执行，i={i}")


print("创建生成器对象...")
counter = count_up_to(3)  # ← 这里不会执行函数体！
print(f"类型: {type(counter)}")
print()

print("第一次调用 next():")
val1 = next(counter)
print(f"  拿到: {val1}")
print()

print("第二次调用 next():")
val2 = next(counter)
print(f"  拿到: {val2}")
print()

print("第三次调用 next():")
val3 = next(counter)
print(f"  拿到: {val3}")
print()

print("第四次（已经没有数据了）:")
try:
    next(counter)
except StopIteration:
    print("  → StopIteration: 生成器没东西了")


# ========== 3. 用 for 循环遍历生成器 ==========
print("\n" + "=" * 60)
print("3. 正常用法：用 for 循环，不用手动 next()")
print("=" * 60)


def tea_menu():
    """奶茶菜单生成器"""
    yield "波霸奶茶"
    yield "四季春茶"
    yield "柠檬养乐多"
    yield "杨枝甘露"


print("今日菜单:")
for drink in tea_menu():
    print(f"  🧋 {drink}")


# ========== 4. d2l 场景：大数据集 ==========
print("\n" + "=" * 60)
print("4. d2l 场景：大数据集按 batch 加载")
print("=" * 60)


def batch_loader(data, batch_size=3):
    """模拟 PyTorch DataLoader：分批产生数据"""
    n = len(data)
    for i in range(0, n, batch_size):
        batch = data[i:i + batch_size]
        print(f"    → yield batch [{i}:{i+batch_size}]")
        yield batch


data = list(range(10))  # 10 个样本
print(f"数据集: {data}, 共 {len(data)} 条")
print("分批加载:")
for batch in batch_loader(data, 3):
    print(f"    拿到 batch: {batch}")

print("""
  PyTorch 的 DataLoader 本质上就是个生成器：
    for batch_x, batch_y in train_loader:
        # 每轮只生成一个 batch 的数据
        # 不会一次性把整个数据集加载到内存
""")


# ========== 5. 生成器表达式 ==========
print("\n" + "=" * 60)
print("5. 生成器表达式 — 推导式的懒加载版本")
print("=" * 60)

# 列表推导式：立即算好
list_squares = [x**2 for x in range(1000000)]
print(f"列表推导式: 已算好 100 万个平方数，内存 = {list_squares.__sizeof__() / 1024 / 1024:.1f}MB")

# 生成器表达式：还没算
gen_squares = (x**2 for x in range(1000000))
print(f"生成器表达式: 还没算，内存 = {gen_squares.__sizeof__()} 字节")

# 需要的时候再转成列表或遍历
print(f"\n取前 5 个: {list(gen_squares)[:5]}")
print(f"取前 5 个后, 生成器已经消耗了前 5 个")


# ========== 小结 ==========
print("\n" + "=" * 60)
print("✅ 总结")
print("=" * 60)
print("""
  列表推导式  [x for x in ...]  → 立即算好，占内存
  生成器表达式 (x for x in ...) → 按需计算，省内存

  def gen():
      yield x     ← 暂停，返回 x
      yield y     ← 下次继续，返回 y

  ML 中：DataLoader 就是生成器
  你不需要自己写生成器，但需要理解它的"按需加载"逻辑
""")
