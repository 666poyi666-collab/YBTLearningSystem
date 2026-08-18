在$\triangle PAF_2$中，由余弦定理推论，$\cos\angle PAF_2=\frac{|PA|^2+|F_2A|^2-|PF_2|^2}{2|PA|\cdot|F_2A|}=\frac{|PA|^2+\left(\frac{3}{4}\right)^2-\left(\frac{3}{2}\right)^2}{2|PA|\cdot\frac{3}{4}}=\frac{16|PA|^2-27}{24|PA|}$，因为$\angle PAF_1=\pi-\angle PAF_2$，所以$\cos\angle PAF_1=\cos(\pi-\angle PAF_2)=-\cos\angle PAF_2$，故$\frac{16|PA|^2-75}{40|PA|}=-\frac{16|PA|^2-27}{24|PA|}$，解得：$|PA|=\frac{3\sqrt{5}}{4}$。

解法2：按解法1求得 $ |PF_1|=\frac{5}{2} $， $ |PF_2|=\frac{3}{2} $后，观察发现 $ \frac{|PF_2|}{|PF_1|}=\frac{3}{5}=\cos\angle F_1PF_2 $，于是 $ PF_2\perp F_1F_2 $，故可先由所给的 $ \cos\angle F_1PF_2 $求出 $ \cos\angle APF_2 $，再到 $ \mathrm{Rt}\triangle PAF_2 $中求 $ |PA| $，

设 $ \angle F_1PF_2=2\alpha $，则 $ \angle APF_2=\alpha $，且 $ \cos2\alpha=\frac{3}{5}=2\cos^2\alpha-1\Rightarrow\cos\alpha=\frac{2\sqrt{5}}{5} $，所以 $ |PA|=\frac{|PF_2|}{\cos\alpha}=\frac{\frac{3}{2}}{\frac{2\sqrt{5}}{5}}=\frac{3\sqrt{5}}{4} $。

答案：D

## 补充、拓展

当点在椭圆上运动时，可以衍生出一些有关的最值问题，这类问题按解决方法不同，主要有两类，本节我们先给大家拓展基于椭圆定义的这一类最值问题，还有一类基于椭圆方程的最值问题，因为要用到椭圆中变量 x，y 的范围，我们下一节再涉及.

类型VI：基于椭圆定义的最值问题

【例 14】已知  $ F_1 $， $ F_2 $ 是椭圆  $ C: \frac{x^2}{9} + \frac{y^2}{4} = 1 $ 的两个焦点，点  $ M $ 在  $ C $ 上，则  $ \frac{1}{|MF_1|} + \frac{1}{|MF_2|} $ 的最小值为___.

解析：由椭圆的定义知$|MF_1| + |MF_2|$为定值，目标是求$\frac{1}{|MF_1|} + \frac{1}{|MF_2|}$的最小值，若把$|MF_1|$看成$x$，把$|MF_2|$看成$y$，则问题即为在$x+y$为定值的条件下求$\frac{1}{x} + \frac{1}{y}$的最小值，这是基本不等式中典型的“1”的代换模型，由所给椭圆方程，$a^2 = 9$，结合$a > 0$可知$a = 3$，所以$|MF_1| + |MF_2| = 2a = 6$，

故 $ \frac{1}{\left|MF_{1}\right|}+\frac{1}{\left|MF_{2}\right|}=\frac{1}{6}\left(\frac{1}{\left|MF_{1}\right|}+\frac{1}{\left|MF_{2}\right|}\right)\cdot6=\frac{1}{6}\left(\frac{1}{\left|MF_{1}\right|}+\frac{1}{\left|MF_{2}\right|}\right)\left(\left|MF_{1}\right|+\left|MF_{2}\right|\right)=\frac{1}{6}\left(1+\frac{\left|MF_{1}\right|}{\left|MF_{2}\right|}+\frac{\left|MF_{2}\right|}{\left|MF_{1}\right|}+1\right)=\frac{1}{6}\left(\frac{\left|MF_{1}\right|}{\left|MF_{2}\right|}+\frac{\left|MF_{2}\right|}{\left|MF_{1}\right|}+2\right)\geq\frac{1}{6}\left(2\sqrt{\frac{\left|MF_{1}\right|}{\left|MF_{2}\right|}\cdot\frac{\left|MF_{2}\right|}{\left|MF_{1}\right|}}+2\right)=\frac{2}{3} $，取等条件是 $ \frac{\left|MF_{1}\right|}{\left|MF_{2}\right|}=\frac{\left|MF_{2}\right|}{\left|MF_{1}\right|} $，即 $ \left|MF_{1}\right|=\left|MF_{2}\right| $，结合 $ \left|MF_{1}\right|+\left|MF_{2}\right|=6 $可得 $ \left|MF_{1}\right|=\left|MF_{2}\right|=3 $，所以 $ \frac{1}{\left|MF_{1}\right|}+\frac{1}{\left|MF_{2}\right|} $的最小值为 $ \frac{2}{3} $.

答案： $ \frac{2}{3} $

【反思】椭圆中天然有 $ |MF_1| + |MF_2| = 2a $（点  $ M $ 在椭圆上），所以遇到与 $ |MF_1| $， $ |MF_2| $ 有关的最值问题时，别忘了运用这一条件。本题求最值的过程采用的是基本不等式，还有一类题是需要结合几何特征分析的，我们来看下面的几道题。