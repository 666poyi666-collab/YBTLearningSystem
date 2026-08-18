# 微专题1：立体几何综合题

习题：P1

# 内容提要

立体几何作为高中数学的重点板块之一，在各类考试中经常出现一些难度中等偏上或难度偏高的综合性考题，本节我们就通过一些细分题型来给大家梳理如何用空间向量求解这类考题。

## 典型例题

## 类型Ⅰ：利用空间向量解决线上动点问题

【例 1】如图，P 为圆锥的顶点，O 是圆锥底面的圆心，AC 为底面直径， $ \triangle ABD $ 为底面圆 O 的内接正三角形，且边长为  $ \sqrt{3} $，点 E 在母线 PC 上，且  $ AE = \sqrt{3} $，CE = 1。

（1）求证：直线PO∥平面BDE；

（2）求证：平面 $ BED \perp $平面 $ ABD $;

（3）已知 $M$ 为线段 $PO$ 上的一点，当直线 $DM$ 与平面 $ABE$ 所成角的正弦值为 $\frac{2\sqrt{7}}{7}$ 时，求点 $M$ 到平面 $ABE$ 的距离。

解：（1）(要证线面平行，先找线线平行，由图可猜想 $EF \parallel PO$（点 $F$ 的位置如下图所示），故尝试找设直线 $AC$ 与 $BD$ 交于点 $F$，连接 $EF$，由题意，$\triangle ABD$ 是边长为 $\sqrt{3}$ 的正三角形，$O$ 是其外心，所以 $F$ 是 $BD$ 的中点，且 $OA = \frac{2}{3}AF = \frac{2}{3} \times \frac{\sqrt{3}}{2} \times \sqrt{3} = 1$，$OF = \frac{1}{2}OA = \frac{1}{2}$，



<div style="text-align: center;"><img src="imgs/img_in_image_box_852_501_1092_742.jpg" alt="Image" width="20%" /></div>


所以 OC = 1，AC = 2，且 F 是 OC 的中点，又  $ AE = \sqrt{3} $，CE = 1，所以  $ AE^2 + CE^2 = 4 = AC^2 $，故  $ AE \perp PC $，且  $ \cos \angle ACE = \frac{CE}{AC} = \frac{1}{2} $，所以  $ \angle ACE = 60^\circ $，结合 PA = PC 可得  $ \triangle PAC $ 是正三角形，因为  $ AE \perp PC $，所以 E 为 PC 中点，结合 F 为 OC 中点可得  $ EF \parallel PO $，

因为  $ AE \perp PC $，所以 E 为 PC 中点，结合 F 为 OC 中点可得  $ EF \parallel PO $，因为  $ PO \not\subset $ 平面 BDE， $ EF \subset $ 平面 BDE，所以  $ PO \parallel $ 平面 BDE。

（2）由（1）得 EF∥PO，因为 PO⊥平面 ABD，所以 EF⊥平面 ABD，又 EF⊂平面 BED，所以平面 BED⊥平面 ABD.

（3）（条件涉及线面角，考虑建系，用向量法来翻译. 在圆锥中，常以圆锥的高为 z 轴建系）

以 O 为原点建立如图所示的空间直角坐标系，则  $ D\left(-\frac{\sqrt{3}}{2},\frac{1}{2},0\right) $， $ A(0,-1,0) $， $ B\left(\frac{\sqrt{3}}{2},\frac{1}{2},0\right) $，

因为  $ \triangle PAC $ 是正三角形，所以  $ PO = PA \cdot \sin \angle PAO = 2 \sin 60^\circ = \sqrt{3} $，故  $ E\left(0, \frac{1}{2}, \frac{\sqrt{3}}{2}\right) $，

所以  $ \overrightarrow{AB} = \left( \frac{\sqrt{3}}{2}, \frac{3}{2}, 0 \right) $， $ \overrightarrow{AE} = \left( 0, \frac{3}{2}, \frac{\sqrt{3}}{2} \right) $，设平面  $ ABE $ 的法向量为  $ \boldsymbol{m} = (x, y, z) $，则  $ \left\{ \begin{array}{l} \boldsymbol{m} \cdot \overrightarrow{AB} = \frac{\sqrt{3}}{2} x + \frac{3}{2} y = 0 \\ \boldsymbol{m} \cdot \overrightarrow{AE} = \frac{3}{2} y + \frac{\sqrt{3}}{2} z = 0 \end{array} \right. $，令  $ x = \sqrt{3} $，则  $ y = -1 $， $ z = \sqrt{3} $，所以  $ \boldsymbol{m} = (\sqrt{3}, -1, \sqrt{3}) $ 是平面  $ ABE $ 的一个法向量，

（求 DM 与平面 ABE 所成的角还差 M 的坐标，M 在线段 PO 上运动，只有 z 坐标会变，故可直接设 M 的坐标）

设  $ M(0,0,a)(0 \leq a \leq \sqrt{3}) $，则  $ \overrightarrow{DM} = \left( \frac{\sqrt{3}}{2}, -\frac{1}{2}, a \right) $，设直线 DM 与平面 ABE 所成的角为  $ \theta $，