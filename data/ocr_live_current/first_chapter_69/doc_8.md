【例 13】棱长为 1 的正四面体  $ ABCD $ 中， $ E $ 是  $ BC $ 的中点，则  $ \overrightarrow{AE} \cdot \overrightarrow{AD} = $ ___.

解析：如图，用定义求  $ \overrightarrow{AE} \cdot \overrightarrow{AD} $ 需要先算  $ \cos \angle DAE $，比较麻烦，能否不求  $ \cos \angle DAE $？在正四面体中， $ \overrightarrow{AB} $， $ \overrightarrow{AC} $， $ \overrightarrow{AD} $ 的长度和两两夹角都已知，故可考虑根据  $ E $ 为  $ BC $ 中点把  $ \overrightarrow{AE} $ 用  $ \overrightarrow{AB} $ 和  $ \overrightarrow{AC} $ 表示，再求  $ \overrightarrow{AE} \cdot \overrightarrow{AD} $，因为  $ E $ 为  $ BC $ 中点，所以  $ \overrightarrow{AE} = \frac{1}{2}\overrightarrow{AB} + \frac{1}{2}\overrightarrow{AC} $，故  $ \overrightarrow{AE} \cdot \overrightarrow{AD} = \left( \frac{1}{2}\overrightarrow{AB} + \frac{1}{2}\overrightarrow{AC} \right) \cdot \overrightarrow{AD} $

 $ = \frac{1}{2}\overrightarrow{AB} \cdot \overrightarrow{AD} + \frac{1}{2}\overrightarrow{AC} \cdot \overrightarrow{AD} = \frac{1}{2}\left| \overrightarrow{AB} \right| \cdot \left| \overrightarrow{AD} \right| \cdot \cos \angle BAD + \frac{1}{2}\left| \overrightarrow{AC} \right| \cdot \left| \overrightarrow{AD} \right| \cdot \cos \angle CAD $

 $ = \frac{1}{2} \times 1 \times 1 \times \cos \frac{\pi}{3} + \frac{1}{2} \times 1 \times 1 \times \cos \frac{\pi}{3} = \frac{1}{2} $.

答案： $ \frac{1}{2} $

【反思】与求平面向量数积类似，求空间向量的数量积，除了用定义之外，还有拆解法、极化恒等式（后面的例14会涉及）等方法可以使用，本题使用的是拆解法，即选择一些已知长度、夹角的向量，先用它们表示求数量积的向量，再将所求数量积转化为这些已知长度、夹角的向量之间的数量积来算。本题的图形较简单，我们来看一个图形稍复杂一点的变式。

【变式】如图，在平行六面体  $ ABCD - A_1B_1C_1D_1 $ 中， $ AB = AD = AA_1 = 1 $， $ \angle A_1AB = \angle A_1AD = \angle BAD = 60^\circ $，则  $ \overrightarrow{BD_1} \cdot \overrightarrow{AC} $ 的值为（ ）

A. 1          B.  $ \sqrt{2} $          C.  $ \sqrt{3} $          D. -1







<div style="text-align: center;"><img src="imgs/img_in_image_box_913_257_1092_430.jpg" alt="Image" width="15%" /></div>


<div style="text-align: center;"><img src="imgs/img_in_image_box_878_574_1093_765.jpg" alt="Image" width="18%" /></div>


