所以  $ S_{n}-S_{n-1}+1=2a_{n}-2a_{n-1} $，从而  $ a_{n}+1=2a_{n}-2a_{n-1} $，故  $ a_{n}=2a_{n-1}+1 $ ①，

（怎样由①求 $ a_{n} $？式①中除了 $ a_{n} $和 $ 2a_{n-1} $外，还有个常数项，于是我们就想，若能把左、右两边的 $ a_{n} $和 $ a_{n-1} $配出相同的常数项，就能构造一个等比数列，求出 $ a_{n} $，怎么配？可考虑用待定系数法，假设 $ a_{n}+\lambda=2(a_{n-1}+\lambda) $，则 $ a_{n}=2a_{n-1}+\lambda $，与 $ a_{n}=2a_{n-1}+1 $对比得 $ \lambda=1 $，构造的方法就有了）

由  $ a_{n}=2a_{n-1}+1 $ 可得  $ a_{n}+1=2(a_{n-1}+1) $，（此时可以得出  $ \{a_{n}+1\} $ 是等比数列了吗？别急，还要看看首项  $ a_{1}+1 $ 是否为 0，可在所给等式中取 n=1，求出  $ a_{1} $ 在  $ S_{n}+n=2a_{n} $ 中取 n=1 可得  $ S_{1}+1=2a_{1} $，结合  $ S_{1}=a_{1} $ 可得  $ a_{1}=1 $，所以  $ a_{1}+1=2 $，从而  $ \{a_{n}+1\} $ 是首项和公比都为 2 的等比数列，故  $ a_{n}+1=2^{n} $，所以  $ a_{n}=2^{n}-1 $.

【反思】遇到形如  $ a_n = A a_{n-1} + B (A \neq 0, A \neq 1, B \neq 0) $ 的递推公式，可考虑通过待定系数法构造等比数列求  $ a_n $，即设  $ a_n + \lambda = A (a_{n-1} + \lambda) $，则  $ a_n = A a_{n-1} + \lambda (A-1) $，与  $ a_n = A a_{n-1} + B $ 对比可得  $ \lambda (A-1) = B $，于是  $ \lambda = \frac{B}{A-1} $，构造的方法就有了。那如果将上述递推式中的 B 换成与 n 有关的代数式，又怎么办呢？我们来看下面的变式。

【变式】记 $ S_{n} $为数列 $ \{a_{n}\} $的前n项和，已知 $ 2S_{n}+a_{n}=3^{n} $

（1）求 $ a_{1} $;

（2）求数列 $ \{a_{n}\} $的通项公式；

（3）求 $ S_{n} $的最小值.

解：（1）在$2S_n + a_n = 3^n$中令$n=1$可得$2S_1 + a_1 = 3$，结合$S_1 = a_1$可解得：$a_1 = 1$。

（2）（涉及$S_n$与$a_n$的关系式，让求$a_n$，考虑退$n$相减，消去$S_n$）

因为$2S_n + a_n = 3^n$，所以当$n \geq 2$时，$2S_{n-1} + a_{n-1} = 3^{n-1}$，两式相减得$2(S_n - S_{n-1}) + a_n - a_{n-1} = 3^n - 3^{n-1}$，

所以$2a_n + a_n - a_{n-1} = 3 \times 3^{n-1} - 3^{n-1}$，整理得：$a_n = \frac{1}{3}a_{n-1} + \frac{2}{9} \times 3^n$（$n \geq 2$）①，

（式①与例12中的$a_n=2a_{n-1}+1$相比，除$a_n$和$a_{n-1}$外，余下的不是常数了，怎么办？可以想象，构造的核心是凑出前后项，$\frac{2}{9}\times3^n$这一结构的前后项可统一设为$\lambda\cdot3^n$和$\lambda\cdot3^{n-1}$，于是可设$a_n+\lambda\cdot3^n=\frac{1}{3}(a_{n-1}+\lambda\cdot3^{n-1})$，整理可得$a_n=\frac{1}{3}a_{n-1}-\frac{8\lambda}{9}\cdot3^n$，与式①对比可得$-\frac{8\lambda}{9}=\frac{2}{9}$，于是$\lambda=-\frac{1}{4}$，构造的方法就有了）

由①得$a_n-\frac{1}{4}\times3^n=\frac{1}{3}\left(a_{n-1}-\frac{1}{4}\times3^{n-1}\right)$，又$a_1-\frac{1}{4}\times3^1=\frac{1}{4}$，所以$\left\{a_n-\frac{1}{4}\times3^n\right\}$是首项为$\frac{1}{4}$，公比为$\frac{1}{3}$的等比数列，从而$a_n-\frac{1}{4}\times3^n=\frac{1}{4}\times\left(\frac{1}{3}\right)^{n-1}$，故$a_n=\frac{1}{4}\times3^n+\frac{1}{4}\times\left(\frac{1}{3}\right)^{n-1}$。

（3）因为 $ 2S_n + a_n = 3^n $，所以 $ S_n = \frac{1}{2}(3^n - a_n) = \frac{1}{2}\left[3^n - \frac{1}{4} \times 3^n - \frac{1}{4} \times \left(\frac{1}{3}\right)^{n-1}\right] = \frac{3}{8} \times 3^n - \frac{1}{8} \times \left(\frac{1}{3}\right)^{n-1} $，

（求  $ S_n $ 的最小值考虑先分析其单调性，由于  $ 3^n \nearrow $， $ \left(\frac{1}{3}\right)^n \searrow $，所以不难想象， $ S_n \nearrow $，下面给出严格分析）

因为  $ S_{n+1} - S_n = \frac{3}{8} \times 3^{n+1} - \frac{1}{8} \times \left(\frac{1}{3}\right)^n - \frac{3}{8} \times 3^n + \frac{1}{8} \times \left(\frac{1}{3}\right)^{n-1} = \frac{9}{8} \times 3^n - \frac{1}{8} \times \left(\frac{1}{3}\right)^n - \frac{3}{8} \times 3^n + \frac{3}{8} \times \left(\frac{1}{3}\right)^n = \frac{3}{4} \times 3^n + \frac{1}{4} \times \left(\frac{1}{3}\right)^n > 0 $，

所以  $ S_{n+1} > S_n $，从而  $ \{S_n\} $ 为递增数列，故  $ S_n $ 的最小值为  $ S_1 = a_1 = 1 $。

【反思】遇到像本题式①这样的形如  $ a_n = A a_{n-1} + B \cdot q^n $ ( $ A \ne 1, A \ne 0, A \ne q, B \ne 0, q \ne 0, q \ne 1 $) 的递推公式，可考虑设  $ a_n + \lambda \cdot q^n = A (a_{n-1} + \lambda \cdot q^{n-1}) $，整理后与原递推公式比较，求出  $ \lambda $，从而构造出等比数列求出  $ a_n $。