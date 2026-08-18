所以  $ f'(x) > 0 \Leftrightarrow 0 < x < \frac{1}{2} $ 或  $ x > 1 $， $ f'(x) < 0 \Leftrightarrow \frac{1}{2} < x < 1 $，

从而  $ f(x) $ 在  $ \left(0,\frac{1}{2}\right) $ 上单调递增，在  $ \left(\frac{1}{2},1\right) $ 上单调递减，在  $ (1,+\infty) $ 上单调递增，

故  $ f(x) $ 有极大值  $ f\left(\frac{1}{2}\right)=\ln\frac{1}{2}+\left(\frac{1}{2}\right)^2-3\times\frac{1}{2}+2=\frac{3}{4}-\ln2 $，极小值  $ f(1)=\ln1+1^2-3\times1+2=0 $。

【反思】求  $ f(x) $ 的极值这类问题的核心是分析  $ f(x) $ 的单调性，上面的解法1和解法2本质上是一样的，只是写法不同，大家可以根据自己的喜好任选一种写法，本书后续内容都采用解法2的写法。本题求极值时，函数已经无参，有时也会遇到含参的情况，我们来看两个变式。

【变式1】已知函数  $ f(x)=\mathrm{e}^{x}-ax-a^{3} $

（1）当a=2时，求曲线 $ y=f(x) $在 $ (0,f(0)) $处的切线方程；

（2）求 $ f(x) $的极值.

解：（1）当 $a=2$ 时，$f(x)=\mathrm{e}^x - 2x - 8$，所以 $f'(x)=\mathrm{e}^x - 2$，故 $f'(0)=\mathrm{e}^0 - 2 = -1$，

又 $f(0)=\mathrm{e}^0 - 2 \times 0 - 8 = -7$，所以曲线 $y=f(x)$ 在 $(0,f(0))$ 处的切线方程为 $y-(-7)=-1 \cdot (x-0)$，即 $x+y+7=0$。

（2）由题意，$f'(x)=\mathrm{e}^x - a$，$x \in \mathbf{R}$，（求 $f(x)$ 的极值，先分析 $f(x)$ 的单调性，令 $f'(x)=0$ 得 $x=\ln a$，但这只在 $a>0$ 时才成立，故分 $a \leq 0$ 和 $a>0$ 两种情况讨论）

当 $a \leq 0$ 时，$\mathrm{e}^x > 0$，所以 $f'(x)=\mathrm{e}^x - a > 0$，从而 $f(x)$ 在 $\mathbf{R}$ 上单调递增，故 $f(x)$ 无极值；

当 $a>0$ 时，$f'(x)<0 \Leftrightarrow \mathrm{e}^x - a<0 \Leftrightarrow \mathrm{e}^x < a \Leftrightarrow x<\ln a$，$f'(x)>0 \Leftrightarrow x>\ln a$，

所以 $f(x)$ 在 $(-\infty, \ln a)$ 上单调递减，在 $(\ln a, +\infty)$ 上单调递增，

故 $f(x)$ 有极小值 $f(\ln a)=\mathrm{e}^{\ln a} - a \ln a - a^3 = a - a \ln a - a^3$，无极大值。

【变式 2】已知函数  $ f(x) = a\mathrm{e}^x - \frac{1}{\mathrm{e}^x} - (a+1)x - 2 $，其中  $ a \in \mathbb{R} $，求函数  $ f(x) $ 的极值.

解：由题意， $ f'(x) = a\mathrm{e}^x + \frac{1}{\mathrm{e}^x} - (a+1) = \frac{a(\mathrm{e}^x)^2 - (a+1)\mathrm{e}^x + 1}{\mathrm{e}^x} = \frac{(\mathrm{e}^x - 1)(a\mathrm{e}^x - 1)}{\mathrm{e}^x} $， $ x \in \mathbf{R} $，

（令  $ f'(x)=0 $ 得 x=0 或  $ \ln\frac{1}{a} $，但  $ \ln\frac{1}{a} $ 只在 a>0 时才有意义，故先讨论 a 的正负）

当  $ a \leq 0 $ 时， $ ae^x - 1 < 0 $，所以  $ f'(x) > 0 \Leftrightarrow e^x - 1 < 0 \Leftrightarrow e^x < 1 \Leftrightarrow x < 0 $， $ f'(x) < 0 \Leftrightarrow x > 0 $，从而  $ f(x) $ 在  $ (-\infty, 0) $ 上单调递增，在  $ (0, +\infty) $ 上单调递减，

故  $ f(x) $ 有极大值  $ f(0)=ae^{0}-\frac{1}{e^{0}}-(a+1)\cdot0-2=a-3 $，无极小值；

（再看 $a>0$ 的情况，此时 $f'(x)$ 有 0 和 $\ln\frac{1}{a}$ 两个零点，它们的大小关系不确定，该大小关系会影响 $f'(x)$ 在各段上的正负情况，故又讨论 $\ln\frac{1}{a}$ 与 0 的大小，即讨论 $a$ 与 1 的大小）

当 $0 < a < 1$ 时，$\frac{1}{a} > 1$，$\ln\frac{1}{a} > 0$，所以 $f'(x) > 0 \Leftrightarrow (\mathrm{e}^x - 1)\left(\mathrm{e}^x - \frac{1}{a}\right) > 0 \Leftrightarrow \mathrm{e}^x < 1$ 或 $\mathrm{e}^x > \frac{1}{a} \Leftrightarrow x < 0$ 或 $x > \ln\frac{1}{a}$。同理，$f'(x) < 0 \Leftrightarrow 0 < x < \ln\frac{1}{a}$，所以 $f(x)$ 在 $(-\infty, 0)$ 上单调递增，在 $\left(0, \ln\frac{1}{a}\right)$ 上单调递减，在 $\left(\ln\frac{1}{a}, +\infty\right)$ 上单调递增，故 $f(x)$ 有极大值 $f(0) = a - 3$，极小值 $f\left(\ln\frac{1}{a}\right) = a\mathrm{e}^{\ln\frac{1}{a}} - \frac{1}{\mathrm{e}^{\ln\frac{1}{a}}} - (a+1)\ln\frac{1}{a} - 2$。