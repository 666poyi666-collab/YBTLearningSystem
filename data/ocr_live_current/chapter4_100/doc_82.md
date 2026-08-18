# 微专题1：几类常见的求前n项和的方法

习题：P1

## 内容提要

求数列的前 n 项和是数列板块的核心问题之一，在各类考试中，除了代等差、等比数列的前 n 项和公式求前 n 项和外，还需掌握以下几种常见的求和方法.

1. 裂项相消法：若数列  $ \{a_{n}\} $ 无法直接代公式求前 n 项和，但可将  $ a_{n} $ 拆分成  $ b_{n}-b_{n+1} $ 或  $ b_{n}-b_{n+2} $ 这种形式，那么相加时就能抵消一些项，从而达到求和的目的，这种求和方法叫做裂项相消法.

①常规裂项：设 $\{a_n\}$ 是公差为 $d(d \neq 0)$ 的等差数列，$a_n \neq 0$，则 $\frac{1}{a_n a_{n+1}}$ 可拆分成 $\frac{1}{d}\left(\frac{1}{a_n} - \frac{1}{a_{n+1}}\right)$，$\frac{1}{a_{n+2}}$ 可拆分成 $\frac{1}{2d}\left(\frac{1}{a_n} - \frac{1}{a_{n+2}}\right)$，按此裂项，可以求出数列 $\left\{\frac{1}{a_n a_{n+1}}\right\}$ 和 $\left\{\frac{1}{a_n a_{n+2}}\right\}$ 的前 $n$ 项和。

例如，若 $p_n = \frac{1}{n(n+1)}$，则 $p_n = \frac{1}{n} - \frac{1}{n+1}$，

所以数列 $\{p_n\}$ 的前 $n$ 项和 $P_n = 1 - \frac{1}{2} + \frac{1}{2} - \frac{1}{3} + \cdots + \frac{1}{n} - \frac{1}{n+1} = 1 - \frac{1}{n+1} = \frac{n}{n+1}$；

若 $q_n = \frac{1}{(2n-1)(2n+1)}$，则 $q_n = \frac{1}{2}\left(\frac{1}{2n-1} - \frac{1}{2n+1}\right)$，

所以数列 $\{q_n\}$ 的前 $n$ 项和 $Q_n = \frac{1}{2}\left(1 - \frac{1}{3} + \frac{1}{3} - \frac{1}{5} + \cdots + \frac{1}{2n-1} - \frac{1}{2n+1}\right) = \frac{1}{2}\left(1 - \frac{1}{2n+1}\right) = \frac{n}{2n+1}$；

若 $r_n = \frac{1}{n(n+2)}$，则 $r_n = \frac{1}{2}\left(\frac{1}{n} - \frac{1}{n+2}\right)$，

所以数列 $\{r_n\}$ 的前 $n$ 项和 $R_n = \frac{1}{2}\left(1 - \frac{1}{3} + \frac{1}{2} - \frac{1}{4} + \frac{1}{3} - \frac{1}{5} + \cdots + \frac{1}{n} - \frac{1}{n+2}\right)$

$= \frac{1}{2}\left[\left(1 + \frac{1}{2} + \frac{1}{3} + \cdots + \frac{1}{n}\right) - \left(\frac{1}{3} + \frac{1}{4} + \frac{1}{5} + \cdots + \frac{1}{n} + \frac{1}{n+1} + \frac{1}{n+2}\right)\right]$

$= \frac{1}{2}\left(1 + \frac{1}{2} - \frac{1}{n+1} - \frac{1}{n+2}\right) = \frac{3}{4} - \frac{1}{2}\left(\frac{1}{n+1} + \frac{1}{n+2}\right)$。

②非常规裂项：有的裂项更复杂，但本质仍是将 $ a_{n} $拆分成 $ b_{n}-b_{n+1} $，这类问题完成裂项的关键是寻找原数列通项中局部的前后项关系.

例如，设  $ a_n = \frac{2^{n+1}}{(2^n - 1)(2^{n+1} - 1)} $，则观察可发现分母的  $ 2^n - 1 $ 和  $ 2^{n+1} - 1 $ 恰好为前后项关系，故可

想象，若能将  $ a_n $ 变成  $ \frac{1}{2^n - 1} - \frac{1}{2^{n+1} - 1} $ 这种结构，就实现了裂项，但  $ \frac{1}{2^n - 1} - \frac{1}{2^{n+1} - 1} = \frac{2^{n+1} - 1 - (2^n - 1)}{(2^n - 1)(2^{n+1} - 1)} $