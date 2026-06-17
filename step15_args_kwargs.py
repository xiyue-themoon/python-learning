"""
============================================
Step 15 — *args 和 **kwargs：灵活的参数
============================================
概念清单:
  1. *args — 收多个位置参数为元组
  2. **kwargs — 收多个关键字参数为字典
  3. 在函数调用时 * 和 ** 的"解包"作用
  4. 实际应用场景
============================================
"""


# ========== 1. *args：收位置参数 ==========
print("=" * 60)
print("1. *args — 收一堆位置参数为一个元组")
print("=" * 60)


def make_combo(*args):
    """任意数量的配料组合"""
    print(f"  你选了配料: {args}")
    print(f"  类型: {type(args)}")
    return " + ".join(args)


# 可以传任意个参数
print(make_combo("珍珠"))
print(make_combo("珍珠", "椰果", "布丁"))
print(make_combo("珍珠", "椰果", "布丁", "仙草", "芋泥"))
print()

print("  *args 把传进来的值打包成一个元组 (tuple)")
print("  名字 args 是约定，重点是 *")


# ========== 2. **kwargs：收关键字参数 ==========
print("\n" + "=" * 60)
print("2. **kwargs — 收一堆关键字参数为一个字典")
print("=" * 60)


def order_drink(**kwargs):
    """自定义饮品"""
    print(f"  订单详情: {kwargs}")
    print(f"  类型: {type(kwargs)}")

    # kwargs 就是个字典
    for key, value in kwargs.items():
        print(f"    {key} = {value}")


order_drink(name="波霸奶茶", size="大杯", sugar="少糖", ice="去冰")
print()
order_drink(name="柠檬养乐多", size="中杯")
print()

print("  **kwargs 把 key=value 打包成一个字典")
print("  名字 kwargs 是约定，重点是 **")


# ========== 3. 到底能干什么？看看真实场景 ==========
print("\n" + "=" * 60)
print("3. 实际用途：写灵活的 API / 透传参数")
print("=" * 60)


# --- 场景 1：打印不同类型的信息 ---
def log_message(level, *messages):
    """可以传任意多条消息"""
    prefix = f"[{level.upper()}]"
    for msg in messages:
        print(f"  {prefix} {msg}")


log_message("info", "系统启动")
log_message("error", "连接失败", "正在重试", "重试成功")
print()


# --- 场景 2：透传参数 ---
# 你封装一个训练函数，用户传各种超参数
def train_model(model_name, **hyperparams):
    print(f"训练 {model_name}:")
    for param, value in hyperparams.items():
        print(f"  {param} = {value}")


train_model("CNN", lr=0.01, epochs=10, batch_size=64)
print()


# --- 场景 3：*和**在调用时是"解包" ---
print("【* 在调用时解包列表】")
nums = [1, 2, 3]
# print(*nums) 等价于 print(1, 2, 3)
print("  print(*[1, 2, 3]) =", end=" ")
print(*nums)

print("【** 在调用时解包字典】")
config = {"name": "波霸奶茶", "size": "大杯", "sugar": "少糖"}
# 等价于 order_drink(name="波霸奶茶", size="大杯", sugar="少糖")
order_drink(**config)


# ========== 4. *args + **kwargs 一起用 ==========
print("\n" + "=" * 60)
print("4. *args + **kwargs 一起用")
print("=" * 60)


def make_drink(size, *toppings, **options):
    """一杯完整的饮品"""
    parts = [f"{size}杯"]
    if toppings:
        parts.append("加料: " + "+".join(toppings))
    if options:
        for k, v in options.items():
            parts.append(f"{k}={v}")

    print("  🧋 " + " | ".join(parts))


make_drink("大", "珍珠", "椰果", sugar="半糖", ice="少冰")
make_drink("中")
make_drink("小", sugar="全糖")


# ========== 小结 ==========
print("\n" + "=" * 60)
print("✅ 总结")
print("=" * 60)
print("""
  *args    → 收位置参数为元组    → def f(*args):
  **kwargs → 收关键字参数为字典  → def f(**kwargs):

  调用时反过来：
  *list    → 解包列表为位置参数  → f(*[1, 2, 3])
  **dict   → 解包字典为关键字参数 → f(**{"a": 1})

  最常见的场景：写装饰器时用 *args, **kwargs 透传
""")
