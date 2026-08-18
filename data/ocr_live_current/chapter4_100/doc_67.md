该性质可知  $ S_3 $， $ S_6 - S_3 $， $ S_9 - S_6 $ 构成公比为  $ q^3 $ 的等比数列，由此能与公比  $ q $ 联系起来，故尝试将所给等式调节为关于  $ S_3 $， $ S_6 - S_3 $， $ S_9 - S_6 $ 的式子，由  $ S_9 + 8S_3 = 9S_6 $ 可得  $ S_9 - S_6 = 8(S_6 - S_3) $，所以  $ \frac{S_9 - S_6}{S_6 - S_3} = 8 $，

由片段和性质， $ S_3 $， $ S_6 - S_3 $， $ S_9 - S_6 $ 成等比数列，且公比为  $ q^3 $，所以  $ \frac{S_9 - S_6}{S_6 - S_3} = q^3 $，故  $ q^3 = 8 $，解得： $ q = 2 $。

答案：2

【变式 3】已知数列 $\{a_n\}$ 的前 $n$ 项和，前 $2n$ 项和，前 $3n$ 项和分别为 $P$，$Q$，$R$，则 “ $\{a_n\}$ 为等比数列” 的一个必要条件为（ ）

A. $(P+Q)-R=Q^2$

B. $P^2+Q^2=P(Q+R)$

C. $P+Q=R$

D. $Q^2=PR$

解析：看到题干表述的“前 $n$ 项和，前 $2n$ 项和，前 $3n$ 项和”自然联想到片段和性质，于是可根据片段和性质列出对应的式子，再观察哪些选项可化为该式子，因为 $\{a_n\}$ 是等比数列，所以 $P$，$Q-P$，$R-Q$ 成等比数列，或它们都为 $0$，从而 $(Q-P)^2 = P(R-Q)$，整理得：$P^2 + Q^2 = P(Q+R)$，故 B 项正确。

答案：B

## 类型Ⅲ：等比数列前 n 项和与通项的关系

【例 5】设  $ S_n $ 为数列  $ \{a_n\} $ 的前  $ n $ 项和，满足  $ S_n = 1 - a_n (n \in \mathbb{N}^* $。

（1）求数列  $ \{a_n\} $ 的通项公式；

（2）记  $ T_n = S_1^2 + S_2^2 + \cdots + S_n^2 $，求  $ T_n $。

解：（1）（条件给出  $ a_{n} $ 与  $ S_{n} $ 混搭的关系式，要求的是  $ a_{n} $，考虑退 n 相减，消去  $ S_{n} $）

因为  $ S_{n}=1-a_{n} $，所以当  $ n\geq2 $ 时， $ S_{n-1}=1-a_{n-1} $，两式相减得  $ S_{n}-S_{n-1}=1-a_{n}-(1-a_{n-1}) $，

从而  $ a_{n} = -a_{n} + a_{n-1} $，故  $ a_{n} = \frac{1}{2}a_{n-1} $ ①，

（由此求  $ a_n $ 还差首项  $ a_1 $，可在  $ S_n = 1 - a_n $ 中取  $ n = 1 $ 来建立关于  $ a_1 $ 的方程并求解  $ a_1 $）

在  $ S_n = 1 - a_n $ 中取  $ n = 1 $ 得  $ S_1 = 1 - a_1 $，又  $ S_1 = a_1 $，所以  $ a_1 = 1 - a_1 $，故  $ a_1 = \frac{1}{2} $，结合①得  $ \{a_n\} $ 的所有项都不为 0，

所以  $ \frac{a_n}{a_{n-1}} = \frac{1}{2} $，从而数列  $ \{a_n\} $ 是首项和公比均为  $ \frac{1}{2} $ 的等比数列，故  $ a_n = \frac{1}{2} \times \left(\frac{1}{2}\right)^{n-1} = \left(\frac{1}{2}\right)^n $。

（2）由（1）可得  $ S_n = 1 - a_n = 1 - \left(\frac{1}{2}\right)^n $，所以  $ S_n^2 = \left[1 - \left(\frac{1}{2}\right)^n\right]^2 = 1 - 2 \times \left(\frac{1}{2}\right)^n + \left(\frac{1}{2}\right)^{2n} = 1 - \left(\frac{1}{2}\right)^{n-1} + \left(\frac{1}{4}\right)^n $，

（ $ S_n^2 $ 有 3 项，怎样求和？这种情况可各自单独求和，再相加或相减，下面我们把过程写详细一些，大家就清楚

原理了）故  $ T_n = S_1^2 + S_2^2 + \cdots + S_n^2 = 1 - \left(\frac{1}{2}\right)^0 + \left(\frac{1}{4}\right)^1 + 1 - \left(\frac{1}{2}\right)^1 + \left(\frac{1}{4}\right)^2 + \cdots + 1 - \left(\frac{1}{2}\right)^{n-1} + \left(\frac{1}{4}\right)^n $

 $ = (1 + 1 + \cdots + 1)(n \text{个}1) - \left[\left(\frac{1}{2}\right)^0 + \left(\frac{1}{2}\right)^1 + \cdots + \left(\frac{1}{2}\right)^{n-1}\right] + \left[\left(\frac{1}{4}\right)^1 + \left(\frac{1}{4}\right)^2 + \cdots + \left(\frac{1}{4}\right)^n\right] = n - \frac{1 - \left(\frac{1}{2}\right)^n}{1 - \frac{1}{2}} + \frac{\frac{1}{4} \left[1 - \left(\frac{1}{4}\right)^n\right]}{1 - \frac{1}{4}} = n - 2 + 2 \times \left(\frac{1}{2}\right)^n + \frac{1}{3} - \frac{1}{3} \times \left(\frac{1}{4}\right)^n = \frac{3n - 5}{3} + \left(\frac{1}{2}\right)^{n-1} - \frac{1}{3} \times \left(\frac{1}{4}\right)^n $。