ABCD 是菱形， $ \triangle PAD $ 是正三角形， $ \angle ABC = \frac{2\pi}{3} $，E 是 AB 的中点.

（1）证明： $ AC \perp PE $；

（2）求平面 ACE 与平面 PCE 的夹角的余弦值.

解：（1）证法1：（证线线垂直，需找线面垂直，若无思路，可尝试逆推．假设AC⊥PE，若能再找一个与AC或PE有关的线线垂直与之组合，就能得到线面垂直，找谁呢？看到面PAD⊥面ABCD，想到最常见的辅助线：过P作AD的垂线PO，得到PO⊥底面ABCD，于是PO⊥该面内所有直线，哪条有用呢？显然是AC，故可通过证AC⊥面POE来证本题的结论）

如图，取  $ AD $ 中点  $ O $，连接  $ PO $， $ OE $， $ BD $，因为  $ \triangle PAD $ 是正三角形， $ O $ 是  $ AD $ 的中点，所以  $ PO \perp AD $，因为平面  $ PAD \perp $ 平面  $ ABCD $，且平面  $ PAD \cap $ 平面  $ ABCD = AD $， $ PO \subset $ 平面  $ PAD $，所以  $ PO \perp $ 平面  $ ABCD $，因为  $ AC \subset $ 平面  $ ABCD $，所以  $ AC \perp PO $ ①，

因为  $ ABCD $ 是菱形，所以  $ AC \perp BD $，又因为  $ O $， $ E $ 分别为  $ AD $， $ AB $ 的中点，所以  $ OE \parallel BD $，故  $ AC \perp OE $，结合①以及  $ PO $， $ OE \subset $ 平面  $ POE $， $ PO \cap OE = O $ 可得  $ AC \perp $ 平面  $ POE $，因为  $ PE \subset $ 平面  $ POE $，所以  $ AC \perp PE $。

证法2：（由题设条件容易找到三条两两垂直的直线，故也可建系，通过证明  $ \overrightarrow{AC} \cdot \overrightarrow{PE} = 0 $ 来证  $ AC \perp PE $）

证明  $ PO \perp $ 平面  $ ABCD $ 的过程同证法1，此处不再赘述，因为  $ ABCD $ 是菱形，所以  $ AB = AD $，

又  $ \angle ABC = \frac{2\pi}{3} $，所以  $ \angle BAD = \frac{\pi}{3} $，从而  $ \triangle ABD $ 是正三角形，故  $ OB \perp AD $，

以 $O$ 为原点建立如图所示的空间直角坐标系，不妨设 $AD=4$，则 $OA=OD=2$，$OP=OB=2\sqrt{3}$，所以 $A(2,0,0)$，$C(-4,2\sqrt{3},0)$，$P(0,0,2\sqrt{3})$，$E(1,\sqrt{3},0)$，从而 $\overrightarrow{AC}=(-6,2\sqrt{3},0)$，$\overrightarrow{PE}=(1,\sqrt{3},-2\sqrt{3})$，故 $\overrightarrow{AC}\cdot\overrightarrow{PE}=-6\times1+2\sqrt{3}\times\sqrt{3}+0\times(-2\sqrt{3})=0$，所以 $\overrightarrow{AC}\perp\overrightarrow{PE}$，故 $AC\perp PE$。

（2）（求二面角可用向量法，需要先求两个平面的法向量，我们沿用第（1）问证法2建立的坐标系，观察图形可发现平面ACE的法向量可直接获得，故只需求平面PCE的法向量）

由（1）可得  $ \overrightarrow{PE}=(1,\sqrt{3},-2\sqrt{3}) $， $ \overrightarrow{CE}=(5,-\sqrt{3},0) $，

由 (1) 可得  $ PE = (1, \sqrt{3}, -2\sqrt{3}) $， $ CE = (5, -\sqrt{3}, 0) $，

设平面 PCE 的法向量为  $ \boldsymbol{m} = (x, y, z) $，则  $ \begin{cases} \boldsymbol{m} \cdot \overrightarrow{PE} = x + \sqrt{3}y - 2\sqrt{3}z = 0 \\ \boldsymbol{m} \cdot \overrightarrow{CE} = 5x - \sqrt{3}y = 0 \end{cases} $，

令  $ x = \sqrt{3} $，则  $ \begin{cases} y = 5 \\ z = 3 \end{cases} $，所以  $ \boldsymbol{m} = (\sqrt{3}, 5, 3) $ 是平面 PCE 的一个法向量，

由图可知， $ \boldsymbol{n} = (0, 0, 1) $ 是平面 ACE 的一个法向量，

设平面 ACE 与平面 PCE 的夹角为  $ \theta $，则  $ \cos\theta = |\cos\langle \boldsymbol{m}, \boldsymbol{n} \rangle| = \frac{|\boldsymbol{m} \cdot \boldsymbol{n}|}{|\boldsymbol{m}| \cdot |\boldsymbol{n}|} = \frac{3\sqrt{37}}{37} $，

所以平面 ACE 与平面 PCE 的夹角的余弦值为  $ \frac{3\sqrt{37}}{37} $。

<div style="text-align: center;"><img src="imgs/img_in_image_box_833_948_1093_1146.jpg" alt="Image" width="21%" /></div>


所以平面 ACE 与平面 PCE 的夹角的余弦值为  $ \frac{3\sqrt{37}}{37} $.

【反思】①不平行的平面 $ \alpha $与平面 $ \beta $的夹角 $ \theta\in\left(0,\frac{\pi}{2}\right] $，要求其余弦值，可先求出两个平面的法向量 $ m,n $，再按 $ \cos\theta=\left|\cos\langle m,n\rangle\right| $求 $ \alpha $与 $ \beta $的夹角余弦；

②对于二面角  $ \alpha-l-\beta $，其大小的取值范围是  $ [0,\pi] $，且它与  $ \alpha $， $ \beta $ 的夹角  $ \theta $ 要么相等，要么互补，故若是让求二面角  $ \alpha-l-\beta $ 的余弦值，则我们常先求  $ \cos <m,n> $，再结合图形观察二面角  $ \alpha-l-\beta $ 的锐钝，决定该取正还是取负。比如下面的变式 1：

③若由图不易看出二面角 $ \alpha-l-\beta $的锐钝，还可通过法向量的指向来判断法向量的夹角与二面角 $ \alpha-l-\beta $的大小关系。如图1，若两个法向量一个朝内，一个朝外，则它们的夹角等于二面角 $ \alpha-l-\beta $；如图2，若两个法向量均朝内（或均朝外），则它们的夹角等于二面角 $ \alpha-l-\beta $的补角，比如后面的变式2.