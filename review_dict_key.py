"""
========================================
复习：dict key 规则 — 完整演示
========================================
知识点清单:
  1. key 必须是不可变类型
  2. True == 1 → 覆盖
  3. False == 0 → 覆盖
  4. tuple 做 key 有条件
  5. list 做 key → TypeError
========================================
"""

print("=" * 60)
print("1. 哪些能做 key？哪些不能？")
print("=" * 60)

# ✅ 可以的
d = {
    "name": "奶茶",      # str ✅
    1: "数字",           # int ✅
    3.14: "圆周率",      # float ✅
    (1, 2): "元组",      # tuple ✅
    True: "布尔值",      # bool ✅
}
print(f"  ✅ 可变类型做 key → 正常: {d}")

# ❌ 不可以的
# d2 = {["a", "b"]: "列表"}   # TypeError: unhashable type: 'list'
# d3 = {{"k": "v"}: "字典"}   # TypeError: unhashable type: 'dict'
# d4 = {{1, 2}: "集合"}       # TypeError: unhashable type: 'set'

print()
print("  ❌ list/dict/set 做 key 会报错:")
print("     TypeError: unhashable type: 'list'")
print("     根源：dict 底层用哈希表查找 key")
print("     可变类型 → 哈希值可能变 → Python 不允许")


print()
print("=" * 60)
print("2. True == 1 冲突")
print("=" * 60)

d_conflict = {
    True: "这是 True",
    1:    "这是 1",
}
print(f"  {d_conflict}")
print("  明明写了两个 key，结果只有一个值")
print("  因为 Python 认为 True == 1，第二个覆盖了第一个")

# 验证一下
print()
print(f"  True == 1  →  {True == 1}")        # True
print(f"  hash(True) → {hash(True)}")
print(f"  hash(1)    → {hash(1)}")


print()
print("=" * 60)
print("3. False == 0 冲突")
print("=" * 60)

d_false = {
    False: "这是 False",
    0:     "这是 0",
}
print(f"  {d_false}")
print(f"  False == 0 → {False == 0}")        # True


print()
print("=" * 60)
print("4. tuple 做 key 的条件")
print("=" * 60)

# ✅ tuple 里全是不可变 → 可以
d_tuple_ok = {
    (1, 2, 3): "纯数字元组",
    ("a", "b"): "纯字符串元组",
}
print(f"  ✅ 纯不可变 tuple: {d_tuple_ok}")

# ❌ tuple 里有可变类型 → 不行
# d_tuple_bad = {
#     ([1, 2], 3): "有列表的元组",   # TypeError!
# }
print(f"  ❌ 含 list 的 tuple → TypeError")


print()
print("=" * 60)
print("5. 实际陷阱：不小心覆盖了 key")
print("=" * 60)

# 真实场景：用 bool 做判断时不小心覆盖了
scores = {
    "张三": 90,
    True:  100,    # ← 本来想表示"所有及格的人"，但覆盖了 key 1
    1:     95,     # ← 把 True 的值覆盖了
}
print(f"  scores = {scores}")
print(f"  len(scores) = {len(scores)}")     # 只有 2 个，不是 3 个！
print("  原因：True 和 1 是同一个 key")


print()
print("=" * 60)
print("✅ dict key 规则小结")
print("=" * 60)
print("""
  ✅ 能做 key:   str, int, float, bool, tuple(全不可变)
  ❌ 不能做 key: list, dict, set, tuple(含可变类型)

  核心原因：dict 是哈希表，key 必须是可哈希的
          可变类型 → 哈希值会变 → 禁止做 key

  特别注意：
    True == 1   → 互相覆盖
    False == 0  → 互相覆盖
    实际编码时避免把 True/False 和 int 混用做 key
""")


print()
print("=" * 60)
print("✏️ 小测验 — 手指答案再看解析")
print("=" * 60)

print("""
Q1: 下面字典有几个 key？
    d = {
        "apple": 1,
        True: 2,
        1: 3,
    }

Q2: 以下哪些能做 dict key？
    A. [1, 2, 3]
    B. (1, 2, 3)
    C. (1, [2], 3)
    D. "hello"

Q3: 下面代码输出什么？
    d = {}
    d[True] = "真"
    d[1] = "一"
    d[0] = "零"
    d[False] = "假"
    print(d)
""")
