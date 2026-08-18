 $ m_2 \geq \pm \frac{m_1 \cdot m_2}{|m_1| \cdot |m_2|} $，若是求  $ \sin \theta $，则可由  $ \sin \theta = \sqrt{1 - \cos^2 \theta} $ 来算， $ \cos \theta $ 取正取负不影响结果；若是求  $ \cos \theta $，则最终结果取正还是取负，需考虑二面角的锐钝，一般可通过观察图形，直观想象来判断，若图形不易判断，则可通过法向量的指向来判断。若两个法向量都朝内或朝外，如图1，则  $ \cos \theta = -\cos < m_1, m_2> $；若一个朝内，一个朝外，如图2，则  $ \cos \theta = \cos < m_1, m_2> $。

<div style="text-align: center;"><img src="imgs/img_in_image_box_168_497_361_617.jpg" alt="Image" width="16%" /></div>


<div style="text-align: center;">图1</div>


<div style="text-align: center;"><img src="imgs/img_in_image_box_417_511_609_615.jpg" alt="Image" width="16%" /></div>


<div style="text-align: center;">图2</div>


4. 利用空间向量解决立体几何问题的一般步骤

①转化：将立体几何问题中涉及的距离、角度等利用空间向量进行表示，把立体几何问题转化为向量问题；

②运算：将向量问题的结果运算出来；

③翻译：把向量问题的结果“翻译”成对应的几何结论。

 $ \overrightarrow{AC} = (1, \sqrt{3}, 0) $， $ \overrightarrow{AE} = \left(0, \frac{\sqrt{3}}{2}, \frac{1}{2}\right) $，

设平面  $ ACE $ 的法向量为  $ \boldsymbol{m} = (x, y, z) $，

则  $ \begin{cases} \boldsymbol{m} \cdot \overrightarrow{AC} = x + \sqrt{3}y = 0 \\ \boldsymbol{m} \cdot \overrightarrow{AE} = \frac{\sqrt{3}}{2}y + \frac{1}{2}z = 0 \end{cases} $，

令  $ x = \sqrt{3} $，则  $ y = -1 $， $ z = \sqrt{3} $，

所以  $ \boldsymbol{m} = (\sqrt{3}, -1, \sqrt{3}) $ 是平面  $ ACE $ 的一个法向量，又  $ x $ 轴perp 平面  $ DAE $，所以  $ \boldsymbol{n} = (1, 0, 0) $ 是平面  $ DAE $ 的一个法向量，

所以  $ \cos \langle \boldsymbol{m}, \boldsymbol{n} \rangle = \frac{\boldsymbol{m} \cdot \boldsymbol{n}}{|\boldsymbol{m}| \cdot |\boldsymbol{n}|} $

 $ = \frac{\sqrt{3} \times 1 + (-1) \times 0 + \sqrt{3} \times 0}{\sqrt{(\sqrt{3})^2 + (-1)^2 + (\sqrt{3})^2} \times 1} = \frac{\sqrt{21}}{7} $，

（最终答案是  $ \frac{\sqrt{21}}{7} $，还是  $ -\frac{\sqrt{21}}{7} $？这由二面角  $ D-AE-C $ 的锐钝决定，可直接观察图形，通过直观想象作出判断）

由图可知，二面角  $ D-AE-C $ 为锐角，所以其余弦值为  $ \frac{\sqrt{21}}{7} $。



<div style="text-align: center;"><img src="imgs/img_in_image_box_782_810_1028_972.jpg" alt="Image" width="20%" /></div>


## 本节核心题型

空间向量作为非常强大的工具，可以解决立体几何中的诸多问题。本节我们通过四组题来为同学们梳理一些立体几何常见题型的向量处理方法，包括用空间向量研究平行关系、垂直关系、求空间角和求空间距离，请大家跟着例题和反思去学习、总结每种题型的向量处理方法吧。

类型 I：利用空间向量研究平行关系

【例 11】如图，在长方体  $ ABCD-A_1B_1C_1D_1 $ 中， $ AB = 4 $， $ BC = CC_1 = 2 $，线段  $ B_1C $ 的中点为  $ P $，证明： $ A_1P \parallel $ 平面  $ ACD_1 $。

证法1：（怎样证  $ A_1P \parallel $ 平面  $ ACD_1 $？只需证  $ \overrightarrow{A_1P} $ 是平面  $ ACD_1 $ 内的向量，即证存在实数  $ \lambda $， $ \mu $，使  $ \overrightarrow{A_1P} = \lambda \overrightarrow{AD_1} + \mu \overrightarrow{AC} $，下面我们按此建立方程组，求解  $ \lambda $ 和  $ \mu $）

由题意， $ A_1(2,0,2) $， $ P(1,4,1) $， $ A(2,0,0) $， $ C(0,4,0) $， $ D_1(0,0,2) $，

所以  $ \overrightarrow{A_1P} = (-1,4,-1) $， $ \overrightarrow{AD_1} = (-2,0,2) $， $ \overrightarrow{AC} = (-2,4,0) $，设  $ \overrightarrow{A_1P} = \lambda \overrightarrow{AD_1} + \mu \overrightarrow{AC} $，

<div style="text-align: center;"><img src="imgs/img_in_image_box_842_1277_1092_1455.jpg" alt="Image" width="20%" /></div>
