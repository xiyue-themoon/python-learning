"""
================================================================
d2l §4.2: 多层感知机从零实现 —— MLP from Scratch
================================================================
手动实现一个隐藏层 + ReLU + 输出层，然后在 Fashion-MNIST 上跑分类。

对比 d2l_32_linear_regression.py，唯一的区别就是：
  模型从 y = X@W + b                ← 线性回归
  变成  h = max(0, X@W1 + b1)       ← 隐藏层 + ReLU（新东西）
        y = h@W2 + b2                ← 输出层

运行方式: python d2l_42_mlp_scratch.py
依赖: PyTorch + torchvision（d2l 环境自带）
"""

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import matplotlib.pyplot as plt

# ======================== 参数设置 ========================
batch_size = 256
num_inputs = 784    # 28×28 像素，拉平成一维
num_hiddens = 256   # 隐藏层神经元数量（可调）
num_outputs = 10    # 10 个类别（0~9 数字/服装）
lr = 0.1
num_epochs = 10


# ======================== 1. 加载 Fashion-MNIST 数据集 ========================

# 下载 + 转 Tensor + 归一化到 [0,1]
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))  # 归一化到 [-1, 1]
])

train_dataset = datasets.FashionMNIST(
    root='./data', train=True, download=True, transform=transform)
test_dataset = datasets.FashionMNIST(
    root='./data', train=False, download=True, transform=transform)

train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

# Fashion-MNIST 的 10 个类别名称
class_names = ['T恤', '裤子', '套衫', '裙子', '外套',
               '凉鞋', '衬衫', '运动鞋', '包', '短靴']


# ======================== 2. 初始化参数 ========================

def init_mlp_params(num_inputs, num_hiddens, num_outputs):
    """初始化 MLP 的两层权重和偏置"""
    # 第一层：输入 → 隐藏层        W1: (784, 256),  b1: (256,)
    # 第二层：隐藏层 → 输出层      W2: (256, 10),   b2: (10,)
    #
    # 为什么 W1 是 (num_inputs, num_hiddens) 而不是反的？
    #   因为前向公式是 h = X @ W1 + b1
    #   X 形状 (batch, 784), W1 (784, 256)
    #   矩阵乘: (batch, 784) @ (784, 256) → (batch, 256)  ✓

    W1 = torch.normal(0, 0.01, (num_inputs, num_hiddens), requires_grad=True)
    b1 = torch.zeros(num_hiddens, requires_grad=True)
    W2 = torch.normal(0, 0.01, (num_hiddens, num_outputs), requires_grad=True)
    b2 = torch.zeros(num_outputs, requires_grad=True)

    return [W1, b1, W2, b2]


params = init_mlp_params(num_inputs, num_hiddens, num_outputs)


# ======================== 3. 定义 MLP 前向传播 ========================

def relu(X):
    """ReLU：max(0, x)，把所有负数砍成 0"""
    # 等价于: return torch.maximum(X, torch.tensor(0.0))
    return torch.max(X, torch.tensor(0.0))


def mlp_forward(X, params):
    """
    MLP 前向传播的完整流程

    输入 X: (batch_size, 784)   ← 28×28 图片拉平了
          │
          ▼
    ① h = X @ W1 + b1           ← (batch, 784) @ (784, 256) → (batch, 256)
          │                        这步把 784 个像素「编码」成 256 个特征
          ▼
    ② h = relu(h)               ← 砍掉负数，引入非线性（关键！）
          │                        没有这步，两层 Linear = 一层 Linear
          ▼
    ③ y = h @ W2 + b2           ← (batch, 256) @ (256, 10) → (batch, 10)
          │                        这步把 256 个特征「组合」成 10 个类别的分数
          ▼
    输出: (batch_size, 10)       ← 每个样本的 10 个 logits（原始分数）
    """
    # 拉平图片：从 (batch, 1, 28, 28) → (batch, 784)
    X = X.reshape(X.shape[0], -1)

    W1, b1, W2, b2 = params

    h = X @ W1 + b1         # ① 隐藏层线性变换
    h = relu(h)             # ② ReLU 激活（砍掉负数）
    y = h @ W2 + b2         # ③ 输出层线性变换

    return y


# ======================== 4. 交叉熵损失 ========================

def cross_entropy(y_pred, y_true):
    """
    交叉熵损失：-log(p_{正确答案})
    y_pred:  (batch, 10)  ← 模型输出的 logits（未经过 softmax）
    y_true:  (batch,)     ← 整数标签，比如 3 表示「裙子」

    注意：这里用 F.cross_entropy 的话内部自动做 softmax，
          但手搓就是为了看过程，所以手动 softmax 再算交叉熵。
    """
    # Step 1: softmax（把 logits 变概率）
    #   exp(x_i) / Σexp(x_j)
    #   指数放大差距 + 归一化，让结果变成概率分布（和为 1）
    exp_pred = torch.exp(y_pred)                           # (batch, 10)
    probs = exp_pred / exp_pred.sum(dim=1, keepdim=True)   # (batch, 10)

    # Step 2: 取出正确答案对应的概率
    #   y_true 是 [3, 5, 1, ...] 这种整数标签
    #   probs[range(N), y_true] 取出每行第 y_true 列的值
    batch_size = y_pred.shape[0]
    p_true = probs[range(batch_size), y_true]              # (batch,)

    # Step 3: 交叉熵 = -log(正确类的概率)
    #   概率越接近 1，loss 越接近 0
    #   概率越接近 0，loss → +∞
    loss = -torch.log(p_true)

    return loss.mean()  # 返回一批数据的平均损失


