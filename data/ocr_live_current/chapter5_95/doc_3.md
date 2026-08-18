时间 $ t $(单位：s)的函数关系为 $ h(t)=\frac{1}{16}t^{3}+\frac{1}{8}t^{2} $，当 $ t=t_{0} $时，液体上升高度的瞬时变化率为 $ \frac{1}{4} $cm/s，则当 $ t=t_{0}+\frac{10}{3} $时，液体上升高度的瞬时变化率为（ ）

A. 2cm/s B. 4cm/s C. 6cm/s D. 8cm/s

解析：已知 $ t=t_0 $时的瞬时变化率，又有 $ h(t) $的瞬时变化率，故可用导数定义求 $ h(t) $在 $ t=t_0 $时的瞬时变化率，从而建立方程求出 $ t_0 $，再求 $ t=t_0+\frac{10}{3} $时的瞬时变化率，

由题意， $ h(t) $在 $ t=t_0 $时的瞬时变化率为 $ \lim_{\Delta t\to0}\frac{h(t_0+\Delta t)-h(t_0)}{\Delta t}=\lim_{\Delta t\to0}\frac{\frac{1}{16}(t_0+\Delta t)^3+\frac{1}{8}(t_0+\Delta t)^2-\left(\frac{1}{16}t_0^3+\frac{1}{8}t_0^2\right)}{\Delta t} $

 $ =\lim_{\Delta t\to0}\frac{\frac{1}{16}[t_0^3+3t_0^2\Delta t+3t_0(\Delta t)^2+(\Delta t)^3]+\frac{1}{8}[t_0^2+2t_0\Delta t+(\Delta t)^2]-\left(\frac{1}{16}t_0^3+\frac{1}{8}t_0^2\right)}{\Delta t} $

 $ =\lim_{\Delta t\to0}\frac{\frac{3}{16}t_0^2\Delta t+\frac{3}{16}t_0(\Delta t)^2+\frac{1}{16}(\Delta t)^3+\frac{1}{4}t_0\Delta t+\frac{1}{8}(\Delta t)^2}{\Delta t}=\lim_{\Delta t\to0}\left[\frac{3}{16}t_0^2+\frac{3}{16}t_0\Delta t+\frac{1}{16}(\Delta t)^2+\frac{1}{4}t_0+\frac{1}{8}\Delta t\right]=\frac{3}{16}t_0^2+\frac{1}{4}t_0 $ ①，

由题意， $ \frac{3}{16}t_0^2+\frac{1}{4}t_0=\frac{1}{4} $，解得： $ t_0=\frac{2}{3} $或-2（舍去），所以 $ t_0+\frac{10}{3}=\frac{2}{3}+\frac{10}{3}=4 $，

还要再用定义求 $ h(t) $在 $ t_0+\frac{10}{3} $处的瞬时变化率吗？不用，已有式①，意味着已经获得了 $ h(t) $在 $ t=t_0 $处的瞬时变化率，于是取 $ t_0=4 $，即可得到 $ h(t) $在 $ t=4 $处的瞬时变化率，

在①中取 $ t_0=4 $得当 $ t=t_0+\frac{10}{3} $时，液体上升高度的瞬时变化率为 $ \frac{3}{16}\times4^2+\frac{1}{4}\times4=4 $ cm/s。

答案：B

## 类型Ⅱ：导数定义式的应用

【例 8】若函数  $ y = f(x) $ 在  $ x = x_{0} $ 处可导，则  $ \lim_{\Delta x \to 0} \frac{f(x_{0} - 3\Delta x) - f(x_{0})}{\Delta x} = (\quad) $

A.  $ f'(x_{0}) $ B.  $ -f'(x_{0}) $ C.  $ 3f'(x_{0}) $ D.  $ -3f'(x_{0}) $

解析：分子中是 $ -3\Delta x $，分母是 $ \Delta x $，这与导数定义中的结构不一致，故考虑将其调整为一致，如何调整？把分母的 $ \Delta x $化为 $ -\frac{1}{3}\times(-3\Delta x) $即可， $ \lim_{\Delta x\to0}\frac{f(x_0-3\Delta x)-f(x_0)}{\Delta x}=\lim_{\Delta x\to0}\frac{f(x_0-3\Delta x)-f(x_0)}{-\frac{1}{3}\times(-3\Delta x)} $

= $ \lim_{\Delta x\to0}\left[(-3)\cdot\frac{f[x_0+(-3\Delta x)]-f(x_0)}{-3\Delta x}\right]=-3\lim_{\Delta x\to0}\frac{f[x_0+(-3\Delta x)]-f(x_0)}{-3\Delta x} $ ①，

式①中的 $ \lim_{\Delta x\to0}\frac{f[x_0+(-3\Delta x)]-f(x_0)}{-3\Delta x} $表示什么？若看不出来，可将 $ -3\Delta x $换元，再作观察，

令 $ \Delta t=-3\Delta x $，则当 $ \Delta x\to0 $时， $ \Delta t\to0 $，所以 $ \lim_{\Delta x\to0}\frac{f[x_0+(-3\Delta x)]-f(x_0)}{-3\Delta x}=\lim_{\Delta x\to0}\frac{f(x_0+\Delta t)-f(x_0)}{\Delta t}=f'(x_0) $，

代入①得 $ \lim_{\Delta x\to0}\frac{f(x_0-3\Delta x)-f(x_0)}{\Delta x}=-3f'(x_0) $。

答案：D

【反思】导数的定义  $ f'(x_0) = \lim_{\Delta x \to 0} \frac{\Delta y}{\Delta x} = \lim_{\Delta x \to 0} \frac{f(x_0 + \Delta x) - f(x_0)}{\Delta x} $ 中，对  $ \Delta x $ 的理解需注意两点：①分子和分母的  $ \Delta x $ 形式上要保持一致，因为分母表示的是“自变量的改变量”，也就是分子中两个  $ f(\cdots) $ 括号内的差；②  $ \Delta x $ 表示一