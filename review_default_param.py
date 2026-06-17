"""
========================================
复习：默认参数陷阱 — 完整演示
========================================
知识点清单:
  1. 默认参数在函数定义时只创建一次
  2. 可变默认参数（list/dict/set）会累积
  3. 不可变默认参数（int/str/None）没问题
  4. 正确的做法：用 None + 函数体内创建
========================================
"""

print("=" * 60)
print("1. 默认参数陷阱 — 当面看")
print("=" * 60)

def add_to_cart(item, cart=[]):
    """把一个商品加入购物车"""
    cart.append(item)
    return cart

print("  第一次调用：", add_to_cart("奶茶"))
print("  第二次调用：", add_to_cart("汉堡"))
print("  第三次调用：", add_to_cart("薯条"))

print()
print("  预期：每次都是独立的购物车")
print("  实际：购物车一直在累积！")
print("  原因：cart=[] 只在函数定义时创建一次")


print()
print("=" * 60)
print("2. 为什么？看默认参数的地址")
print("=" * 60)

def show_default(x=[]):
    return id(x)

print(f"  第一次: {show_default()}")
print(f"  第二次: {show_default()}")
print(f"  地址一样 → 同一个 []")


print()
print("=" * 60)
print("3. 不可变默认参数没问题")
print("=" * 60)

def add_price(price, tax=0.1):
    """价格 + 税率，默认 10%"""
    return price * (1 + tax)

print(f"  add_price(100)      → {add_price(100)}")
print(f"  add_price(100)      → {add_price(100)}")
print(f"  add_price(100, 0.2) → {add_price(100, 0.2)}")
print("  int 不可变，每次调用都是新值，不会累积 ✅")


print()
print("=" * 60)
print("4. 正确的做法：None + 函数体内创建")
print("=" * 60)

def add_to_cart_safe(item, cart=None):
    """安全的购物车函数"""
    if cart is None:
        cart = []           # 每次没传 cart 时都新建
    cart.append(item)
    return cart

print("  第一次调用：", add_to_cart_safe("奶茶"))
print("  第二次调用：", add_to_cart_safe("汉堡"))
print("  第三次调用：", add_to_cart_safe("薯条"))

print()
print("  ✅ 每次都是新购物车，不会累积！")


print()
print("=" * 60)
print("5. 哪些默认参数会踩坑？")
print("=" * 60)
print("""
  ❌ 危险（可变类型）：
     def func(lst=[]):        ← list
     def func(d={}):          ← dict
     def func(s=set()):       ← set

  ✅ 安全（不可变类型）：
     def func(x=0):           ← int
     def func(s=""):          ← str
     def func(t=()):          ← tuple
     def func(b=True):        ← bool
     def func(x=None):        ← None（最常用）
""")


print()
print("=" * 60)
print("✅ 小结")
print("=" * 60)
print("""
  根因：默认参数在函数定义时创建一次
       之后所有调用共用同一个默认值对象

  可变类型做默认参数 → 累积隐患
  解决方案 → 用 None 做默认，函数体内新建
""")

print()
print("=" * 60)
print("✏️ 小测验")
print("=" * 60)

print("""
Q1: 下面代码输出什么？
    def func(x=[]):
        x.append(len(x))
        return x

    print(func())
    print(func())
    print(func())

Q2: 怎么修复上面的问题？

Q3: 以下哪些默认参数是安全的？
    A. def a(n=0)
    B. def b(data={})
    C. def c(name="")
    D. def d(items=[])
""")
