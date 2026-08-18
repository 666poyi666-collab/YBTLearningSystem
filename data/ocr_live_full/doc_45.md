解析：求点  $ A $ 到直线  $ l $ 的距离，考虑代公式  $ d = \sqrt{AB}^2 - (AB \cdot u)^2 $，下面先求直线  $ l $ 的单位方向向量  $ \boldsymbol{u} $，由题意， $ \overrightarrow{BC} = (0, 1, 1) $，所以直线  $ l $ 的一个单位方向量为  $ \boldsymbol{u} = \frac{\overrightarrow{BC}}{\left|\overrightarrow{BC}\right|} = \frac{\overrightarrow{BC}}{\sqrt{0^2 + 1^2 + 1^2}} = \frac{\overrightarrow{BC}}{\sqrt{2}} = \left(0, \frac{\sqrt{2}}{2}, \frac{\sqrt{2}}{2}\right) $，又因为  $ \overrightarrow{AB} = (-1, -1, -1) $，所以由点到直线的距离公式，点  $ A $ 到直线  $ l $ 的距离  $ d = \sqrt{AB^2 - (\overrightarrow{AB} \cdot \boldsymbol{u})^2} = \sqrt{(-1)^2 + (-1)^2 + (-1)^2} - \left[-1 \times 0 + (-1) \times \frac{\sqrt{2}}{2} + (-1) \times \frac{\sqrt{2}}{2}\right]^2} = 1 $。

答案：1

【反思】设  $ A $ 为直线  $ l $ 外一点， $ B $ 为直线  $ l $ 上任意一点， $ u $ 为直线  $ l $ 的一个单位方向向量，则点  $ A $ 到直线  $ l $ 的距离  $ d = \sqrt{AB}^2 - (\overrightarrow{AB} \cdot u)^2 $。

【例 19】如图，在三棱锥  $ P-ABC $ 中， $ PA \perp $ 底面  $ ABC $， $ \angle BAC = 90^\circ $。点  $ D $， $ E $， $ N $ 分别为棱  $ PA $， $ PC $， $ BC $ 的中点， $ M $ 是线段  $ AD $ 的中点， $ PA = AC = 2 $， $ AB = 1 $。

（1）求证：MN//平面BDE；

（2）求点N到直线ME的距离.

<div style="text-align: center;"><img src="imgs/img_in_image_box_882_521_1093_717.jpg" alt="Image" width="17%" /></div>


解：（1）证法1：（若用几何法证线面平行，需先找线线平行，怎么找？若无思路，可尝试逆推，假设$MN//$平面$BDE$，则经过直线$MN$的某平面与平面$BDE$相交，交线应与$MN$平行，观察发现$MN$和点$P$位于平面$BDE$的两侧，平面$PMN$与平面$BDE$的交线容易作出，于是先作出该交线，它就是我们要找的与$MN$平行的直线）如图，连接$PN$交$BE$于点$G$，连接$DG$，因为$E$，$N$分别为$PC$，$BC$的中点，所以$G$为$\triangle PBC$的重心，故$\frac{PG}{PN}=\frac{2}{3}$，又由题意，$PD=\frac{1}{2}PA=1$，$PM=\frac{3}{4}PA=\frac{3}{2}$，所以$\frac{PD}{PM}=\frac{2}{3}=\frac{PG}{PN}$，故$DG\parallel MN$，结合$DG\subset$平面$BDE$，$MN\not\subset$平面$BDE$可得$MN//$平面$BDE$。

证法2：（三棱锥中本身就有三条两两垂直的直线，故也可考虑建立坐标系，用向量法证 $MN \parallel$ 平面 $BDE$）

以 $A$ 为原点建立如图所示的空间直角坐标系，则 $M\left(0,0,\frac{1}{2}\right)$，$N\left(\frac{1}{2},1,0\right)$，$B(1,0,0)$，$D(0,0,1)$，$E(0,1,1)$，

所以 $\overrightarrow{MN}=\left(\frac{1}{2},1,-\frac{1}{2}\right)$，$\overrightarrow{BD}=(-1,0,1)$，$\overrightarrow{DE}=(0,1,0)$，设平面 $BDE$ 的法向量为 $\boldsymbol{m}=(x,y,z)$，

则 $\begin{cases}\boldsymbol{m}\cdot\overrightarrow{BD}=-x+z=0\\ \boldsymbol{m}\cdot\overrightarrow{DE}=y=0\end{cases}$，令 $x=1$，则 $y=0$，$z=1$，所以 $\boldsymbol{m}=(1,0,1)$ 是平面 $BDE$ 的一个法向量，

因为 $\overrightarrow{MN}\cdot\boldsymbol{m}=\frac{1}{2}\times1+1\times0+\left(-\frac{1}{2}\right)\times1=0$，所以 $\overrightarrow{MN}\perp\boldsymbol{m}$，又 $MN\not\subset$ 平面 $BDE$，所以 $MN\parallel$ 平面 $BDE$。

（2）（求点 $N$ 到直线 $ME$ 的距离，考虑代公式 $d=\sqrt{MN}^2-(\overrightarrow{MN}\cdot\boldsymbol{u})^2$，下面先求直线 $ME$ 的单位方向向量 $\boldsymbol{u}$）

由（1）可得 $\overrightarrow{ME}=\left(0,1,\frac{1}{2}\right)$，所以直线 $ME$ 的一个单位方向向量为



 $$ \boldsymbol{u}=\frac{\overrightarrow{ME}}{\left|\overrightarrow{ME}\right|}=\frac{\overrightarrow{ME}}{\sqrt{1^{2}+\left(\frac{1}{2}\right)^{2}}}=\frac{2}{\sqrt{5}}\overrightarrow{ME}=\left(0,\frac{2}{\sqrt{5}},\frac{1}{\sqrt{5}}\right), $$ 

由点到直线的距离公式，点 $N$ 到直线 $ME$ 的距离 $d = \sqrt{\overrightarrow{MN}^2 - (\overrightarrow{MN} \cdot \boldsymbol{u})^2}$

<div style="text-align: center;"><img src="imgs/img_in_image_box_843_1341_1092_1553.jpg" alt="Image" width="20%" /></div>
