# 微专题2：数列拔高题型

习题：P1

## 内容提要

本节收录一些数列综合大题，包括数列的添项和去项问题、奇偶数列求和、奇偶数列求通项、放缩法证明数列求和不等式四个类型。本节难度较大，是数列板块的拔高内容。

## 典型例题

## 类型 I：数列中的添项和去项问题

【例 1】已知数列  $ \{a_{n}\} $ 的前 n 项和为  $ S_{n} $， $ a_{1}=2 $，且  $ a_{n+1}=S_{n}+2 $。

（1）求数列 $ \{a_{n}\} $的通项公式；

（2）在  $ a_n $ 与  $ a_{n+1} $ 之间插入  $ n $ 个数，使这  $ n+2 $ 个数组成一个公差为  $ d_n $ 的等差数列，设  $ T_n = \frac{1}{d_1} + \frac{1}{d_2} + \frac{1}{d_3} + \cdots + \frac{1}{d_n} $，求  $ T_n $。

解：（1）解法1：（条件给出  $ a_{n+1} $ 与  $ S_n $ 混搭的关系式，要求的是  $ a_n $，故可考虑退 n 相减，消去  $ S_n $）

因为  $ a_{n+1} = S_n + 2 $，所以当  $ n \geq 2 $ 时， $ a_n = S_{n-1} + 2 $，两式相减得  $ a_{n+1} - a_n = S_n + 2 - S_{n-1} - 2 = a_n $，所以  $ a_{n+1} = 2a_n $，（上式成立的条件是  $ n \geq 2 $，那么当  $ n=1 $ 时它是否成立呢？我们单独来看看）

在  $ a_{n+1} = S_n + 2 $ 中令  $ n=1 $ 得  $ a_2 = S_1 + 2 = a_1 + 2 = 4 $，所以  $ a_2 = 2a_1 $，从而  $ a_{n+1} = 2a_n $ 对任意的  $ n \in \mathbb{N}^* $ 都成立，故  $ \{a_n\} $ 是首项为 2，公比也为 2 的等比数列，所以  $ a_n = 2 \times 2^{n-1} = 2^n $。

解法2：（注意到 $ a_{n+1}=S_{n+1}-S_n $，故也可考虑用它替换题干等式中的 $ a_{n+1} $，先求 $ S_n $，再用 $ S_n $求 $ a_n $）

将 $ a_{n+1}=S_{n+1}-S_n $代入 $ a_{n+1}=S_n+2 $得 $ S_{n+1}-S_n=S_n+2 $，所以 $ S_{n+1}=2S_n+2 $①，

（由上式的结构联想到可用待定系数法构造等比数列求 $ S_n $，可先假设 $ S_{n+1}+\lambda=2(S_n+\lambda) $，则 $ S_{n+1}=2S_n+\lambda $，与

式①对比得 $ \lambda=2 $，构造的方法就有了）由①可得 $ S_{n+1}+2=2(S_n+2) $，又 $ S_1+2=a_1+2=4 $，

所以 $ \{S_n+2\} $是首项为4，公比为2的等比数列，从而 $ S_n+2=4\times2^{n-1}=2^{n+1} $，故 $ S_n=2^{n+1}-2 $，

所以当 $ n\geq2 $时， $ a_n=S_n-S_{n-1}=2^{n+1}-2-(2^n-2)=2^{n+1}-2^n=2\times2^n-2^n=2^n $，

又因为 $ a_1=2 $也满足上式，所以对任意的 $ n\in\mathbb{N}^* $，都有 $ a_n=2^n $。

（2）（可以想象，在  $ a_n $ 和  $ a_{n+1} $ 之间插入  $ n $ 个数，使它们构成公差为  $ d_n $ 的等差数列，则  $ d_n = \frac{a_{n+1} - a_n}{n+2-1} $，已有  $ a_n $，故由此可得到  $ d_n $）由题意， $ d_n = \frac{a_{n+1} - a_n}{n+2-1} = \frac{2^{n+1} - 2^n}{n+1} = \frac{2^n}{n+1} $，所以  $ \frac{1}{d_n} = \frac{n+1}{2^n} = (n+1) \cdot \left(\frac{1}{2}\right)^n $，

（这是“等差×等比”结构，可用错位相减法求前n项和）

 $$ \begin{aligned}& 所以 \left\{\begin{aligned}&T_{n}=2\times\left(\frac{1}{2}\right)^{1}+3\times\left(\frac{1}{2}\right)^{2}+4\times\left(\frac{1}{2}\right)^{3}+\cdots+(n+1)\cdot\left(\frac{1}{2}\right)^{n}\textcircled{2}\\ &\frac{1}{2}T_{n}=\quad2\times\left(\frac{1}{2}\right)^{2}+3\times\left(\frac{1}{2}\right)^{3}+4\times\left(\frac{1}{2}\right)^{4}+\cdots+n\cdot\left(\frac{1}{2}\right)^{n}+(n+1)\cdot\left(\frac{1}{2}\right)^{n+1}\textcircled{3}\end{aligned}\right.,\end{aligned} $$ 

 $$  \textcircled{2} - \textcircled{3}得 \frac{1}{2}T_{n}=2\times\left(\frac{1}{2}\right)^{1}+\left(\frac{1}{2}\right)^{2}+\left(\frac{1}{2}\right)^{3}+\cdots+\left(\frac{1}{2}\right)^{n}-(n+1)\cdot\left(\frac{1}{2}\right)^{n+1}=1+\frac{\left(\frac{1}{2}\right)^{2}\cdot\left[1-\left(\frac{1}{2}\right)^{n-1}\right]}{1-\frac{1}{2}}-(n+1)\cdot\left(\frac{1}{2}\right)^{n+1} $$ 