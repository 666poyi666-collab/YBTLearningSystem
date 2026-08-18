当 $k=2$ 时，$f(x)=(\mathrm{e}^x-1)(x-1)^2$，$f'(x)=\mathrm{e}^x(x-1)^2+2(x-1)(\mathrm{e}^x-1)=(x-1)[(x+1)\mathrm{e}^x-2]$，

结合选项知只需判断 $x=1$ 的极值情况，可只考虑 $f'(x)$ 在 1 附近的正负情况，观察发现当 $x\to1$ 时，$(x+1)\mathrm{e}^x-2\to2\mathrm{e}-2>0$，所以 $f'(x)$ 的正负由 $x-1$ 决定，下面通过简单的放缩来严格论证，

在 $\left(\frac{1}{2},1\right)$ 上，$(x+1)\mathrm{e}^x-2>\frac{3}{2}\sqrt{\mathrm{e}}-2>0$，$x-1<0$，所以 $f'(x)<0$，

在 $(1,+\infty)$ 上，$(x+1)\mathrm{e}^x-2>2\mathrm{e}-2>0$，$x-1>0$，所以 $f'(x)>0$，

从而 $f(x)$ 在 $\left(\frac{1}{2},1\right)$ 上 $\searrow$，在 $(1,+\infty)$ 上 $\nearrow$，故 $f(x)$ 在 $x=1$ 处取到极小值。

答案：C

【例 6】（2021·新高考Ⅰ卷）函数  $ f(x)=\left|2x-1\right|-2\ln x $ 的最小值为___.

解法1：由题意， $ f(x)=\begin{cases}1-2x-2\ln x,0<x\leq\frac{1}{2}\\2x-1-2\ln x,x>\frac{1}{2}\end{cases} $，分段函数求最值，应分段考虑，再比较各段的最值，

显然 $ f(x) $在 $ \left(0,\frac{1}{2}\right] $上 $ \searrow $，所以 $ f(x) $在 $ \left(0,\frac{1}{2}\right] $上的最小值为 $ f\left(\frac{1}{2}\right)=1-2\times\frac{1}{2}-2\ln\frac{1}{2}=2\ln2 $；

当 $ x>\frac{1}{2} $时， $ f'(x)=2-\frac{2}{x}=\frac{2(x-1)}{x} $，所以 $ f'(x)>0\Leftrightarrow x>1 $， $ f'(x)<0\Leftrightarrow\frac{1}{2}<x<1 $，

从而 $ f(x) $在 $ \left(\frac{1}{2},1\right) $上 $ \searrow $，在 $ (1,+\infty) $上 $ \nearrow $，故 $ f(x) $在 $ \left(\frac{1}{2},+\infty\right) $上的最小值为 $ f(1)=1 $；

因为 $ 1<2\ln2 $，所以 $ f(x) $的最小值为1

因为 $ 1<2\ln2 $，所以 $ f(x) $的最小值为1.

解法2：解析式中有  $ 2x $ 和  $ 2\ln x $，由此可联想到经典切线放缩不等式  $ \ln x \leq x-1 $，故也可尝试直接用此不等式将解析式进行放缩，看能否凑成定值，由经典切线放缩不等式， $ \ln x \leq x-1 $，所以  $ 2\ln x \leq 2(x-1) $，故  $ f(x)=|2x-1|-2\ln x \geq 2x-1-2\ln x \geq 2x-1-2(x-1)=1 $，又  $ f(1)=1 $，所以  $ f(x)_{\min}=1 $。

答案：1

类型IV：讨论单调性

【例 7】（2017 • 新课标 I 卷（节选））已知函数  $ f(x) = a\mathrm{e}^{2x} + (a-2)\mathrm{e}^x - x $，讨论  $ f(x) $ 的单调性。

解：由题意， $ f(x) $ 的定义域为  $ \mathbb{R} $，且  $ f'(x) = 2a\mathrm{e}^{2x} + (a-2)\mathrm{e}^x - 1 = (2\mathrm{e}^x + 1)(a\mathrm{e}^x - 1) $，

（只需看  $ a\mathrm{e}^x - 1 $ 这部分，它是否变号由  $ a $ 的正负决定，故据此讨论）

当  $ a \leq 0 $ 时， $ 2\mathrm{e}^x + 1 > 0 $， $ a\mathrm{e}^x - 1 < 0 $，所以  $ f'(x) < 0 $ 恒成立，故  $ f(x) $ 在  $ \mathbb{R} $ 上单调递减；

当  $ a > 0 $ 时， $ f'(x) > 0 \Leftrightarrow x > \ln\frac{1}{a} $， $ f'(x) < 0 \Leftrightarrow x < \ln\frac{1}{a} $，

所以  $ f(x) $ 在  $ \left(-\infty, \ln\frac{1}{a}\right) $ 上单调递减，在  $ \left(\ln\frac{1}{a}, +\infty\right) $ 上单调递增。

【变式】（2016·山东卷（节选））已知  $ f(x)=a(x-\ln x)+\frac{2x-1}{x^2} $， $ a\in\mathbb{R} $，讨论  $ f(x) $ 的单调性.

解：由题意， $ f'(x)=a\left(1-\frac{1}{x}\right)+\frac{2x^{2}-2x(2x-1)}{x^{4}}=\frac{a(x-1)}{x}+\frac{2(1-x)}{x^{3}}=\frac{(x-1)(ax^{2}-2)}{x^{3}} $，x>0，

（分母恒为正，只需看分子的两项，x-1在x=1处变号， $ ax^{2}-2 $是否变号由a的正负决定，故先讨论a的正负）