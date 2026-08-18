(i)当 $n=2$ 时，结论的左边 $=1+\frac{1}{2^2}=\frac{5}{4}$，右边 $=2-\frac{1}{2}=\frac{3}{2}$，所以左边 < 右边，结论成立；

(ii)假设当 $n=k(k \geq 2)$ 时，结论成立，即 $1+\frac{1}{2^2}+\frac{1}{3^2}+\cdots+\frac{1}{k^2}<2-\frac{1}{k}$ ①，

（要证当 $n=k+1$ 时结论也成立，即证 $1+\frac{1}{2^2}+\frac{1}{3^2}+\cdots+\frac{1}{k^2}+\frac{1}{(k+1)^2}<2-\frac{1}{k+1}$，怎么证？可以运用上面的假设将 $1+\frac{1}{2^2}+\frac{1}{3^2}+\cdots+\frac{1}{k^2}$ 这部分进行放缩）由①可得 $1+\frac{1}{2^2}+\frac{1}{3^2}+\cdots+\frac{1}{k^2}+\frac{1}{(k+1)^2}<2-\frac{1}{k}+\frac{1}{(k+1)^2}$ ②，

（于是只要再证 $2-\frac{1}{k}+\frac{1}{(k+1)^2}<2-\frac{1}{k+1}$，就能得到 $1+\frac{1}{2^2}+\frac{1}{3^2}+\cdots+\frac{1}{k^2}+\frac{1}{(k+1)^2}<2-\frac{1}{k+1}$，可通过作差比较来证）因为 $2-\frac{1}{k}+\frac{1}{(k+1)^2}-\left(2-\frac{1}{k+1}\right)=\frac{1}{k+1}-\frac{1}{k}+\frac{1}{(k+1)^2}=\frac{k(k+1)-(k+1)^2+k}{k(k+1)^2}=-\frac{1}{k(k+1)^2}<0$，

所以 $2-\frac{1}{k}+\frac{1}{(k+1)^2}<2-\frac{1}{k+1}$，结合②可得 $1+\frac{1}{2^2}+\frac{1}{3^2}+\cdots+\frac{1}{k^2}+\frac{1}{(k+1)^2}<2-\frac{1}{k+1}$，

故当 $n=k+1$ 时，结论也成立；

由(i)(ii)结合数学归纳法原理可知对任意的  $ n \geq 2 $ 且  $ n \in \mathbb{N}^* $，都有  $ 1 + \frac{1}{2^2} + \frac{1}{3^2} + \cdots + \frac{1}{n^2} < 2 - \frac{1}{n} $。

【反思】①初始值是结论中规定的 $n$ 的最小值，不一定是 1；②可以看到，用数学归纳法证明不等式与用数学归纳法证明等式的步骤类似，也是分两步完成：先证 $n$ 取初始值 $n_0$ 时不等式成立；再假设当 $n = k (k \geq n_0)$ 时不等式成立，由此出发推导出当 $n = k + 1$ 时不等式也成立。本题的结论不等式除了 $n \geq 2$ 外，没有附加条件，有时也会遇到在特定情境下的数列问题中让我们证明某不等式成立的情形，比如下面的变式。

【变式】已知数列 $\{a_n\}$ 满足 $a_1 = \frac{1}{2}$，且 $a_{n+1} = \frac{1}{3}a_n^3 + \frac{2}{3}a_n$，求证：$\frac{1}{2}\cdot\left(\frac{2}{3}\right)^{n+1} \leq a_n \leq \frac{1}{2}\cdot\left(\frac{3}{4}\right)^{n+1}$。

证法1：(i) 当 $n=1$ 时，结论即为 $\frac{1}{2} \leq a_1 \leq \frac{1}{2}$，也即 $a_1 = \frac{1}{2}$，由所给条件可知结论成立；

(ii) 假设当 $n=k$ ($k \geq 1$) 时结论成立，即 $\frac{1}{2}\cdot\left(\frac{2}{3}\right)^{k-1} \leq a_k \leq \frac{1}{2}\cdot\left(\frac{3}{4}\right)^{k-1}$ ①，（怎样证当 $n=k+1$ 时结论也成立？只需证 $\frac{1}{2}\cdot\left(\frac{2}{3}\right)^k \leq a_{k+1} \leq \frac{1}{2}\cdot\left(\frac{3}{4}\right)^k$，条件给出了 $a_{n+1}$ 与 $a_n$ 的关系式，故运用该关系式，结合上面的假设来证明）

