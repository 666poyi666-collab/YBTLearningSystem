2. 利用向量方法解决立体几何中的求距离问题

①点到直线的距离

①点到直线的距离

如图，$\overrightarrow{AP}$ 在直线 $l$ 上的投影向量为 $\overrightarrow{AQ}$，则 $\triangle APQ$ 为直角三角形，直线 $l$ 的方向向量为 $\boldsymbol{a}$，单位方向向量为 $\boldsymbol{u}$，则向量 $\overrightarrow{AP}$ 在直线 $l$ 上的投影向量为 $\overrightarrow{AQ} = \frac{\boldsymbol{a} \cdot \overrightarrow{AP}}{|\boldsymbol{a}|^2} \boldsymbol{a}$，所以

$\left|\overrightarrow{AQ}\right|^2 = \left(\frac{\boldsymbol{a} \cdot \overrightarrow{AP}}{|\boldsymbol{a}|^2} \boldsymbol{a}\right)^2 = \frac{(\boldsymbol{a} \cdot \overrightarrow{AP})^2}{|\boldsymbol{a}|^4} \left|\boldsymbol{a}^2\right| = \left(\frac{\boldsymbol{a} \cdot \overrightarrow{AP}}{|\boldsymbol{a}|}\right)^2 = \left(\frac{\boldsymbol{a}}{|\boldsymbol{a}|} \cdot \overrightarrow{AP}\right)^2$

$= (\boldsymbol{u} \cdot \overrightarrow{AP})^2$，由勾股定理可得点 $P$ 到直线 $l$ 的距离 $d = PQ$

$= \sqrt{|\overrightarrow{AP}|^2 - |\overrightarrow{AQ}|^2} = \sqrt{\overrightarrow{AP}^2 - (\boldsymbol{u} \cdot \overrightarrow{AP})^2}$。

<div style="text-align: center;"><img src="imgs/img_in_image_box_302_679_515_797.jpg" alt="Image" width="17%" /></div>


②点到平面的距离

如图，设平面$\alpha$的法向量为$\boldsymbol{n}$，$A$是平面$\alpha$内的任意一点，$P$是平面$\alpha$外一点，过点$P$作平面$\alpha$的垂线交平面$\alpha$于点$Q$，则$\boldsymbol{n}$是直线$PQ$的方向向量，且点$P$到平面$\alpha$的距离就是$\overrightarrow{AP}$在直线$PQ$上的投影向量的长度，该投影向量为$\frac{\overrightarrow{AP}\cdot\boldsymbol{n}}{|\boldsymbol{n}|^2}\boldsymbol{n}$，故$P$到$\alpha$的距离$d=\left|\frac{\overrightarrow{AP}\cdot\boldsymbol{n}}{|\boldsymbol{n}|^2}\boldsymbol{n}\right|=\frac{\left|\overrightarrow{AP}\cdot\boldsymbol{n}\right|}{|\boldsymbol{n}|}$。

<div style="text-align: center;"><img src="imgs/img_in_image_box_299_1172_517_1278.jpg" alt="Image" width="18%" /></div>


③直线到平面、平面到平面的距离

若直线与平面平行，平面与平面平行，则直线到平面、平面到平面的距离可转化为点到平面的距离来计算.

3. 利用向量方法求立体几何中的空间角

①异面直线所成角

【例7】若平面 $ \alpha $的一个法向量为 $ \boldsymbol{n}=(1,2,1) $，已知 $ \overrightarrow{AB}=(-1,-1,2) $， $ A \notin \alpha $， $ B \in \alpha $，则点 $ A $到平面 $ \alpha $的距离为（ ）

A. 1 \quad B.  $ \frac{\sqrt{6}}{6} $

C.  $ \frac{\sqrt{3}}{3} $ \quad D.  $ \frac{\sqrt{2}}{3} $

答案：C

解析：求点到平面的距离，可代知识点3第2点②的公式计算，这里已有 $ \alpha $的法向量 $ n $和 $ \overrightarrow{AB} $的坐标，可直接代公式，

由题意，点 $ A $到平面 $ \alpha $的距离 $ d=\frac{|\overrightarrow{BA}\cdot\boldsymbol{n}|}{|\boldsymbol{n}|} $

 $ =\frac{|\overrightarrow{AB}\cdot\boldsymbol{n}|}{|\boldsymbol{n}|}=\frac{|-1\times1+(-1)\times2+2\times1|}{\sqrt{1^2+2^2+1^2}}=\frac{\sqrt{6}}{6} $.

答案：B

【例8】已知直线 $l$ 的一个方向向量为 $\boldsymbol{m}=(1,1,0)$，平面 $\alpha$ 的一个法向量为 $\boldsymbol{n}=(0,-\sqrt{2},\sqrt{2})$，则直线 $l$ 与平面 $\alpha$ 所成的角为（ ）

A. $\frac{\pi}{6}$  B. $\frac{\pi}{4}$  

C. $\frac{\pi}{6}$ 或 $\frac{5\pi}{6}$  D. $\frac{\pi}{4}$ 或 $\frac{3\pi}{4}$

解析：设直线 $l$ 与平面 $\alpha$ 所成角为 $\theta$，其中 $0 \leq \theta \leq \frac{\pi}{2}$，则 $\sin \theta = |\cos < m, n>| = \frac{|m \cdot n|}{|m| \cdot |n|}$

$= \frac{|1 \times 0 + 1 \times (-\sqrt{2}) + 0 \times \sqrt{2}|}{\sqrt{1^2 + 1^2 + 0^2} \cdot \sqrt{0^2 + (-\sqrt{2})^2 + (\sqrt{2})^2}}$

$= \frac{1}{2}$，结合 $0 \leq \theta \leq \frac{\pi}{2}$ 可得 $\theta = \frac{\pi}{6}$。

答案：A

答案：A

【例9】在空间直角坐标系中，已知平面 $ \alpha $， $ \beta $的一个法向量分别为 $ m= $