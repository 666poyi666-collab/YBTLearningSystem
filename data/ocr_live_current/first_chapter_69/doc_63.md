B 项， $ \overrightarrow{AB}=\left(\frac{\sqrt{3}}{3},-\frac{\sqrt{6}}{3}\cos\theta,-\frac{\sqrt{6}}{3}\sin\theta\right) $， $ \overrightarrow{CD}=\left(-\frac{\sqrt{3}}{3},-\frac{\sqrt{6}}{3},0\right) $，所以  $ \overrightarrow{AB}\cdot\overrightarrow{CD}=\frac{2\cos\theta-1}{3} $，

从而当  $ \theta=60^\circ $ 时， $ \overrightarrow{AB}\cdot\overrightarrow{CD}=0 $，此时  $ AB\perp CD $，故 B 项正确；

C 项， $ \overrightarrow{AD}=\left(-\frac{2\sqrt{3}}{3},-\frac{\sqrt{6}}{3}\cos\theta,-\frac{\sqrt{6}}{3}\sin\theta\right) $， $ \overrightarrow{BC}=\left(-\frac{2\sqrt{3}}{3},\frac{\sqrt{6}}{3},0\right) $，所以  $ \overrightarrow{AD}\cdot\overrightarrow{BC}=\frac{2(2-\cos\theta)}{3}>0 $，

从而直线  $ AD $ 与直线  $ BC $ 始终不垂直，故 C 项错误；

D 项，由前面的分析过程可知 D 项错误，故选 B.

答案：B

【反思】作出二面角的平面角，并将其设为变量，再以该角的顶点为原点建系，从而把动点坐标表示成关于所设变量的三角形式，参与后续运算，这是动态二面角问题的常用处理方法，此法大题小题都能用，我们再来看一个例题.

【例 7】正方形 ABCD 的边长为 2，E，F 分别为边 AD，BC 的中点，M 为线段 EF 的中点，将正方形 ABCD 沿 EF 折起，得到如图所示的二面角 A-EF-D.

（1）直线 AM 与平面 BCF 相交于点 O，试确定点 O 的位置，并证明 OC∥平面 BDM;



（2）若平面 BDM 与平面 BCM 所成的锐二面角的余弦值为  $ \frac{1}{3} $，求二面

<div style="text-align: center;"><img src="imgs/img_in_image_box_843_601_1092_758.jpg" alt="Image" width="20%" /></div>


角 A-EF-D 的大小.

解：（1）（观察发现 AM 和 BF 是平面 ABFE 内的相交直线，故它们的交点就是直线 AM 与平面 BCF 的交点，于是把 AM 和 BF 延长，再作分析）如图，延长 AM 和 BF 交于点 O，则点 O 即为直线 AM 与平面 BCF 的交点，由题意，MF∥AB，且 AB = 2MF，所以 MF 是 △OAB 的中位线，故 OF = BF = 1，OM = AM，

（怎样证 OC∥平面 BDM？证线面平行，先找线线平行，怎么找？若无思路，可尝试逆推。假设 OC∥平面 BDM，则如图，由线面平行的性质定理，OC∥GM，故可通过证明 OC∥GM 来证 OC∥平面 BDM，已有 M 为 OA 的中点，于是只需证 G 为 AC 的中点）因为折叠前 E，F 分别是 AD，BC 的中点，所以 AB，EF，CD 平行且相等，折叠后，AB∥EF 且 AB = EF，CD∥EF 且 CD = EF，所以 AB∥CD 且 AB = CD，故四边形 ABCD 是平行四边形，连接 AC 交 BD 于点 G，则 G 为 AC 中点，又 M 是 OA 中点，所以 GM∥OC，中点可知 OC⊂平面 BDM，GM = 平面 BDM，所以 OC∥平面 BDM。

又 M 是 OA 中点，所以 GM∥OC，由图可知 OC ⊂ 平面 BDM，GM ⊂ 平面 BDM，所以 OC∥平面 BDM.

（2）（观察发现 ∠AED 是二面角 A−EF−D 的平面角，只要设出该角，就能方便地以 E 为原点建系，写出有关点的坐标，故按此处理，用向量法翻译条件所给的锐二面角的余弦值，建立方程求所设二面角的大小）

由题意可知，EF ⊥ AE，EF ⊥ DE，所以 ∠AED 是二面角 A−EF−D 的平面角，

以 $E$ 为原点建立如图所示的空间直角坐标系，设 $\angle AED = \theta (0 < \theta < \pi)$，则 $D(\cos \theta, 0, \sin \theta)$，$M(0, 1, 0)$，$B(1, 2, 0)$，$C(\cos \theta, 2, \sin \theta)$，所以 $\overrightarrow{MD} = (\cos \theta, -1, \sin \theta)$，$\overrightarrow{MB} = (1, 1, 0)$，$\overrightarrow{MC} = (\cos \theta, 1, \sin \theta)$，

 $$ \boldsymbol{m}=(x_{1},y_{1},z_{1}) $$ 

 $$ \boldsymbol{n}=(x_{2},y_{2},z_{2}) $$ 

则$\begin{cases} \boldsymbol{m} \cdot \overrightarrow{MD} = x_1 \cos \theta - y_1 + z_1 \sin \theta = 0 \textcircled{1} \\ \boldsymbol{m} \cdot \overrightarrow{MB} = x_1 + y_1 = 0 \textcircled{2} \end{cases}$，（怎样由此求 $m$ 的坐标？由式②不妨先令 $x_1 = 1$，则 $y_1 = -1$，代入①得 $z_1 = \frac{-\cos \theta - 1}{\sin \theta}$，于是 $m = \left(1, -1, \frac{-\cos \theta - 1}{\sin \theta}\right)$，为了后续计算方便，我们将各分量同时乘以 $\sin \theta$，去掉分母）令 $x_1 = \sin \theta$，则 $y_1 = -\sin \theta$，$z_1 = -\cos \theta - 1$，所以 $m = (\sin \theta, -\sin \theta, -\cos \theta - 1)$ 是平面 $BDM$ 的一个法向量，