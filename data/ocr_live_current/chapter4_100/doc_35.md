关于 n 的“一次函数”；若 B=0 （即  $ a_{1}=0 $），则  $ S_{n} $ 是关于 n 的“常函数”。无论哪种情况，点  $ (n,S_{n}) $ 都是直线 y=Bx 上一系列孤立的点。

### 2. 前 n 项和  $ S_{n} $ 的最值

设等差数列 $ \{a_{n}\} $的首项为 $ a_{1} $，公差为d，则：


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>条件</td><td style='text-align: center; word-wrap: break-word;'>$ S_n $ 的最值</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>d &lt; 0</td><td style='text-align: center; word-wrap: break-word;'>数列  $ \{a_n\} $ 为递减数列，此时  $ S_n $ 有最大值，无最小值</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>d &gt; 0</td><td style='text-align: center; word-wrap: break-word;'>数列  $ \{a_n\} $ 为递增数列，此时  $ S_n $ 有最小值，无最大值</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>d = 0</td><td style='text-align: center; word-wrap: break-word;'>数列  $ \{a_n\} $ 为常数列，若  $ a_1 &lt; 0 $，则  $ S_n $ 有最大值  $ a_1 $，无最小值；若  $ a_1 &gt; 0 $，则  $ S_n $ 有最小值  $ a_1 $，无最大值.</td></tr></table>

## 知识点 3：等差数列的前 n 项和的性质

1. 设等差数列 $ \{a_{n}\} $的前n项和为 $ S_{n} $，则

 $$ S_{2n-1}=\frac{(2n-1)(a_{1}+a_{2n-1})}{2}=\frac{(2n-1)\cdot2a_{n}}{2}=(2n-1)a_{n}, $$ 

 $$ S_{2n}=\frac{2n(a_{1}+a_{2n})}{2}=n(a_{1}+a_{2n})=n(a_{n}+a_{n+1}). $$ 

2. 片段和性质：等差数列 $ \{a_{n}\} $中，公差为d，前k项的和为 $ S_{k} $，则 $ S_{k} $， $ S_{2k}-S_{k} $， $ S_{3k}-S_{2k} $， $ \cdots $， $ S_{mk}-S_{(m-1)k} $， $ \cdots $构成公差为 $ k^{2}d $的等差数列.

3. 由  $ S_{n}=na_{1}+\frac{n(n-1)}{2}d $ 可知， $ \frac{S_{n}}{n}=a_{1}+\frac{n-1}{2}d=\frac{d}{2}n+a_{1}-\frac{d}{2} $，所以  $ \left\{\frac{S_{n}}{n}\right\} $ 是等差数列，首项为  $ a_{1} $，公差为  $ \frac{d}{2} $.

## 知识点2

【例3】设$\{a_n\}$是等差数列，且$a_1=3$，公差$d=-2$，则数列$\{a_n\}$的前$n$项和$S_n$的最大值是___。

解法1：由题意，$S_n=na_1+\frac{n(n-1)}{2}d=3n+\frac{n(n-1)}{2}\times(-2)=-n^2+4n=-(n-2)^2+4$，当$n=2$时，$S_n$取最大值，且最大值为4。

解法2：研究等差数列前$n$项和的最值，也可从项的正负上来考虑，由题意，$a_n=a_1+(n-1)d=3+(n-1)\cdot(-2)=5-2n$，所以$a_1>0$，$a_2>0$，当$n\geq3$时，$a_n<0$，所以$S_n$的最大值为$S_2=a_1+a_2=3+1=4$。

答案：4

## 知识点3

【例 4】等差数列 $\{a_n\}$ 的前 $n$ 项和为 $S_n$，若 $S_2 = 4$，$S_4 = 16$，则 $S_6 = $___。

解析：观察发现已知和所求涉及的下标都是 $2$ 的倍数，联想到利用片段和性质求 $S_6$，因为 $\{a_n\}$ 是等差数列，所以由片段和性质，$S_2$，$S_4 - S_2$，$S_6 - S_4$ 成等差数列，所以 $2(S_4 - S_2) = S_2 + (S_6 - S_4)$，即 $2 \times (16 - 4) = 4 + S_6 - 16$，解得：$S_6 = 36$。

答案：36

## 本节核心题型

关于等差数列的前 $n$ 项和，首先要学会最基本的代公式计算，所以我们设计了类型Ⅰ这组题来给大家强化基础；其次，前 $n$ 项和的有关性质也是高频考点，于是我们又设计了类型Ⅱ这组题来讲解与等差数列前 $n$ 项和有关的几个性质的应用；而在类型Ⅲ中，我们将重点分析与等差数列前 $n$ 项和最值有关的问题的处理方法；最后，我们通过类型Ⅳ来给大家举一个等差数列前 $n$ 项和公式在实际问题中的应用的例子。

类型 I：求等差数列的前 n 项和