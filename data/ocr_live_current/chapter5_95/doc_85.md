设  $ r(x) = \mathrm{e}^x + x - x \mathrm{e}^{\frac{1}{x}} - 1 $， $ 0 < x < 1 $，则  $ r'(x) = \mathrm{e}^x + 1 - \left[ \mathrm{e}^{\frac{1}{x}} + x \mathrm{e}^{\frac{1}{x}} \cdot \left( -\frac{1}{x^2} \right) \right] = \mathrm{e}^x + 1 + \left( \frac{1}{x} - 1 \right) \mathrm{e}^{\frac{1}{x}} > 0 $，

所以  $ r(x) $ 在  $ (0,1) $ 上单调递增，又  $ r(1) = 0 $，所以  $ r(x) < 0 $，从而  $ F'(x) = \frac{(x-1)r(x)}{x^2} > 0 $，

故  $ F(x) $ 在  $ (0,1) $ 上单调递增，又  $ F(1) = 0 $，所以  $ F(x) < 0 $，故  $ F(x_1) = f(x_1) - f\left( \frac{1}{x_1} \right) < 0 $，所以  $ x_1 x_2 < 1 $。

解法2：（1）（注意到 $ \frac{e^x}{x} = \frac{e^x}{e^{\ln x}} = e^{x-\ln x} $，于是 $ f(x) $的解析式中含 $ x $的部分以 $ x - \ln x $这一结构整体出现，可考虑将该结构换元，简化 $ f(x) $的解析式，再求导分析）

由题意， $ f(x) $的定义域为 $ (0,+\infty) $，且 $ f(x)=\frac{e^x}{x}-\ln x+x-a=e^{x-\ln x}+x-\ln x-a $，

令  $ u = x - \ln x $，则  $ f(x) = \mathrm{e}^u + u - a $，设  $ \varphi(x) = x - \ln x $， $ x > 0 $，则  $ \varphi'(x) = 1 - \frac{1}{x} = \frac{x - 1}{x} $，

所以  $ \varphi'(x) > 0 \Leftrightarrow x > 1 $， $ \varphi'(x) < 0 \Leftrightarrow 0 < x < 1 $，从而  $ \varphi(x) $ 在  $ (0,1) $ 上单调递减，在  $ (1,+\infty) $ 上单调递增，

故  $ \varphi(x)_{\min} = \varphi(1) = 1 $，所以  $ u \geq 1 $，因为函数  $ y = \mathrm{e}^u + u - a $ 为增函数，

所以当  $ u = 1 $ 时， $ f(x) $ 取得最小值  $ \mathrm{e} + 1 - a $，因为  $ f(x) \geq 0 $，所以  $ \mathrm{e} + 1 - a \geq 0 $，解得： $ a \leq \mathrm{e} + 1 $，

故实数  $ a $ 的取值范围是  $ (-\infty, \mathrm{e} + 1] $。

（2）由（1）知  $ f(x)=0 \Leftrightarrow e^u + u - a = 0 $，其中  $ u = x - \ln x $，由（1）可得要使  $ f(x) $ 有两个零点  $ x_1 $， $ x_2 $，则  $ f(x)_{\min} = e + 1 - a < 0 $，此时  $ a > e + 1 $，且  $ x_1 $， $ x_2 $ 是方程  $ u = x - \ln x $ 的两根，不妨设  $ x_1 < x_2 $，

 $$ x_{1}x_{2}<1\text{？} $$ 

 $$ x_{1},x_{2} $$ 

 $$ 0<x_{1}<1<x_{2} $$ 

 $$ \left\{\begin{aligned}x_{1}-\ln x_{1}&=u\\ x_{2}-\ln x_{2}&=u\end{aligned}\right. $$ 

 $$ x_{1},x_{2} $$ 

两式作差得： $ x_1 - x_2 - \ln\frac{x_1}{x_2} = 0 $ ②，（式②中有两个变量，考虑消元，如何消元？经尝试，由式②无法直接反解

 $$ x_{1} $$ 

 $$ x_{2} $$ 

 $$ \frac{x_{1}}{x_{2}} $$ 

 $$ x_{1},x_{2} $$ 

设  $ t = \frac{x_1}{x_2} $，则  $ 0 < t < 1 $，且  $ x_1 = tx_2 $，代入②可得  $ tx_2 - x_2 - \ln t = 0 $，所以  $ x_2 = \frac{\ln t}{t-1} $， $ x_1 = tx_2 = \frac{t \ln t}{t-1} $，从而  $ x_1 x_2 = \frac{t \ln^2 t}{(t-1)^2} $，故要证  $ x_1 x_2 < 1 $，只需证  $ \frac{t \ln^2 t}{(t-1)^2} < 1 $，即证  $ \ln^2 t < \frac{(t-1)^2}{t} $，也即证  $ -\ln t < \frac{1-t}{\sqrt{t}} $，所以只需证  $ -2 \ln \sqrt{t} < \frac{1}{\sqrt{t}} - \sqrt{t} $，即证  $ 2 \ln \sqrt{t} + \frac{1}{\sqrt{t}} - \sqrt{t} > 0 $，令  $ m = \sqrt{t} $，则  $ 0 < m < 1 $，

且 $ 2\ln\sqrt{t}+\frac{1}{\sqrt{t}}-\sqrt{t}>0 $即为 $ 2\ln m+\frac{1}{m}-m>0 $，（只有一个变量m了，且此不等式不算复杂，可直接构造函数求导分析）设 $ p(m)=2\ln m+\frac{1}{m}-m $， $ 0<m<1 $，则 $ p'(m)=\frac{2}{m}-\frac{1}{m^2}-1=-\frac{(m-1)^2}{m^2}<0 $，

所以 $ p(m) $在 $ (0,1) $上单调递减，又 $ p(1)=0 $，所以 $ p(m)>0 $，即 $ 2\ln m+\frac{1}{m}-m>0 $，故 $ x_1x_2<1 $成立。

【例 14】（2022·新课标Ⅱ卷）已知函数  $ f(x)=xe^{ax}-e^x $

（1）当a=1时，讨论 $ f(x) $的单调性；

（2）当x>0时， $ f(x)<-1 $，求a的取值范围；

（3）设  $ n \in \mathbb{N}^* $，证明： $ \frac{1}{\sqrt{1^2 + 1}} + \frac{1}{\sqrt{2^2 + 2}} + \cdots + \frac{1}{\sqrt{n^2 + n}} > \ln(n + 1) $.