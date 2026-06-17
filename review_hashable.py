"""
什么是可哈希 (hashable)？
"""

print("=" * 60)
print("1. 哈希是什么？— 类比懂")
print("=" * 60)
print("""
  图书馆的藏书分类：
    书 → 按书名计算 → 书架编号      ← 这就是哈希函数
    同一本书 → 永远是同一个书架编号   ← 哈希值不变

  Python dict：
     key → 哈希函数 → 哈希值 → 存入对应的桶
  查的时候：
     要找的 key → 哈希函数 → 哈希值 → 直接去对应桶找
         ✨ 不用遍历，一步到位！
""")

print()
print("=" * 60)
print("2. 可哈希的要求（特点）")
print("=" * 60)
print("""
  条件1：哈希值不能变
        一个对象创建后，它的哈希值必须永远不变
        → 可变对象（list/dict/set）哈希值会变 → 不可哈希 ❌

  条件2：相等则哈希值必须相等
        a == b  →  hash(a) == hash(b)  （必须）
        但反过来不要求：hash(a) == hash(b) 不一定 a == b
""")

print()
print("=" * 60)
print("3. 当面看 hash() 函数")
print("=" * 60)

print(f"  hash('hello')    → {hash('hello')}")
print(f"  hash('hello')    → {hash('hello')}")   # 同一个字符串，哈希值一样
print(f"  hash(42)         → {hash(42)}")
print(f"  hash(3.14)       → {hash(3.14)}")
print(f"  hash((1, 2, 3))  → {hash((1, 2, 3))}")

print()
print("=" * 60)
print("4. 不可哈希的对象会怎样？")
print("=" * 60)

try:
    hash([1, 2, 3])
except TypeError as e:
    print(f"  hash([1, 2, 3])  → TypeError: {e}")

try:
    hash({"a": 1})
except TypeError as e:
    print(f"  hash({{'a': 1}}) → TypeError: {e}")

try:
    hash({1, 2, 3})
except TypeError as e:
    print(f"  hash({{1, 2, 3}}) → TypeError: {e}")

print()
print("  原因：list/dict/set 可以修改内容")
print("  内容变了 → 哈希值就会变 → 违反了'哈希值不变'的条件")

print()
print("=" * 60)
print("5. tuple 的特殊情况")
print("=" * 60)

t1 = (1, 2, 3)
print(f"  hash((1, 2, 3))        → {hash(t1)}")       # ✅ 全不可变

t2 = (1, [2, 3])
try:
    hash(t2)
except TypeError as e:
    print(f"  hash((1, [2, 3]))     → TypeError: {e}")  # ❌ 内含 list

print()
print("  → tuple 的哈希值由它的元素决定")
print("  元素里有可变类型 → 整个 tuple 不可哈希")

print()
print("=" * 60)
print("6. 为什么 dict 要求 key 可哈希？")
print("=" * 60)
print("""
  dict 底层结构：哈希表（hash table）

  存的时候：
    dict["apple"] = 1
    → hash("apple") → 找到桶号  → 存进去

  取的时候：
    dict["apple"]
    → hash("apple") → 找到桶号  → 直接取出  ✨ O(1)

  如果 key 可以变：
    先存了 list [1,2] → hash → 桶5
    然后把 list 改成 [1,2,3] → hash 变了！
    再去桶5找 → 找不到了！   💥

  → 所以 Python 直接禁止可变类型做 key
""")

print()
print("=" * 60)
print("✅ 小结")
print("=" * 60)
print("""
  可哈希 ≈ 可以当 dict key / set 元素

  两个条件：
    ① 哈希值不变（生命周期内固定）
    ② a == b 则 hash(a) == hash(b)

  ✅ 可哈希：str, int, float, bool, tuple(全不可变)
  ❌ 不可哈希：list, dict, set, tuple(含可变类型)

  本质原因：哈希表需要 key 稳定不变才能工作
""")
