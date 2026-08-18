解得： $ \cos \angle BAD = \frac{1}{2} $，结合  $ 0^\circ < \angle BAD < 180^\circ $ 可得  $ \angle BAD = 60^\circ $。

答案： $ 60^{\circ} $

【变式 2】如图，边长为 1 的正方形 $ABCD$ 所在平面与正方形 $ABEF$ 所在平面互相垂直，动点 $M$，$N$ 满足 $\overrightarrow{CM} = \lambda \overrightarrow{CA}$，$\overrightarrow{BN} = \lambda \overrightarrow{BF}$，其中 $0 < \lambda < 1$。

（1）若  $ \overrightarrow{MN} = x\overrightarrow{AB} + y\overrightarrow{AD} + z\overrightarrow{AF} $，求实数 x, y, z 的值（用  $ \lambda $ 表示）；

<div style="text-align: center;"><img src="imgs/img_in_image_box_892_152_1091_339.jpg" alt="Image" width="16%" /></div>


（2）求线段 MN 的长度的最小值.

解：（1）由题意， $ \overrightarrow{MN} = \overrightarrow{MC} + \overrightarrow{CB} + \overrightarrow{BN} = \lambda \overrightarrow{AC} - \overrightarrow{BC} + \overrightarrow{BN} = \lambda (\overrightarrow{AB} + \overrightarrow{AD}) - \overrightarrow{AD} + \lambda \overrightarrow{BF} $

 $ = \lambda (\overrightarrow{AB} + \overrightarrow{AD}) - \overrightarrow{AD} + \lambda (\overrightarrow{BA} + \overrightarrow{AF}) = \lambda (\overrightarrow{AB} + \overrightarrow{AD}) - \overrightarrow{AD} + \lambda (-\overrightarrow{AB} + \overrightarrow{AF}) = (\lambda - 1) \overrightarrow{AD} + \lambda \overrightarrow{AF} $，

又由题意， $ \overrightarrow{MN} = x \overrightarrow{AB} + y \overrightarrow{AD} + z \overrightarrow{AF} $，所以  $ x = 0 $， $ y = \lambda - 1 $， $ z = \lambda $。

（2）（第（1）问已将 $ \overrightarrow{MN} $用 $ \overrightarrow{AD} $， $ \overrightarrow{AF} $表示，故可通过平方将 $ |\overrightarrow{MN}| $转化为 $ \overrightarrow{AD} $， $ \overrightarrow{AF} $之间的数量积来计算，下面先分析它们的夹角）因为四边形ABCD为正方形，所以 $ AD \perp AB $，又平面 $ ABCD \perp $平面 $ ABEF $，平面 $ ABCD \cap $平面 $ ABEF = AB $， $ AD \subset $平面 $ ABCD $，故 $ AD \perp $平面 $ ABEF $，结合 $ AF \subset $平面 $ ABEF $得 $ AD \perp AF $，由（1）知 $ \overrightarrow{MN} = (\lambda - 1)\overrightarrow{AD} + \lambda\overrightarrow{AF} $，所以 $ \overrightarrow{MN}^2 = [(\lambda - 1)\overrightarrow{AD} + \lambda\overrightarrow{AF}]^2 = (\lambda - 1)^2\overrightarrow{AD}^2 + \lambda^2\overrightarrow{AF}^2 + 2(\lambda - 1)\lambda\overrightarrow{AD} \cdot \overrightarrow{AF} $，从而 $ \left|\overrightarrow{MN}\right|^2 = (\lambda - 1)^2 \times 1^2 + \lambda^2 \times 1^2 + 2(\lambda - 1)\lambda \times 0 = 2\lambda^2 - 2\lambda + 1 = 2\left(\lambda - \frac{1}{2}\right)^2 + \frac{1}{2} $，故当 $ \lambda = \frac{1}{2} $时（满足 $ 0 < \lambda < 1 $）， $ \left|\overrightarrow{MN}\right|^2 $取得最小值 $ \frac{1}{2} $，所以线段MN的长度的最小值为 $ \frac{\sqrt{2}}{2} $。

## 类型VI：利用空间向量求角

【例 16】若空间向量  $ a $， $ b $， $ c $ 满足  $ a + b + c = 0 $，且  $ |a| = 2 $， $ |b| = 3 $， $ |c| = 4 $，则  $ \cos \langle a, b \rangle = $ （ ）

A.  $ \frac{1}{3} $  B.  $ \frac{\sqrt{2}}{3} $  C.  $ \frac{\sqrt{3}}{3} $  D.  $ \frac{1}{4} $

解析：所求为  $ \cos <a,b> $，联想到夹角余弦公式  $ \cos <a,b> = \frac{a\cdot b}{|a|\cdot|b|} $，其中  $ |a| $ 和  $ |b| $ 已知，还差  $ a\cdot b $，那怎样产生  $ a\cdot b $? 可考虑将  $ a+b+c=0 $ 平方，但若直接平方，还会产生额外的  $ a\cdot c $ 和  $ b\cdot c $，怎么办呢？把  $ c $ 移到等号另一侧，再平方，就不会有这两个干扰项了，

因为  $ a+b+c=0 $，所以  $ a+b=-c $，从而  $ (a+b)^2 = (-c)^2 $，故  $ a^2 + b^2 + 2a\cdot b = c^2 $，

所以 $ |a|^2 + |b|^2 + 2a \cdot b = |c|^2 $，将所给数据代入得 $ 2^2 + 3^2 + 2a \cdot b = 4^2 \Rightarrow a \cdot b = \frac{3}{2} \Rightarrow \cos \langle a, b \rangle = \frac{a \cdot b}{|a| \cdot |b|} = \frac{\frac{3}{2}}{2 \times 3} = \frac{1}{4} $。

答案：D

【反思】与平面向量中的处理方法类似，在空间向量中，涉及夹角，往往用夹角余弦公式处理，其核心是计算数量积和模。本题没有图形，且模是已知的，在具体的图形下，也可能有类似的问题，

我们来看两个变式。

【变式1】如图，正四面体OABC中，E，F分别为AB，OC的中点，则向量 $ \overrightarrow{OE} $与 $ \overrightarrow{BF} $的夹角余弦值为___。





<div style="text-align: center;"><img src="imgs/img_in_image_box_895_1378_1092_1572.jpg" alt="Image" width="16%" /></div>
