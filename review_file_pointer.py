"""
========================================
复习：文件指针 — 完整演示
========================================
知识点清单:
  1. 指针从开头开始
  2. .read() 读完 → 指针在末尾
  3. .readlines() 也会移动指针
  4. .readline() 读一行移一行
  5. 指针末尾再读 → 空
  6. 解决方案：.seek(0) 或 with open
  7. with 语句
========================================
"""

# 先写一个测试文件
with open("/tmp/test_file.txt", "w", encoding="utf-8") as f:
    f.write("第一行\n第二行\n第三行\n")

print("=" * 60)
print("1. 文件指针 — 它就像磁带/播放头")
print("=" * 60)
print("""
  打开文件 → 指针在最前面（就像刚放进去的磁带）
  读取内容 → 指针向前走（播放头往前走）
  读完所有 → 指针在最后面（磁带播完了）
  再读     → 什么都读不到（没有内容了）
""")

# ========== 2. .read() 后指针到末尾 ==========
print("\n" + "=" * 60)
print("2. .read() 读完所有 → 指针到末尾")
print("=" * 60)

f = open("/tmp/test_file.txt", "r", encoding="utf-8")
print(f"  第一次 read() → {repr(f.read())}")     # 读完
print(f"  第二次 read() → {repr(f.read())}")     # 空的！
f.close()
print("  → 第一次全读完了，第二次指针在末尾，啥也没读到")


# ========== 3. .readlines() 同理 ==========
print("\n" + "=" * 60)
print("3. .readlines() 也会移动指针")
print("=" * 60)

f = open("/tmp/test_file.txt", "r", encoding="utf-8")
print(f"  .readlines() → {f.readlines()}")       # 读完所有行
print(f"  .readlines() → {f.readlines()}")       # 空的！
f.close()


# ========== 4. .readline() 一次读一行 ==========
print("\n" + "=" * 60)
print("4. .readline() 读一行，指针走一行")
print("=" * 60)

f = open("/tmp/test_file.txt", "r", encoding="utf-8")
print(f"  第1行: {repr(f.readline())}")
print(f"  第2行: {repr(f.readline())}")
print(f"  第3行: {repr(f.readline())}")
print(f"  第4行: {repr(f.readline())}")    # 没内容了
f.close()


# ========== 5. for line in f 安全循环 ==========
print("\n" + "=" * 60)
print("5. 最推荐：for line in f — 逐行读，不担心指针")
print("=" * 60)

f = open("/tmp/test_file.txt", "r", encoding="utf-8")
for line in f:
    print(f"  → {repr(line)}")
f.close()


# ========== 6. 解决方案 ==========
print("\n" + "=" * 60)
print("6. 解决方案 — 三种做法")
print("=" * 60)

# 方案A: 读完一次后 .seek(0) 重置指针
print("方案A: .seek(0) 把指针拨回开头")
f = open("/tmp/test_file.txt", "r", encoding="utf-8")
all_text = f.read()
print(f"  第一次 read(): {len(all_text)} 个字符")
f.seek(0)                                     # ← 指针重置到开头
print(f"  .seek(0) 后再次 read(): {len(f.read())} 个字符 ✅")
f.close()

# 方案B: 只选一种方式，不混用
print("\n方案B: 只选一种方式，不混用")
f = open("/tmp/test_file.txt", "r", encoding="utf-8")
# ✅ 选一种：要么 read()，要么 readlines()，要么 for line
content = f.read()
print(f"  用 .read() 专一读完: {len(content)} 字符")
f.close()

# 方案C: with 语句（自动关文件，省心）
print("\n方案C: with open — 最推荐")
with open("/tmp/test_file.txt", "r", encoding="utf-8") as f:
    content = f.read()
    print(f"  with 块内: {len(content)} 字符")
    # with 块结束自动 .close()，不用手动关
print(f"  with 块外: 文件已自动关闭 ✅")


# ========== 小结 ==========
print("\n" + "=" * 60)
print("✅ 文件指针小结")
print("=" * 60)
print("""
  打开文件 = 放磁带，指针在开头
  .read()  = 播完整个磁带，指针在最后
  .seek(0) = 把指针拨回开头
  for line in f = 逐行读（最常用，不出错）

  黄金法则：不要混用读法，选一种坚持到底
  省心写法：with open(...) as f:
""")


# ========== 小测验 ==========
print("\n" + "=" * 60)
print("✏️ 小测验 — 用手指数完再看答案")
print("=" * 60)

print("""
Q1: 用 .read() 读完后，紧接着 .readlines() 会返回什么？

Q2: 用 .readlines() 读到一半想从头再读，怎么办？

Q3: 下面代码输出什么？
    f = open("test.txt", "r")
    for line in f:
        print(line)
    for line in f:
        print(line)
""")
