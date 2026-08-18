 $ -\frac{1}{2}\ln n = \frac{1}{2}\ln \frac{n+1}{n} $，于是只需证  $ \frac{1}{2n+1} < \frac{1}{2}\ln \frac{n+1}{n} $，怎么证此不等式成立？可考虑联系第（1）问处理）

由（1）可得当  $ a=2 $ 时， $ f(x)=(x+1)\ln x - 2x + 2 $ 在  $ (0, +\infty) $ 上单调递增，

所以当  $ x > 1 $ 时， $ f(x) > f(1) $，从而  $ (x+1)\ln x - 2x + 2 > 0 $，故  $ \ln x > \frac{2x - 2}{x+1} $，

取  $ x = \frac{k+1}{k} (k \in \mathbb{N}^* $) 可得  $ \ln \frac{k+1}{k} > \frac{2 \cdot \frac{k+1}{k} - 2}{\frac{k+1}{k} + 1} = \frac{2}{2k+1} $，所以  $ \frac{1}{2k+1} < \frac{1}{2}\ln \frac{k+1}{k} $，

依次取  $ k=1,2,3,\cdots, n $ 得  $ \frac{1}{3} < \frac{1}{2}\ln \frac{2}{1} $， $ \frac{1}{5} < \frac{1}{2}\ln \frac{3}{2} $， $ \frac{1}{7} < \frac{1}{2}\ln \frac{4}{3} $， $ \cdots $， $ \frac{1}{2n+1} < \frac{1}{2}\ln \frac{n+1}{n} $，

将以上各式相加得  $ \frac{1}{3} + \frac{1}{5} + \frac{1}{7} + \cdots + \frac{1}{2n+1} < \frac{1}{2}\ln \frac{2}{1} + \frac{1}{2}\ln \frac{3}{2} + \frac{1}{2}\ln \frac{4}{3} + \cdots + \frac{1}{2}\ln \frac{n+1}{n} = \frac{1}{2}\ln\left(\frac{2}{1} \times \frac{3}{2} \times \frac{4}{3} \times \cdots \times \frac{n+1}{n}\right) = \frac{1}{2}\ln(n+1) $。

【反思】证明  $ \frac{1}{3} + \frac{1}{5} + \frac{1}{7} + \cdots + \frac{1}{2n+1} < \frac{1}{2}\ln(n+1) $ 这种左侧无法求出和的求和不等式时，可考虑将右边也化为求和结构，再通过证明左右两边求和通项的大小关系，来证明该不等式成立。

## 强化训练

考虑到本节涉及的题型都有一定的难度，故不设 A 组题，只设计了 B 组和 C 组题.

## B组 强化能力

1. (2025 · 陕西模拟)

已知函数  $ f(x) = x^2 - ax + \ln x $， $ a \in \mathbb{R} $。高中数学一本通

（1）若  $ f(x) $ 是单调函数，求 a 的最大值；

（2）若  $ f(x)>0 $ 在  $ (1,+\infty) $ 上恒成立，求 a 的取值范围.

### 2. （2025·湖南一模）

已知函数  $ f(x) = \ln x + ax^2 $， $ g(x) = e^x - ax^2 $， $ a \in \mathbb{R} $。

（1）讨论  $ f(x) $ 的单调性；

（2）若  $ g(2x) \geq 4x^{2}\left[f(x) + \frac{1}{x} - ax^{2}\right] $ 恒成立，求 a 的取值范围.