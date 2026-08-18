从而  $ a^{4}-5a^{2}c^{2}=0 $，故  $ a^{2}=5c^{2}\Rightarrow $ 椭圆 C 的离心率  $ e=\frac{c}{a}=\frac{\sqrt{5}}{5} $.

解法4：注意到$\angle F_1BF_2$的大小可以反映椭圆的离心率，故也可考虑先求$\angle F_1BF_2$，再求离心率，

因为$\overrightarrow{AF_2} \cdot \overrightarrow{BF_2} = 0$，所以$AF_2 \perp BF_2$，设$\angle F_1BF_2 = 2\theta$，则$\angle OBF_1 = \angle OBF_2 = \theta$，注意到$|BF_1| = |BF_2| = a$，故可在$\triangle ABF_2$中求出$|AF_2|$和$|AB|$，再求出$|AF_1|$，全部用$\theta$表示，根据椭圆定义建立$\theta$的方程，

由图1可知，$|AF_2| = |BF_2| \cdot \tan 2\theta = a \tan 2\theta$，$|AB| = \frac{|BF_2|}{\cos 2\theta} = \frac{a}{\cos 2\theta}$，所以$|AF_1| = |AB| - |BF_1| = \frac{a}{\cos 2\theta} - a$，

由椭圆定义，$|AF_1| + |AF_2| = 2a$，所以$\frac{a}{\cos 2\theta} - a + a \tan 2\theta = 2a$，故$\tan 2\theta + \frac{1}{\cos 2\theta} = 3$，

又$\tan 2\theta + \frac{1}{\cos 2\theta} = \frac{\sin 2\theta + 1}{\cos 2\theta} = \frac{(\sin \theta + \cos \theta)^2}{(\cos \theta + \sin \theta)(\cos \theta - \sin \theta)} = \frac{\sin \theta + \cos \theta}{\cos \theta - \sin \theta} = \frac{\tan \theta + 1}{1 - \tan \theta}$，所以$\frac{\tan \theta + 1}{1 - \tan \theta} = 3$，

解得：$\tan \theta = \frac{1}{2}$，另一方面，$\tan \theta = \frac{|OF_2|}{|OB|} = \frac{c}{b}$，所以$\frac{c}{b} = \frac{1}{2}$，从而$2c = b$，故$4c^2 = b^2 = a^2 - c^2$，

化简得椭圆$C$的离心率$e = \frac{c}{a} = \frac{\sqrt{5}}{5}$。

答案：$\frac{\sqrt{5}}{5}$

【变式5】已知 $ F_{1} $， $ F_{2} $是椭圆 $ \frac{x^{2}}{a^{2}}+\frac{y^{2}}{b^{2}}=1(a>b>0) $的左、右焦点，P是椭圆上任意一点，过 $ F_{1} $作 $ \angle F_{1}PF_{2} $的外角平分线的垂线，垂足为Q，若Q与短轴端点的最短距离为 $ \frac{c}{2} $，则椭圆的离心率为（ ）

A. $ \frac{2}{3} $ B. $ \frac{3}{4} $ C. $ \frac{4}{5} $ D. $ \frac{5}{6} $

解析：如图1，P在椭圆上运动时，Q跟着一起动，故翻译“Q与短轴端点的最短距离为 $ \frac{c}{2} $”这一条件前，应先找Q的轨迹，怎么找？题干涉及角平分线和垂线，想到三线合一，故按此添加辅助线，分析几何特征，如图1，延长 $ F_1Q $交直线 $ PF_2 $于点M，由题意，PQ是 $ \angle F_1PM $的角平分线，且 $ PQ\perp QF_1 $，所以 $ |PM|=|PF_1| $，且Q为 $ MF_1 $的中点，涉及中点，又可联想到中位线，这里O天然是 $ F_1F_2 $的中点，容易构造中位线，因为O为 $ F_1F_2 $的中点，所以 $ |OQ|=\frac{1}{2}|MF_2| $，又因为 $ |MF_2|=|PF_2|+|PM|=|PF_2|+|PF_1|=2a $，所以 $ |OQ|=a $，故点Q的轨迹是圆心为原点O，半径r=a的圆，如图2，短轴端点 $ B_1 $， $ B_2 $都在圆O内部，由对称性，圆O上的点Q到 $ B_1 $， $ B_2 $的最短距离都为r-b=a-b，结合题意可知a-b= $ \frac{c}{2} $①，关于a，b，c的齐次方程有了，求离心率需找c与a的比值，故考虑消去上式中的b，由①可得 $ a-\frac{c}{2}=b $，所以 $ \left(a-\frac{c}{2}\right)^2=b^2=a^2-c^2 $，故 $ a^2-ac+\frac{c^2}{4}=a^2-c^2 $，化简得椭圆的离心率 $ e=\frac{c}{a}=\frac{4}{5} $。