# ======================== 5. 评估函数 ========================

def evaluate_accuracy(loader, params):
    """计算模型在数据集上的准确率"""
    correct = 0
    total = 0
    for X, y in loader:
        y_pred = mlp_forward(X, params)          # (batch, 10)
        predicted = y_pred.argmax(dim=1)          # 取分数最高的类
        correct += (predicted == y).sum().item()
        total += y.shape[0]
    return correct / total


# ======================== 6. 训练循环 ========================

print("=" * 55)
print("开始训练 MLP（从零实现）")
print(f"  隐藏层大小: {num_hiddens}")
print(f"  学习率: {lr}")
print(f"  批次大小: {batch_size}")
print(f"  轮数: {num_epochs}")
print("=" * 55)

for epoch in range(num_epochs):
    total_loss = 0.0
    num_batches = 0

    for X, y in train_loader:
        # 前向：计算预测
        y_pred = mlp_forward(X, params)           # (batch, 10)

        # 算损失
        loss = cross_entropy(y_pred, y)           # 标量

        # 反向传播：计算梯度
        loss.backward()

        # SGD 更新参数（手动实现，不用优化器）
        with torch.no_grad():
            for param in params:
                param -= lr * param.grad          # w = w - lr * grad
                param.grad.zero_()                # 清空梯度，下一轮重新算

        total_loss += loss.item()
        num_batches += 1

    # 每轮结束评估
    train_acc = evaluate_accuracy(train_loader, params)
    test_acc = evaluate_accuracy(test_loader, params)

    avg_loss = total_loss / num_batches
    print(f"Epoch {epoch+1:2d}/{num_epochs} | "
          f"Loss: {avg_loss:.4f} | "
          f"Train Acc: {train_acc*100:.2f}% | "
          f"Test Acc: {test_acc*100:.2f}%")


# ======================== 7. 看几个预测结果 ========================

print("\n" + "=" * 55)
print("测试集预测示例")
print("=" * 55)

# 取一批测试数据
X_sample, y_sample = next(iter(test_loader))
with torch.no_grad():
    y_pred = mlp_forward(X_sample, params)
    predicted = y_pred.argmax(dim=1)

# 显示前 10 个结果
for i in range(10):
    true_name = class_names[y_sample[i]]
    pred_name = class_names[predicted[i]]
    mark = "✓" if y_sample[i] == predicted[i] else "✗"
    print(f"  {mark} 真实: {true_name:4s} | 预测: {pred_name:4s}")


# ======================== 8. 可视化（可选） ========================

try:
    # 画第一层的前几个权重，看看它学了什么特征
    fig, axes = plt.subplots(2, 5, figsize=(10, 4))
    W1 = params[0].detach()
    for i in range(10):
        row, col = i // 5, i % 5
        # 每个权重列 reshape 回 28×28 就是一张「特征图」
        weight_img = W1[:, i].reshape(28, 28)
        axes[row, col].imshow(weight_img, cmap='gray')
        axes[row, col].axis('off')
        axes[row, col].set_title(f'Neuron {i}')
    plt.suptitle('隐藏层前 10 个神经元的权重（可解释为学到的特征模板）')
    plt.savefig('mlp_weights_viz.png')
    print("\n✅ 权重可视化已保存: mlp_weights_viz.png")
except Exception as e:
    print(f"\n(可视化跳过: {e})")


print("\n" + "=" * 55)
print("训练完成！")
print("=" * 55)
print(f"""
🎯 一句话记住 MLP：

   h = max(0, X@W1 + b1)      ← 隐藏层：提取特征
   y = h@W2 + b2               ← 输出层：组合特征做决策

   比线性回归多了一行代码，但能学到的边界从直线→任意形状。
""")


# ======================== 术语对照表 ========================
"""
术语对照表（从零实现视角）：
┌─────────────────┬────────────────────────────────────┐
│   代码里的名字   │              什么意思               │
├─────────────────┼────────────────────────────────────┤
│  num_hiddens    │ 隐藏层神经元数量（模型的「宽度」）     │
│  W1, b1         │ 第一层权重和偏置（输入→隐藏层）      │
│  W2, b2         │ 第二层权重和偏置（隐藏层→输出层）    │
│  relu(h)        │ 激活函数，砍掉负数引入非线性          │
│  logits          │ 输出层的原始分数（softmax 前的值）   │
│  cross_entropy  │ 分类损失，惩罚「正确答案预测不够高」   │
│  argmax(dim=1)  │ 取最大值的索引，即最终预测的类别      │
└─────────────────┴────────────────────────────────────┘
"""
