当  $ a \leq 0 $ 时， $ ax^2 - 2 < 0 $， $ x^3 > 0 $，所以  $ f'(x) < 0 \Leftrightarrow x - 1 > 0 \Leftrightarrow x > 1 $， $ f'(x) > 0 \Leftrightarrow 0 < x < 1 $，故  $ f(x) $ 在  $ (0,1) $ 上单调递增，在  $ (1,+\infty) $ 上单调递减；

（再看 $a>0$ 的情况，此时 $ax^2-2$ 要变号，为了看出零点，可先将 $f'(x)$ 化为 $\frac{a(x-1)\left(x-\sqrt{\frac{2}{a}}\right)\left(x+\sqrt{\frac{2}{a}}\right)}{x^3}$，只需关注 $(x-1)\left(x-\sqrt{\frac{2}{a}}\right)$ 这部分，其余项全为正，两个零点是 $1$ 和 $\sqrt{\frac{2}{a}}$，它们的大小关系对 $f'(x)$ 在各段上的正负有影响，故又讨论两个零点的大小）

当 $0<a<2$ 时，$\sqrt{\frac{2}{a}}>1$，所以 $f'(x)>0 \Leftrightarrow 0<x<1$ 或 $x>\sqrt{\frac{2}{a}}$，$f'(x)<0 \Leftrightarrow 1<x<\sqrt{\frac{2}{a}}$，

故 $f(x)$ 在 $(0,1)$ 上单调递增，在 $\left(1,\sqrt{\frac{2}{a}}\right)$ 上单调递减，在 $\left(\sqrt{\frac{2}{a}},+\infty\right)$ 上单调递增；

当 $a=2$ 时，$f'(x)=\frac{2(x+1)(x-1)^2}{x^3} \geq 0$，所以 $f(x)$ 在 $(0,+\infty)$ 上单调递增；

当 $a>2$ 时，$0<\sqrt{\frac{2}{a}}<1$，所以 $f'(x)>0 \Leftrightarrow 0<x<\sqrt{\frac{2}{a}}$ 或 $x>1$，$f'(x)<0 \Leftrightarrow \sqrt{\frac{2}{a}}<x<1$，

故 $f(x)$ 在 $\left(0,\sqrt{\frac{2}{a}}\right)$ 上单调递增，在 $\left(\sqrt{\frac{2}{a}},1\right)$ 上单调递减，在 $(1,+\infty)$ 上单调递增。

## 类型V：不等式证明

【例 8】（2018·新课标Ⅱ卷（节选））已知  $ f(x) = \mathrm{e}^x - ax^2 $，若  $ a=1 $，证明：当  $ x \geq 0 $ 时， $ f(x) \geq 1 $。

证法1：若  $ a=1 $，则  $ f(x) = \mathrm{e}^x - x^2 $，要证  $ f(x) \geq 1 $，只需证  $ \mathrm{e}^x - x^2 \geq 1 $ ①，

（上述不等式中有  $ \mathrm{e}^x $，考虑变形成  $ \varphi(x)\mathrm{e}^x $ 或  $ \frac{\varphi(x)}{\mathrm{e}^x} $ 这种结构，求导分析可能更容易）

要证不等式①成立，只需证  $ \mathrm{e}^x \geq x^2 + 1 $，即证  $ \frac{x^2 + 1}{\mathrm{e}^x} \leq 1 $，

令  $ g(x) = \frac{x^2 + 1}{\mathrm{e}^x} $， $ x \geq 0 $，则  $ g'(x) = \frac{2x\mathrm{e}^x - \mathrm{e}^x(x^2 + 1)}{(\mathrm{e}^x)^2} = -\frac{(x - 1)^2}{\mathrm{e}^x} \leq 0 $，当且仅当  $ x=1 $ 时  $ g'(x) = 0 $，

所以  $ g(x) $ 在  $ [0, +\infty) $ 上单调递减，又  $ g(0) = 1 $，所以  $ g(x) \leq 1 $，即  $ \frac{x^2 + 1}{x^2} \leq 1 $，故  $ f(x) \geq 1 $ 成立。

证法2：（按证法1得到要证目标不等式成立，只需证①成立后，考虑到不等式①不算复杂，故也可尝试直接移项，构造函数求导分析）要证不等式①成立，只需证 $ e^x - x^2 - 1 \geq 0 $，设 $ h(x) = e^x - x^2 - 1 $， $ x \geq 0 $，则 $ h'(x) = e^x - 2x $，（不易直接判断正负，可继续求导） $ h''(x) = e^x - 2 $，

所以  $ h''(x) < 0 \Leftrightarrow 0 \leq x < \ln 2 $， $ h''(x) > 0 \Leftrightarrow x > \ln 2 $，从而  $ h'(x) $ 在  $ [0, \ln 2) $ 上单调递减，在  $ (\ln 2, +\infty) $ 上单调递增，故  $ h'(x) \geq h'(\ln 2) = \mathrm{e}^{\ln 2} - 2 \ln 2 = 2 - 2 \ln 2 > 0 $，所以  $ h(x) $ 在  $ [0, +\infty) $ 上单调递增，又  $ h(0) = \mathrm{e}^0 - 0^2 - 1 = 0 $，所以  $ h(x) \geq 0 $，即  $ \mathrm{e}^x - x^2 - 1 \geq 0 $，故当  $ x \geq 0 $ 时， $ f(x) \geq 1 $ 成立。