# NumPy Cheat Sheet

> Python 数据分析基础知识点速查

---

## 1. 布尔数组索引（Boolean Array Indexing）

```python
import numpy as np

a = np.array([1, 2, 3, 4, 5, 6])

# 生成布尔数组
bool_mask = a > 3          # array([False, False, False,  True,  True,  True])

# 用布尔数组过滤 — 返回一维数组，只含 True 对应位置的元素
result = a[bool_mask]      # array([4, 5, 6])

# 等价写法（inline）
a[a > 3]                   # array([4, 5, 6])
a[(a > 2) & (a < 6)]       # array([3, 4, 5])   — 注意用 & 而非 and
```

**要点：**
- 返回一维数组（非矩阵）
- 条件表达式需加括号
- 多条件用 `&`（且）和 `|`（或），不能用 Python 关键字 `and`/`or`

---

## 2. 花式索引（Fancy Indexing）

```python
a = np.array([10, 20, 30, 40, 50])

# 用整数位置数组取元素 — 按位置而非条件
idx = [0, 2, 4]
a[idx]                     # array([10, 30, 50])

# 二维数组的行选取
b = np.arange(12).reshape(3, 4)
rows = [0, 2]
b[rows]                    # 取第 0 行和第 2 行
b[:, [1, 3]]              # 取第 1 列和第 3 列
```

**要点：** Fancy indexing 返回的是视图的复制还是引用取决于索引类型。

---

## 3. `np.where` — 条件替换

```python
a = np.array([1, 2, 3, 4, 5])

# 基础用法：condition ? x : y（类 Excel IF）
np.where(a > 2, a, 0)     # array([0, 0, 3, 4, 5])

# 二维：按行列条件分别处理
b = np.arange(9).reshape(3, 3)
np.where(b > 4, b * 2, b) # 大于 4 的元素翻倍，其余不变
```

---

## 4. `np.any` / `np.all` — 聚合布尔

```python
a = np.array([True, False, True])

np.any(a)                  # True — 至少一个 True
np.all(a)                  # False — 不是全为 True

# 常用于条件检查
np.any(a > 3)             # 数组中是否存在 > 3 的元素
np.all(a > 0)             # 是否全为正
```

---

## 5. `axis` 参数 — 维度理解

```python
b = np.arange(12).reshape(3, 4)
# array([[ 0,  1,  2,  3],
#        [ 4,  5,  6,  7],
#        [ 8,  9, 10, 11]])

b.sum(axis=0)             # 按列求和 → array([12, 15, 18, 21])
b.sum(axis=1)             # 按行求和 → array([ 6, 22, 38])

b.mean(axis=0)            # 每列均值
b.max(axis=1)             # 每行最大值
```

**二维轴含义：** `axis=0` 是列方向（纵向），`axis=1` 是行方向（横向）。

---

## 6. 视图（View）vs 复制（Copy）

```python
a = np.array([1, 2, 3, 4, 5])

# 视图 — 共享内存，修改 a 会影响 b
b = a.reshape(5, 1)       # 除非用了 .reshape() 有时返回 copy
b[0, 0] = 99
print(a[0])               # 99（如果返回的是视图）

# 复制 — 完全独立
c = a.copy()
c[0] = 99
print(a[0])               # 1（不受影响）
```

**判断方法：**
```python
np.shares_memory(a, b)    # True = 视图，False = 复制
```

---

## 7. `np.concatenate` / `np.stack` — 合并数组

```python
a = np.array([1, 2])
b = np.array([3, 4])

np.concatenate([a, b])          # array([1, 2, 3, 4])
np.stack([a, b])                # 2D array: [[1, 2], [3, 4]]
np.hstack([a, b])               # 水平合并 → [1, 2, 3, 4]
np.vstack([a, b])               # 垂直合并 → [[1, 2], [3, 4]]
```

---

## 8. `np.unique` — 去重

```python
a = np.array([1, 2, 2, 3, 3, 3, 4])

np.unique(a)                    # array([1, 2, 3, 4])
np.unique(a, return_counts=True) # (array([1, 2, 3, 4]), array([1, 2, 3, 1]))
                               # 返回值和出现次数
```

---

## 9. `np.save` / `np.load` — 持久化

```python
# 保存单个数组
np.save('data.npy', array)

# 保存多个数组
np.savez('data.npz', a=arr1, b=arr2)

# 加载
arr = np.load('data.npy')
data = np.load('data.npz')
data['a']                       # 取出 arr1
data['b']                       # 取出 arr2
```

---

## 10. 常用统计函数

```python
a = np.array([1, 5, 3, 9, 7])

a.mean()                        # 均值
a.std()                         # 标准差
a.var()                         # 方差
a.min() / a.max()              # 最小/最大值
a.argmin() / a.argmax()        # 最小/最大值的索引位置
np.percentile(a, 25)           # 第25百分位数
np.median(a)                   # 中位数
np.corrcoef(a, b)             # 相关系数矩阵
```

---

## 11. `np.dot` / `@` — 矩阵乘法

```python
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

np.dot(A, B)                    # 2x2 矩阵乘法
A @ B                          # 等价写法（Python 3.5+）
```

---

## 12. Broadcasting（广播机制）

```python
# 小数组自动广播到大数组的形状
a = np.array([[1, 2, 3], [4, 5, 6]])    # shape (2, 3)
b = np.array([10, 20, 30])               # shape (3,) — 自动扩展成 (2, 3)
a + b                                    # [[11, 22, 33], [14, 25, 36]]
```

**广播规则：** 从右往左比较维度，相等或其一为 1 则兼容。

---

## 13. `np.isnan` / `np.isinf` — 缺失值和无穷检测

```python
a = np.array([1, np.nan, 3, np.inf])

np.isnan(a)                    # array([False,  True, False, False])
np.isinf(a)                    # array([False, False, False,  True])
np.isfinite(a)                 # array([ True, False,  True, False])

# 替换缺失值
a[np.isnan(a)] = 0
```

---

## 14. 结构化数组（Structured Array）

```python
dt = np.dtype([('ticker', 'U10'), ('score', 'f4'), ('shares', 'i4')])
arr = np.array([('NVDA', 0.85, 100), ('AMD', 0.72, 50)], dtype=dt)

arr['ticker']                  # array(['NVDA', 'AMD'], dtype='<U10')
arr['score']                   # array([0.85, 0.72], dtype='float32')
```

---

## 15. 常用配置

```python
# yfinance 等库通常需要设置 proxy
import os
os.environ["http_proxy"] = "http://127.0.0.1:7890"
os.environ["https_proxy"] = "http://127.0.0.1:7890"

# NumPy 显示设置
np.set_printoptions(precision=3, suppress=True, threshold=10, edgeitems=3)
```

---

## 快速参考

| 操作 | 代码 |
|------|------|
| 生成 0-1 均匀分布 | `np.random.rand(3, 4)` |
| 生成标准正态 | `np.random.randn(100)` |
| 生成整数数组 | `np.arange(0, 10, 2)` |
| 等差数组 | `np.linspace(0, 1, 5)` |
| 全 0 / 全 1 矩阵 | `np.zeros((3,4))`, `np.ones((2,3))` |
| 单位矩阵 | `np.eye(4)` |
| 对角矩阵 | `np.diag([1,2,3])` |