由①可知 $a_k \geq \frac{1}{2}\cdot\left(\frac{2}{3}\right)^{k-1}$，所以 $a_{k+1} = \frac{1}{3}a_k^3 + \frac{2}{3}a_k \geq \frac{1}{3} \times \left[\frac{1}{2}\cdot\left(\frac{2}{3}\right)^{k-1}\right]^{3} + \frac{2}{3} \times \frac{1}{2}\cdot\left(\frac{2}{3}\right)^{k-1} = \frac{1}{24}\cdot\left(\frac{2}{3}\right)^{3k-3} + \frac{1}{3}\cdot\left(\frac{2}{3}\right)^{k-1}$

$= \frac{1}{24}\cdot\left(\frac{2}{3}\right)^{3k-3} + \frac{1}{3}\cdot\left(\frac{2}{3}\right)^k \cdot \frac{3}{2} = \frac{1}{24}\cdot\left(\frac{2}{3}\right)^{3k-3} + \frac{1}{2}\cdot\left(\frac{2}{3}\right)^k \geq \frac{1}{2}\cdot\left(\frac{2}{3}\right)^k$，

由①可知 $a_k \leq \frac{1}{2}\cdot\left(\frac{3}{4}\right)^{k-1}$，所以 $a_{k+1} = \frac{1}{3}a_k^3 + \frac{2}{3}a_k \leq \frac{1}{3}\cdot\left[\frac{1}{2}\cdot\left(\frac{3}{4}\right)^{k-1}\right]^{3} + \frac{2}{3} \times \frac{1}{2}\cdot\left(\frac{3}{4}\right)^{k-1} = \frac{1}{24}\cdot\left(\frac{3}{4}\right)^{3k-3} + \frac{1}{3}\cdot\left(\frac{3}{4}\right)^{k-1}$ ②，

（接下来只需证明 $\frac{1}{24}\cdot\left(\frac{3}{4}\right)^{3k-3} + \frac{1}{3}\cdot\left(\frac{3}{4}\right)^{k-1} \leq \frac{1}{2}\cdot\left(\frac{3}{4}\right)^k$，就能得出 $a_{k+1} \leq \frac{1}{2}\cdot\left(\frac{3}{4}\right)^k$，怎么证？可尝试作差比较）

$\frac{1}{24}\cdot\left(\frac{3}{4}\right)^{3k-3} + \frac{1}{3}\cdot\left(\frac{3}{4}\right)^{k-1} - \frac{1}{2}\cdot\left(\frac{3}{4}\right)^k = \frac{1}{24}\cdot\left(\frac{3}{4}\right)^{3k-3} + \frac{1}{3}\cdot\left(\frac{3}{4}\right)^{k-1} - \frac{1}{2}\cdot\left(\frac{3}{4}\right)^{k-1} \cdot \frac{3}{4} = \frac{1}{24}\cdot\left(\frac{3}{4}\right)^{3k-3} + \frac{1}{3}\cdot\left(\frac{3}{4}\right)^{k-1} - \frac{3}{8}\cdot\left(\frac{3}{4}\right)^{k-1}$

$= \frac{1}{24}\cdot\left(\frac{3}{4}\right)^{3k-3} - \frac{1}{24}\cdot\left(\frac{3}{4}\right)^{k-1} = \frac{1}{24}\cdot\left(\frac{3}{4}\right)^{k-1}\left[\left(\frac{3}{4}\right)^{2k-2} - 1\right]$，

因为 $k \geq 1$，所以 $\left(\frac{3}{4}\right)^{2k-2} \leq 1$，从而 $\left(\frac{3}{4}\right)^{2k-2} - 1 \leq 0$，故 $\frac{1}{24}\cdot\left(\frac{3}{4}\right)^{k-1}\left[\left(\frac{3}{4}\right)^{2k-2} - 1\right] \leq 0$，