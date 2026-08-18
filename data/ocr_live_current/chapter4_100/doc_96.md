所以 $ \frac{1}{a_1}+\frac{1}{a_2}+\frac{1}{a_3}+\cdots+\frac{1}{a_n}<\frac{1}{2}\left(1-\frac{1}{3}+\frac{1}{2}-\frac{1}{4}+\frac{1}{3}-\frac{1}{5}+\cdots+\frac{1}{n}-\frac{1}{n+2}\right) $

 $ =\frac{1}{2}\left[\left(1+\frac{1}{2}+\frac{1}{3}+\cdots+\frac{1}{n}\right)-\left(\frac{1}{3}+\frac{1}{4}+\cdots+\frac{1}{n}+\frac{1}{n+1}+\frac{1}{n+2}\right)\right]=\frac{1}{2}\left(1+\frac{1}{2}-\frac{1}{n+1}-\frac{1}{n+2}\right)=\frac{3}{4}-\frac{1}{2}\left(\frac{1}{n+1}+\frac{1}{n+2}\right) $,

因为 $ \frac{1}{2}\left(\frac{1}{n+1}+\frac{1}{n+2}\right)>0 $，所以 $ \frac{1}{a_1}+\frac{1}{a_2}+\frac{1}{a_3}+\cdots+\frac{1}{a_n}<\frac{3}{4}-\frac{1}{2}\left(\frac{1}{n+1}+\frac{1}{n+2}\right)<\frac{3}{4} $.

【反思】①通过丢项将不能求和的结构放缩成可以求和的结构是证明数列求和不等式常用的方法。本题丢项后放缩成了可通过裂项求和的结构，有时也会放缩成其它可求和的结构，比如下面的变式；②放缩的方向可能不唯一，需要尝试。例如本题若改为证明 $ \frac{1}{a_1}+\frac{1}{a_2}+\cdots+\frac{1}{a_n}<1 $，则可按 $ \frac{1}{a_n}=\frac{1}{(n+1)^2}<\frac{1}{n(n+1)}=\frac{1}{n}-\frac{1}{n+1} $放缩，进而得到 $ \frac{1}{a_1}+\frac{1}{a_2}+\cdots+\frac{1}{a_n}<1-\frac{1}{2}+\frac{1}{2}-\frac{1}{3}+\cdots+\frac{1}{n}-\frac{1}{n+1}=1-\frac{1}{n+1}<1 $。

【变式】已知对任意的  $ n \in \mathbb{N}^* $，数列  $ \{a_n\} $ 都满足  $ \frac{a_1 - 1}{2^1 + 1} + \frac{a_2 - 2}{2^2 + 1} + \cdots + \frac{a_n - n}{2^n + 1} = n + 1 $。

（1）求数列 $ \{a_{n}\} $的通项公式；

（2）求证： $ \frac{2}{a_{2}}+\frac{2}{a_{3}}+\cdots+\frac{2}{a_{n+1}}<1-\frac{1}{2^{n}} $

解：（1）（观察发现所给等式左侧是数列$\left\{\frac{a_n-n}{2^n+1}\right\}$的前$n$项和，已知前$n$项和，可直接退$n$相减，求出通项）记$b_n=\frac{a_n-n}{2^n+1}$，数列$\{b_n\}$的前$n$项和为$S_n$，则由题意，$S_n=n+1$，所以$b_1=S_1=2$，即$\frac{a_1-1}{2^1+1}=2$，故$a_1=7$，当$n\geq2$时，$b_n=S_n-S_{n-1}=n+1-n=1$，即$\frac{a_n-n}{2^n+1}=1$，所以$a_n=2^n+1+n$，故$a_n=\begin{cases}7,n=1\\2^n+1+n,n\geq2\end{cases}$。

（2）（可以想象， $ \frac{2}{a_{n+1}}=\frac{2}{2^{n+1}+1+n+1}=\frac{2}{2^{n+1}+n+2} $，所以 $ \left\{\frac{2}{a_{n+1}}\right\} $无法求和，考虑放缩成能求和的结构，如何放缩？观察发现，只要把分母的 $ n+2 $丢掉，化为 $ \frac{2}{2^{n+1}} $，就能求和了，故可按此尝试）

由（1）可得 $ \frac{2}{a_{n+1}}=\frac{2}{2^{n+1}+n+2}<\frac{2}{2^{n+1}}=\frac{1}{2^n} $，所以 $ \frac{2}{a_2}<\frac{1}{2^1} $， $ \frac{2}{a_3}<\frac{1}{2^2} $， $ \cdots $， $ \frac{2}{a_{n+1}}<\frac{1}{2^n} $，

将以上各式相加得 $ \frac{2}{a_2}+\frac{2}{a_3}+\cdots+\frac{2}{a_{n+1}}<\frac{1}{2^1}+\frac{1}{2^2}+\cdots+\frac{1}{2^n}=\frac{\frac{1}{2}\left[1-\left(\frac{1}{2}\right)^n\right]}{1-\frac{1}{2}}=1-\left(\frac{1}{2}\right)^n=1-\frac{1}{2^n} $.

## 强化训练

考虑到本节涉及的题型都有一定的综合性和难度，故不设 A 组题，只设计了 B 组和 C 组题.

B 组 强化能力

1. (2025·四川成都开学考试)

数列 $\{a_n\}$ 满足 $a_{n+1} = (-1)^n a_n + n (n \in \mathbb{N}^*)$，则 $\{a_n\}$ 的前 100 项和 $S_{100} = $___.