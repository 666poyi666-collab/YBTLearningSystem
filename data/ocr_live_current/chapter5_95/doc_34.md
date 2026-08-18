则不等式  $ f(x)+2025\mathrm{e}^{x}<0 $ 的解集是（）

A.  $ (-\infty,0) $ B.  $ (0,+\infty) $ C.  $ \left(-\infty,\frac{1}{e}\right) $ D.  $ \left(\frac{1}{e},+\infty\right) $

解析：条件给出  $ f(x) > f'(x) $，移项可产生  $ f(x) - f'(x) $ 这一结构，联想到构造函数  $ y = \frac{f(x)}{\mathrm{e}^x} $ 来分析，

设  $ g(x) = \frac{f(x)}{\mathrm{e}^x} $， $ x \in \mathbf{R} $，则  $ g'(x) = \frac{f'(x)\mathrm{e}^x - \mathrm{e}^x f(x)}{(\mathrm{e}^x)^2} = \frac{f'(x) - f(x)}{\mathrm{e}^x} $，由题意， $ f(x) > f'(x) $，

所以  $ f'(x) - f(x) < 0 $，从而  $ g'(x) < 0 $，故  $ g(x) $ 在  $ \mathbf{R} $ 上  $ \searrow $，有  $ g(x) $ 的单调性，当然把要解的不等式往  $ g(x) $ 上化，

 $ f(x) + 2025\mathrm{e}^x < 0 \Leftrightarrow f(x) < -2025\mathrm{e}^x \Leftrightarrow \frac{f(x)}{\mathrm{e}^x} < -2025 \Leftrightarrow g(x) < -2025 $ ①，

若能将右边的 -2025 也化为  $ g(x) $ 在某处的函数值，就能用单调性处理了，怎么化？条件还给出  $ f(x) + 2025 $ 为奇函数，可联想到  $ f(0) + 2025 = 0 $，移项即可产生 -2025，故尝试由此出发分析，

因为  $ f(x) + 2025 $ 为奇函数，所以  $ f(0) + 2025 = 0 \Rightarrow f(0) = -2025 \Rightarrow \frac{f(0)}{\mathrm{e}^0} = -2025 \Rightarrow g(0) = -2025 $，

所以不等式①即为  $ g(x) < g(0) $，结合  $ g(x) $ 在  $ \mathbf{R} $ 上  $ \searrow $ 可得  $ x > 0 $，故所求不等式的解集为  $ (0, +\infty) $。

答案：B

【变式 2】（多选）已知函数  $ f(x) $ 对任意的  $ x \in \left(-\frac{\pi}{2}, \frac{\pi}{2}\right) $，满足  $ f'(x) \cos x + f(x) \sin x > 0 $，则下列不等式中成立的是（ ）

A.  $ \sqrt{2} f\left(-\frac{\pi}{3}\right) < f\left(-\frac{\pi}{4}\right) $

B.  $ \sqrt{2} f\left(\frac{\pi}{3}\right) < f\left(\frac{\pi}{4}\right) $

C.  $ f(0) < \sqrt{2} f\left(\frac{\pi}{4}\right) $

D.  $ f(0) > 2 f\left(\frac{\pi}{3}\right) $

解析：由  $ f'(x)\cos x + f(x)\sin x $ 这一结构联想到构造函数  $ y = \frac{f(x)}{\cos x} $ 来分析，设  $ g(x) = \frac{f(x)}{\cos x} $， $ x \in \left(-\frac{\pi}{2}, \frac{\pi}{2}\right) $，由题意， $ g'(x) = \frac{f'(x)\cos x - (-\sin x)f(x)}{\cos^2 x} = \frac{f'(x)\cos x + f(x)\sin x}{\cos^2 x} > 0 $，所以  $ g(x) $ 在  $ \left(-\frac{\pi}{2}, \frac{\pi}{2}\right) $ 上  $ \nearrow $，下面分析选项，以 A 项为例，涉及  $ f\left(-\frac{\pi}{3}\right) $ 和  $ f\left(-\frac{\pi}{4}\right) $，当然想到研究  $ g\left(-\frac{\pi}{3}\right) $ 和  $ g\left(-\frac{\pi}{4}\right) $ 的大小关系，A 项，因为  $ -\frac{\pi}{3} < -\frac{\pi}{4} $，所以  $ g\left(-\frac{\pi}{3}\right) < g\left(-\frac{\pi}{4}\right) $，即  $ \frac{f\left(-\frac{\pi}{3}\right)}{\cos\left(-\frac{\pi}{3}\right)} < \frac{f\left(-\frac{\pi}{4}\right)}{\cos\left(-\frac{\pi}{4}\right)} $，也即  $ 2f\left(-\frac{\pi}{3}\right) < \sqrt{2}f\left(-\frac{\pi}{4}\right) $，所以  $ \sqrt{2}f\left(-\frac{\pi}{3}\right) < f\left(-\frac{\pi}{4}\right) $，故 A 项正确；B 项，因为  $ \frac{\pi}{4} < \frac{\pi}{3} $，所以  $ g\left(\frac{\pi}{4}\right) < g\left(\frac{\pi}{3}\right) $，即  $ \frac{f\left(\frac{\pi}{4}\right)}{\cos\frac{\pi}{4}} < \frac{f\left(\frac{\pi}{3}\right)}{\cos\frac{\pi}{3}} $，也即  $ \sqrt{2}f\left(\frac{\pi}{4}\right) < 2f\left(\frac{\pi}{3}\right) $，所以  $ f\left(\frac{\pi}{4}\right) < \sqrt{2}f\left(\frac{\pi}{3}\right) $，故 B 项错误；