解析：不难发现$\overrightarrow{AB}$，$\overrightarrow{AD}$，$\overrightarrow{AA_1}$已知长度和两两夹角，故可考虑先用它们表示$\overrightarrow{BD_1}$和$\overrightarrow{AC}$，再求$\overrightarrow{BD_1}\cdot\overrightarrow{AC}$，由图可知，$\overrightarrow{BD_1}=\overrightarrow{BA}+\overrightarrow{AA_1}+\overrightarrow{A_1D_1}=-\overrightarrow{AB}+\overrightarrow{AA_1}+\overrightarrow{AD}$，$\overrightarrow{AC}=\overrightarrow{AB}+\overrightarrow{AD}$，所以$\overrightarrow{BD_1}\cdot\overrightarrow{AC}=(-\overrightarrow{AB}+\overrightarrow{AA_1}+\overrightarrow{AD})\cdot(\overrightarrow{AB}+\overrightarrow{AD})=-\overrightarrow{AB}^2-\overrightarrow{AB}\cdot\overrightarrow{AD}+\overrightarrow{AA_1}\cdot\overrightarrow{AB}+\overrightarrow{AA_1}\cdot\overrightarrow{AD}+\overrightarrow{AD}\cdot\overrightarrow{AB}+\overrightarrow{AD}^2=-\overrightarrow{AB}^2+\overrightarrow{AA_1}\cdot\overrightarrow{AB}+\overrightarrow{AA_1}\cdot\overrightarrow{AD}+\overrightarrow{AD}^2=-\left|\overrightarrow{AB}\right|^2+\left|\overrightarrow{AA_1}\right|\cdot\left|\overrightarrow{AB}\right|\cdot\cos\angle A_1AB+\left|\overrightarrow{AA_1}\right|\cdot\left|\overrightarrow{AD}\right|\cdot\cos\angle A_1AD+\left|\overrightarrow{AD}\right|^2=-1^2+1\times1\times\cos60^\circ+1\times1\times\cos60^\circ+1^2=1$

答案：A

【例 14】已知正三棱锥  $ S-ABC $ 的底面  $ ABC $ 的边长为 2， $ P $ 是空间中任意一点，则  $ \overrightarrow{PA} \cdot (\overrightarrow{PB} + \overrightarrow{PC}) $ 的最小值为（ ）

A.  $ -\frac{3}{2} $ \quad B.  $ -\frac{\sqrt{3}}{2} $ \quad C.  $ -\frac{1}{2} $ \quad D.  $ -\frac{1}{4} $

解析：设  $ BC $ 中点为  $ D $，则  $ \overrightarrow{PB} + \overrightarrow{PC} = 2\overrightarrow{PD} \Rightarrow \overrightarrow{PA} \cdot (\overrightarrow{PB} + \overrightarrow{PC}) = \overrightarrow{PA} \cdot (2\overrightarrow{PD}) = 2\overrightarrow{PA} \cdot \overrightarrow{PD} $ ①，



注意到  $ \overrightarrow{PA} $， $ \overrightarrow{PD} $ 共起点，底边  $ AD $ 的长也容易计算，故想到用极化恒等式计算  $ \overrightarrow{PA} \cdot \overrightarrow{PD} $，如图， $ \triangle ABC $ 是边长为 2 的正三角形，所以  $ AD \perp BC $，故  $ |\overrightarrow{AD}| = |\overrightarrow{AB}| \cdot \sin \angle ABD = 2 \sin 60^\circ = \sqrt{3} $，

设 $AD$ 中点为 $G$，则由极化恒等式，$\overrightarrow{PA} \cdot \overrightarrow{PD} = |\overrightarrow{PG}|^2 - |\overrightarrow{GA}|^2 = |\overrightarrow{PG}|^2 - \frac{1}{4}|\overrightarrow{AD}|^2$

$= |\overrightarrow{PG}|^2 - \frac{3}{4} \geq -\frac{3}{4}$，代入①得 $\overrightarrow{PA} \cdot (\overrightarrow{PB} + \overrightarrow{PC}) = 2\overrightarrow{PA} \cdot \overrightarrow{PD} \geq 2 \times \left(-\frac{3}{4}\right) = -\frac{3}{2}$，

当且仅当 $P$ 与 $G$ 重合时取等号，所以 $\overrightarrow{PA} \cdot (\overrightarrow{PB} + \overrightarrow{PC})$ 的最小值为 $-\frac{3}{2}$。

<div style="text-align: center;"><img src="imgs/img_in_image_box_935_1221_1093_1378.jpg" alt="Image" width="13%" /></div>


<div style="text-align: center;"><img src="imgs/img_in_image_box_915_1437_1094_1528.jpg" alt="Image" width="15%" /></div>
