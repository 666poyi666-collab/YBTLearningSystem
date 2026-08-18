因为  $ f'(x) < \frac{1}{3}x $，所以  $ f'(x) - \frac{1}{3}x < 0 $，设  $ g(x) = f(x) - \frac{1}{6}x^2 $，则  $ g'(x) = f'(x) - \frac{1}{3}x < 0 $，所以  $ g(x) $ 在  $ \mathbb{R} $ 上  $ \searrow $，既然有了  $ g(x) $ 的单调性，那么当然将要求解的不等式往  $ g(x) $ 上去化，

 $ f(3a-1) - f(a) < \frac{4}{3}a^2 - a + \frac{1}{6} \Leftrightarrow f(3a-1) - \frac{4}{3}a^2 + a - \frac{1}{6} < f(a) \Leftrightarrow f(3a-1) - \frac{4}{3}a^2 + a - \frac{1}{6} - \frac{1}{6}a^2 < f(a) - \frac{1}{6}a^2 \Leftrightarrow f(3a-1) - \left(\frac{3}{2}a^2 - a + \frac{1}{6}\right) < f(a) - \frac{1}{6}a^2 \Leftrightarrow f(3a-1) - \frac{1}{6}(9a^2 - 6a + 1) < f(a) - \frac{1}{6}a^2 \Leftrightarrow f(3a-1) - \frac{1}{6}(3a-1)^2 < f(a) - \frac{1}{6}a^2 \Leftrightarrow g(3a-1) < g(a) $，结合  $ g(x) $ 在  $ \mathbb{R} $ 上  $ \searrow $ 可得  $ 3a-1 > a $，所以  $ a > \frac{1}{2} $。

答案：B

【例 11】已知函数  $ f(x) $ 为奇函数，且当  $ x \in (-\infty, 0) $ 时， $ f(x) + x f'(x) < 0 $，记  $ a = 3^{0.2} f(3^{0.2}) $， $ b = \ln 2 f(\ln 2) $， $ c = -3 f(-3) $，则  $ a $， $ b $， $ c $ 的大小关系是（ ）

A.  $ a > b > c $          B.  $ c > b > a $          C.  $ a > c > b $          D.  $ c > a > b $

解析： $ f(x) + xf'(x) < 0 $ 中的  $ f(x) $ 和  $ xf'(x) $ 各自的原函数都不易看出，故不能拆开来看了，怎么办呢？考虑整体观察原函数，谁求导后等于  $ f(x) + xf'(x) $？因为中间是加号，所以联想到积的导数，进一步尝试会发现  $ xf(x) $ 求导后结果就是  $ f(x) + xf'(x) $，构造原函数的思路就有了，

设  $ g(x) = xf(x) $，当  $ x \in (-\infty, 0) $ 时， $ g'(x) = f(x) + xf'(x) < 0 $，所以  $ g(x) $ 在  $ (- \infty, 0) $ 上  $ \searrow $，

由题意， $ a = 3^{0.2} f(3^{0.2}) = g(3^{0.2}) $， $ b = \ln 2 f(\ln 2) = g(\ln 2) $， $ c = -3 f(-3) = g(-3) $，

三个自变量的值不都在  $ (- \infty, 0) $ 上，怎么办呢？题干还给出了  $ f(x) $ 为奇函数，故考虑结合奇偶性来看，

由题意， $ f(x) $ 为奇函数，所以  $ g(-x) = -xf(-x) = -x[-f(x)] = xf(x) = g(x) $，故  $ g(x) $ 为偶函数，

所以  $ g(x) $ 在  $ (0, +\infty) $ 上  $ \nearrow $，且  $ c = g(-3) = g(3) $，因为  $ 0 < \ln 2 < 1 < 3^{0.2} < 3 $，所以  $ g(\ln 2) < g(3^{0.2}) < g(3) $，

从而  $ b < a < c $，故  $ c > a > b $。

答案：D

【反思】若各部分的原函数无法单独看出，则常整体考虑，此时一般对应着积、商的导数，这种情况下要顺利地构造出原函数，需要熟悉一些常见的模型，我们用下面的表格给大家归纳出来：


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>已知的不等式中所含结构</td><td style='text-align: center; word-wrap: break-word;'>构造原函数的方法</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ xf&#x27;(x) + f(x) $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = xf(x), \quad F&#x27;(x) = f(x) + xf&#x27;(x) $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ xf&#x27;(x) - f(x) $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = \frac{f(x)}{x}, \quad F&#x27;(x) = \frac{xf&#x27;(x) - f(x)}{x^2} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ xf&#x27;(x) + 2f(x) $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = x^2f(x), \quad F&#x27;(x) = x[xf&#x27;(x) + 2f(x)] $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ xf&#x27;(x) - 2f(x) $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = \frac{f(x)}{x^2}, \quad F&#x27;(x) = \frac{xf&#x27;(x) - 2f(x)}{x^3} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x) + f&#x27;(x) $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = e^x, \quad F&#x27;(x) = e^x[f(x) + f&#x27;(x)] $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x) - f(x) $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = \frac{f(x)}{e^x}, \quad F&#x27;(x) = \frac{f&#x27;(x) - f(x)}{e^x} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)\sin x + f(x)\cos x $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = f(x)\sin x, \quad F&#x27;(x) = f&#x27;(x)\sin x + f(x)\cos x $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)\cos x - f(x)\sin x $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = f(x)\cos x, \quad F&#x27;(x) = f&#x27;(x)\cos x - f(x)\sin x $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)\sin x - f(x)\cos x $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = \frac{f(x)}{\sin x}, \quad F&#x27;(x) = \frac{f&#x27;(x)\sin x - f(x)\cos x}{\sin^2 x} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)\cos x + f(x)\sin x $</td><td style='text-align: center; word-wrap: break-word;'>$ F(x) = \frac{f(x)}{\cos x}, \quad F&#x27;(x) = \frac{f&#x27;(x)\cos x + f(x)\sin x}{\cos^2 x} $</td></tr></table>

【变式1】设定义在$\mathbb{R}$上的函数$f(x)$的导函数为$f'(x)$，若$f(x)>f'(x)$，且$f(x)+2025$为奇函数，