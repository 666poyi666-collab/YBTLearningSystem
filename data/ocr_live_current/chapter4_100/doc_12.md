求解，找到最大项是谁）设数列 $\{a_n\}$ 的最大项为 $a_k$，则 $\begin{cases} a_k \geq a_{k-1} \\ a_k \geq a_{k+1} \end{cases}$，即 $\begin{cases} \dfrac{2k-5}{2^k} \geq \dfrac{2k-7}{2^{k-1}} \\ \dfrac{2k-5}{2^k} \geq \dfrac{2k-3}{2^{k+1}} \end{cases}$，

化简得：$\begin{cases} 2k-5 \geq 2(2k-7) \\ 2(2k-5) \geq 2k-3 \end{cases}$，解得：$\dfrac{7}{2} \leq k \leq \dfrac{9}{2}$，结合 $k \in \mathbb{N}^*$ 可得 $k$ 只能取 4，

所以数列 $\{a_n\}$ 的最大项为 $a_4 = \dfrac{2 \times 4 - 5}{2^4} = \dfrac{3}{16}$。

【反思】求数列 $\{a_n\}$ 的最大项时，除了分析单调性的方法外，也可直接由 $\begin{cases} a_k \geq a_{k-1} \\ a_k \geq a_{k+1} \end{cases}$ 求解 $k$ 的范围，结合 $k$ 为正整数得到 $k$ 的值。本题的 $k$ 只有 1 个值，所以能直接得到最大项，若由 $\begin{cases} a_k \geq a_{k-1} \\ a_k \geq a_{k+1} \end{cases}$ 求出的 $k$ 有多个取值，则还需计算并比较对应的这些项谁最大，才能求出 $\{a_n\}$ 的最大项。

## 类型Ⅶ：两类数列求前 n 项和问题

【例 17】记数列 $\{a_n\}$ 的前 $n$ 项和为 $S_n$，且 $a_n = \cos \frac{n\pi}{4}$，则 $S_{2025} =$ ___。

解析：可以想象， $ y = \cos \frac{\pi}{4} x $ 的周期  $ T = \frac{2\pi}{\frac{\pi}{4}} = 8 $，故猜想  $ \{a_n\} $ 是周期为 8 的周期数列，下面先给出证明对任意的  $ n \in \mathbf{N}^* $， $ a_{n+8} = \cos \frac{(n+8)\pi}{4} = \cos \left( \frac{n\pi}{4} + 2\pi \right) = \cos \frac{n\pi}{4} = a_n $，所以  $ \{a_n\} $ 是周期为 8 的周期数列，要求  $ S_{2025} $，考虑按周期分组，可先求  $ a_1 + a_2 + \cdots + a_8 $，再看  $ \{a_n\} $ 的前 2025 项有几个周期，余下几项， $ a_1 = \cos \frac{\pi}{4} = \frac{\sqrt{2}}{2} $， $ a_2 = \cos \frac{2\pi}{4} = 0 $， $ a_3 = \cos \frac{3\pi}{4} = -\frac{\sqrt{2}}{2} $， $ a_4 = \cos \frac{4\pi}{4} = -1 $， $ a_5 = \cos \frac{5\pi}{4} = -\frac{\sqrt{2}}{2} $， $ a_6 = \cos \frac{6\pi}{4} = 0 $， $ a_7 = \cos \frac{7\pi}{4} = \frac{\sqrt{2}}{2} $， $ a_8 = \cos \frac{8\pi}{4} = 1 $，所以  $ a_1 + a_2 + \cdots + a_8 = \frac{\sqrt{2}}{2} + 0 - \frac{\sqrt{2}}{2} - 1 - \frac{\sqrt{2}}{2} + 0 + \frac{\sqrt{2}}{2} + 1 = 0 $，

又因为  $ 2025 = 253 \times 8 + 1 $，所以  $ S_{2025} = 253 (a_1 + a_2 + \cdots + a_8) + a_{2025} = a_{2025} = a_1 = \frac{\sqrt{2}}{2} $

答案： $ \frac{\sqrt{2}}{2} $

【反思】当数列$\{a_n\}$具有周期性时，要求$\{a_n\}$的前$M$项和$S_M$，常抓住每个周期内求和的结果相同来计算。一般将前$M$项按周期分组，先求一个周期内的和，再看前$M$项有几个周期，余下几项。

【例 18】在数列 $\{a_n\}$ 中，$a_1 = 2$，$n(a_{n+1} - a_n) = a_n + 1$，$n \in \mathbb{N}^*$，若对任意的 $a \in [-2,2]$，$n \in \mathbb{N}^*$，不等式 $\frac{a_{n+1}}{n+1} < 2t^2 + at -1$ 恒成立，则实数 $t$ 的取值范围为（ ）

A. $(-\infty,-2) \cup (1,+\infty)$  

B. $(-\infty,-2] \cup [2,+\infty)$  

C. $(-\infty,-1] \cup [2,+\infty)$  

D. $[-2,2]$

解析：注意到所给不等式 $ \frac{a_{n+1}}{n+1}<2t^{2}+at-1 $的右边不含n，故可先分析当n变化时，左边的 $ \frac{a_{n+1}}{n+1} $的取值情况，