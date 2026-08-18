不共线的向量数量积为0.

## 类型Ⅲ：利用空间向量求空间角

【例 15】如图，在空间直角坐标系中有直三棱柱  $ ABC-A_1B_1C_1 $， $ CA=CC_1=2CB=2 $，则直线  $ BC_1 $ 与  $ AB_1 $ 所成角的正弦值为（ ）

A.  $ \frac{\sqrt{5}}{5} $ B.  $ \frac{\sqrt{5}}{3} $ C.  $ \frac{2\sqrt{5}}{5} $ D.  $ \frac{3}{5} $

解析：求线线角，可在两条直线上各取一个向量，计算它们的夹角余弦，进而得到线线角的正弦值，由图可知， $ B(0,0,1) $， $ C_1(0,2,0) $， $ A(2,0,0) $， $ B_1(0,2,1) $，所以  $ \overrightarrow{BC_1} = (0,2,-1) $， $ \overrightarrow{AB_1} = (-2,2,1) $，



<div style="text-align: center;"><img src="imgs/img_in_image_box_854_237_1088_414.jpg" alt="Image" width="19%" /></div>


设直线 $BC_1$ 与 $AB_1$ 所成的角为 $\theta$，则 $\cos\theta = \left|\cos<\overrightarrow{BC_1},\overrightarrow{AB_1}>\right| = \frac{\left|\overrightarrow{BC_1}\cdot\overrightarrow{AB_1}\right|}{\left|\overrightarrow{BC_1}\right|\cdot\left|\overrightarrow{AB_1}\right|} = \frac{\left|0\times(-2)+2\times2+(-1)\times1\right|}{\sqrt{0^2+2^2+(-1)^2}\times\sqrt{(-2)^2+2^2+1^2}} = \frac{\sqrt{5}}{5}$，所以直线 $BC_1$ 与 $AB_1$ 所成角的正弦值为 $\sin\theta = \sqrt{1-\cos^2\theta} = \sqrt{1-\left(\frac{\sqrt{5}}{5}\right)^2} = \frac{2\sqrt{5}}{5}$。

答案：C

【反思】对于两条异面直线所成的角$\theta$，可在两直线上各取一个向量$a$，$b$，按$\cos\theta=\left|\cos\langle a,b\rangle\right|$求$\cos\theta$。

【例16】（2021·天津卷（节选））如图，在棱长为2的正方体$ABCD-$$A_1B_1C_1D_1$中，$E$，$F$分别为棱$BC$，$CD$的中点，求直线$AC_1$与平面$A_1EC_1$所成角的正弦值。



解：（正方体容易建系，可考虑建系处理，那建系后怎样用向量法求线面角？需要先求

直线上的一个向量，以及平面的法向量，再求二者的夹角余弦值）

以  $ A $ 为原点建立如图所示的空间直角坐标系，则  $ A(0,0,0) $， $ A_1(0,0,2) $， $ E(2,1,0) $， $ C_1(2,2,2) $，

所以  $ \overrightarrow{AC_1} = (2,2,2) $， $ \overrightarrow{A_1C_1} = (2,2,0) $， $ \overrightarrow{EC_1} = (0,1,2) $，

设平面  $ A_1EC_1 $ 的法向量为  $ \boldsymbol{n} = (x,y,z) $，则  $ \begin{cases} \boldsymbol{n} \cdot \overrightarrow{A_1C_1} = 2x + 2y = 0 \\ \boldsymbol{n} \cdot \overrightarrow{EC_1} = y + 2z = 0 \end{cases} $，令  $ x = 2 $，则  $ y = -2 $， $ z = 1 $，

所以  $ \boldsymbol{n} = (2,-2,1) $ 是平面  $ A_1EC_1 $ 的一个法向量，





<div style="text-align: center;"><img src="imgs/img_in_image_box_896_783_1093_962.jpg" alt="Image" width="16%" /></div>


设直线  $ AC_1 $ 与平面  $ A_1EC_1 $ 所成的角为  $ \theta $，则  $ \sin \theta = |\cos < \overrightarrow{AC_1}, \boldsymbol{n} > | $ =  $ \frac{|AC_1 \cdot \boldsymbol{n}|}{|AC_1| \cdot |\boldsymbol{n}|} $

 $ = \frac{|2 \times 2 + 2 \times (-2) + 2 \times 1|}{\sqrt{2^2 + 2^2 + 2^2} \times \sqrt{2^2 + (-2)^2 + 1^2}} = \frac{\sqrt{3}}{9} $，

所以直线  $ AC_1 $ 与平面  $ A_1EC_1 $ 所成角的正弦值为  $ \frac{\sqrt{3}}{9} $。

【反思】设直线  $ l $ 与平面  $ \alpha $ 所成的角为  $ \theta $，则可按以下步骤用向量法求  $ \sin \theta $：先在直线  $ l $ 上取一个向量  $ \boldsymbol{u} $，再求出平面  $ \alpha $ 的法向量  $ \boldsymbol{n} $，则  $ \sin \theta = |\cos < \boldsymbol{u}, \boldsymbol{n} > | $。



<div style="text-align: center;"><img src="imgs/img_in_image_box_850_1143_1090_1352.jpg" alt="Image" width="20%" /></div>


【例 17】如图，在四棱锥 P-ABCD 中，平面  $ PAD \perp $ 平面 ABCD，底面

<div style="text-align: center;"><img src="imgs/img_in_image_box_853_1486_1092_1663.jpg" alt="Image" width="20%" /></div>
