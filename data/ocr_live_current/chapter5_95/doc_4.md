个距离0要多近有多近的量，既可为正也可为负，也就是说， $ \Delta x $， $ 2\Delta x $， $ -\Delta x $等都是无限趋近于0的量，所以都可以充当导数定义中 $ \Delta x $的角色，我们通过下面的变式来加深理解。

【变式】若 $ f'(2)=4 $，则 $ \lim_{\Delta x\to0}\frac{f(2+\Delta x)-f(2-\Delta x)}{\Delta x}= $（）

A. 2 B. 4 C. 6 D. 8

解法 1：根据导数的定义， $ f'(x_0) = \lim_{\Delta x \to 0} \frac{\Delta y}{\Delta x} = \lim_{\Delta x \to 0} \frac{f(x_0 + \Delta x) - f(x_0)}{\Delta x} $，故可尝试将所给式子按此凑形式，怎么凑？

涉及  $ f(2 + \Delta x) $ 和  $ f(2 - \Delta x) $，分别凑一个  $ -f(2) $ 即可，

由题意， $ \lim_{\Delta x \to 0} \frac{f(2 + \Delta x) - f(2 - \Delta x)}{\Delta x} = \lim_{\Delta x \to 0} \frac{f(2 + \Delta x) - f(2) - [f(2 - \Delta x) - f(2)]}{\Delta x} $

 $ = \lim_{\Delta x \to 0} \frac{f(2 + \Delta x) - f(2)}{\Delta x} - \lim_{\Delta x \to 0} \frac{f(2 - \Delta x) - f(2)}{\Delta x} = f'(2) - \lim_{\Delta x \to 0} \frac{f(2 - \Delta x) - f(2)}{\Delta x} $ ①，

式①中的  $ \lim_{\Delta x \to 0} \frac{f(2 - \Delta x) - f(2)}{\Delta x} $ 怎么处理？可将  $ -\Delta x $ 看作整体，换元处理，

令  $ \Delta t = -\Delta x $，则当  $ \Delta x \to 0 $ 时， $ \Delta t \to 0 $，所以  $ \lim_{\Delta x \to 0} \frac{f(2 - \Delta x) - f(2)}{\Delta x} = \lim_{\Delta x \to 0} \frac{f(2 - \Delta x) - f(2)}{-(-\Delta x)} = -\lim_{\Delta x \to 0} \frac{f(2 - \Delta x) - f(2)}{-\Delta x} $

 $ = -\lim_{\Delta x \to 0} \frac{f(2 + \Delta x) - f(2)}{\Delta x} = -f'(2) $，代入①得  $ \lim_{\Delta x \to 0} \frac{f(2 + \Delta x) - f(2 - \Delta x)}{\Delta x} = f'(2) - [-f'(2)] = 2f''(2) = 8 $。

解法 2：根据导数的定义， $ f'(x_0) = \lim_{\Delta x \to 0} \frac{\Delta y}{\Delta x} $，若将  $ f(2 + \Delta x) - f(2 - \Delta x) $ 看成  $ \Delta y $，那相应的  $ \Delta x $ 是谁呢？请注意， $ \Delta x $ 表示的是自变量的改变量，这里应为  $ (2 + \Delta x) - (2 - \Delta x) $，故也可直接按此对分母的系数进行调整，

因为  $ 2 + \Delta x - (2 - \Delta x) = 2\Delta x $，所以  $ \lim_{\Delta x \to 0} \frac{f(2 + \Delta x) - f(2 - \Delta x)}{\Delta x} = \lim_{\Delta x \to 0} \left[ 2 \cdot \frac{f(2 + \Delta x) - f(2 - \Delta x)}{2\Delta x} \right] $

 $ = 2 \lim_{2\Delta x \to 0} \frac{f(2 + \Delta x) - f(2 - \Delta x)}{2\Delta x} = 2f'(2) = 2 \times 4 = 8 $。

答案：D

【反思】在导数定义式  $ f'(x_0) = \lim_{\Delta x \to 0} \frac{\Delta y}{\Delta x} $ 中， $ \Delta y $ 是函数值的改变量， $ \Delta x $ 是相应的自变量的改变量，解法 2 就是抓住了这一特征，根据分子中函数值的改变量，直接找到对应的自变量的改变量，凑出导数定义式，更便捷。

## 类型III：用导数定义求函数的切线

【例 9】函数  $ f(x)=2x^{2}+4x $ 在 x=3 处的切线方程是 ___.

解析：（要求切线方程，需要切点坐标和切线斜率，前者直接代解析式求  $ f(3) $ 即可，后者即为  $ f'(3) $，可用导数的定义求得）由题意， $ f(3)=2\times3^2+4\times3=30 $，所以切点为  $ (3,30) $，

又  $ \lim_{\Delta x \to 0} \frac{f(3 + \Delta x) - f(3)}{\Delta x} = \lim_{\Delta x \to 0} \frac{2(3 + \Delta x)^2 + 4(3 + \Delta x) - 30}{\Delta x} = \lim_{\Delta x \to 0} \frac{2(\Delta x)^2 + 16\Delta x}{\Delta x} = \lim_{\Delta x \to 0} (2\Delta x + 16) = 16 $，

所以  $ f(x) $ 在 x=3 处的切线斜率为 16，故该切线的方程为  $ y-30=16(x-3) $，整理得：y=16x-18.

答案：y=16x-18

【反思】①函数在某一点处的导数值，即为函数在该点处的切线斜率；②由于切点既在函数图象上，又在切线上，是沟通函数与切线的桥梁，所以切线问题一定要牢牢抓住切点。本题已知切点，如果不知道切点，那么就需要设出切点来处理，我们来看下面的变式。

【变式】已知函数  $ f(x)=1-x^{3} $，则  $ f(x) $ 的过点  $ (-1,6) $ 的切线方程为 ___.

解析：切线只是经过点 $ (-1,6) $，这意味着 $ (-1,6) $不一定是切点，怎么办？不知道切点，考虑设切点，