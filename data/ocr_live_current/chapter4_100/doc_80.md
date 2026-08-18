所以 $ \frac{1}{24}\cdot\left(\frac{3}{4}\right)^{3k-3}+\frac{1}{3}\cdot\left(\frac{3}{4}\right)^{k-1}-\frac{1}{2}\cdot\left(\frac{3}{4}\right)^k\leq0 $，故 $ \frac{1}{24}\cdot\left(\frac{3}{4}\right)^{3k-3}+\frac{1}{3}\cdot\left(\frac{3}{4}\right)^{k-1}\leq\frac{1}{2}\cdot\left(\frac{3}{4}\right)^k $，

结合②可得 $ a_{k+1}\leq\frac{1}{2}\cdot\left(\frac{3}{4}\right)^k $，综上所述， $ \frac{1}{2}\cdot\left(\frac{2}{3}\right)^k\leq a_{k+1}\leq\frac{1}{2}\cdot\left(\frac{3}{4}\right)^k $，即当 $ n=k+1 $时结论也成立；

由(i)(ii)结合数学归纳法原理可知对任意的 $ n\in\mathbb{N}^* $，都有 $ \frac{1}{2}\cdot\left(\frac{2}{3}\right)^{n-1}\leq a_n\leq\frac{1}{2}\cdot\left(\frac{3}{4}\right)^{n-1} $。

证法2：（前面过程同证法1，得到不等式①后，要证当$n=k+1$时结论也成立，即证$\frac{1}{2}\cdot\left(\frac{2}{3}\right)^k\leq a_{k+1}\leq\frac{1}{2}\cdot\left(\frac{3}{4}\right)^k$也成立，注意到递推公式$a_{k+1}=\frac{1}{3}a_k^3+\frac{2}{3}a_k$中$\frac{1}{3}a_k^3$这部分较复杂，故也可尝试将其放缩掉）

由①可知$a_k\geq\frac{1}{2}\cdot\left(\frac{2}{3}\right)^{k-1}$，所以$a_{k+1}=\frac{1}{3}a_k^3+\frac{2}{3}a_k\geq\frac{2}{3}a_k\geq\frac{2}{3}\times\frac{1}{2}\cdot\left(\frac{2}{3}\right)^{k-1}=\frac{1}{2}\cdot\left(\frac{2}{3}\right)^k$，

由①可知$a_k\leq\frac{1}{2}\cdot\left(\frac{3}{4}\right)^{k-1}$，又因为$k\geq1$，所以$\left(\frac{3}{4}\right)^{k-1}\leq1$，故$a_k\leq\frac{1}{2}$，

所以$a_{k+1}=\frac{1}{3}a_k^3+\frac{2}{3}a_k=\frac{1}{3}a_k^2\cdot a_k+\frac{2}{3}a_k\leq\frac{1}{3}\times\left(\frac{1}{2}\right)^2a_k+\frac{2}{3}a_k=\frac{3}{4}a_k\leq\frac{3}{4}\times\frac{1}{2}\cdot\left(\frac{3}{4}\right)^{k-1}=\frac{1}{2}\cdot\left(\frac{3}{4}\right)^k$，

综上所述，$\frac{1}{2}\cdot\left(\frac{2}{3}\right)^k\leq a_{k+1}\leq\frac{1}{2}\cdot\left(\frac{3}{4}\right)^k$，接下来同证法1.

## 类型Ⅲ：用数学归纳法证明整除有关的结论

【例 3】用数学归纳法证明：对任意的正整数 n，数  $ A_{n}=5^{n}+2\times3^{n-1}+1 $ 都能被 8 整除.

证明：(i)当 $ n=1 $时， $ A_{1}=5^{1}+2\times3^{1-1}+1=8 $，所以 $ A_{1} $能被8整除，结论成立；

(ii) 假设当  $ n = k (k \geq 1) $ 时，结论成立，即  $ A_k = 5^k + 2 \times 3^{k-1} + 1 $ 能被 8 整除，

（如何证明当 $n=k+1$ 时结论也成立？只需证 $A_{k+1}=5^{k+1}+2\times3^k+1$ 能被 8 整除，为了运用归纳假设，考虑将 $A_{k+1}$ 凑出 $A_k=5^k+2\times3^{k-1}+1$ 这一结构）

$A_{k+1}=5^{k+1}+2\times3^k+1=5\times5^k+2\times3\times3^{k-1}+1=4\times5^k+5^k+4\times3^{k-1}+2\times3^{k-1}+1$

$=4\times5^k+4\times3^{k-1}+5^k+2\times3^{k-1}+1=4(5^k+3^{k-1})+A_k$，

因为 $ 5^k $和 $ 3^{k-1} $都是奇数，所以 $ 5^k + 3^{k-1} $为偶数，故 $ 4(5^k + 3^{k-1}) $必为8的倍数，它能被8整除，又因为 $ A_k $也能被8整除，所以 $ 4(5^k + 3^{k-1}) + A_k $能被8整除，即 $ A_{k+1} $能被8整除，故当 $ n = k + 1 $时，结论也成立；由(i)(ii)结合数学归纳法原理可知对任意的正整数 $ n $，数 $ A_n = 5^n + 2 \times 3^{n-1} + 1 $都能被8整除。

【反思】用数学归纳法证明整除问题，基本步骤还是分两步，但需注意，解决这类问题的核心是将 $ n=k+1 $时的数拆分成当n=k时的数和余下部分，从而把问题转化为证明余下部分满足整除.

## 强化训练

考虑到本节涉及的题型都有一定的综合性和难度，故不设 A 组题；且由于本节是选学内容，要求不高，所以也不设 C 组题，只设计了 B 组题.

## B组 强化能力

### 1. (2025 · 全国模拟)

用数学归纳法证明： $ (\cos\theta + i\sin\theta)^n = \cos n\theta + i\sin n\theta $，其中 $ i $为虚数单位， $ n \in \mathbb{N}^* $。