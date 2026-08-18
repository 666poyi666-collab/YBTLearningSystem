【反思】用向量法证明两个平面平行，只需求出其中一个平面的法向量，再证明它也是另一个平面的法向量.

## 类型Ⅱ：利用空间向量研究垂直关系

【例 13】如图，在四棱锥  $ P-ABCD $ 中， $ PA \perp $ 平面  $ ABCD $， $ AD \perp AB $， $ AB \parallel DC $， $ AD = DC = AP = 2 $， $ AB = 1 $，求证：平面  $ PCD \perp $ 平面 PBC。

证明：（不难发现图中本身有 3 条两两垂直的直线，故可考虑建系处理）

因为  $ PA \perp $ 平面  $ ABCD $， $ AB $， $ AD \subset $ 平面  $ ABCD $，所以  $ PA \perp AB $， $ PA \perp AD $，

又  $ AD \perp AB $，所以  $ PA $， $ AB $， $ AD $ 两两垂直，以  $ A $ 为原点建立如



<div style="text-align: center;"><img src="imgs/img_in_image_box_886_251_1092_401.jpg" alt="Image" width="17%" /></div>


（怎样证平面 $PCD \perp$ 平面 $PBC$？如图2，可以想象，互相垂直的两个平面 $\alpha$，$\beta$ 的法向量 $m$，$n$ 也互相垂直故可通过证明两个平面的法向量垂直来证明这两个平面垂直）

由图1可知，$P(0,0,2)$，$C(2,2,0)$，$D(0,2,0)$，$B(1,0,0)$，所以 $\overrightarrow{DC}=(2,0,0)$，$\overrightarrow{PC}=(2,2,-2)$，$\overrightarrow{BC}=(1,2,0)$，设平面 $PCD$ 和平面 $PBC$ 的法向量分别为 $\boldsymbol{m}=(x_1,y_1,z_1)$，$\boldsymbol{n}=(x_2,y_2,z_2)$，

则 $\begin{cases} \boldsymbol{m} \cdot \overrightarrow{DC} = 2x_1 = 0 \\ \boldsymbol{m} \cdot \overrightarrow{PC} = 2x_1 + 2y_1 - 2z_1 = 0 \end{cases}$，令 $y_1 = 1$，则 $\begin{cases} x_1 = 0 \\ z_1 = 1 \end{cases}$，所以 $\boldsymbol{m} = (0,1,1)$ 是平面 $PCD$ 的一个法向量，

同理，$\begin{cases} \boldsymbol{n} \cdot \overrightarrow{PC} = 2x_2 + 2y_2 - 2z_2 = 0 \\ \boldsymbol{n} \cdot \overrightarrow{BC} = x_2 + 2y_2 = 0 \end{cases}$，令 $x_2 = 2$，则 $\begin{cases} y_2 = -1 \\ z_2 = 1 \end{cases}$，所以 $\boldsymbol{n} = (2,-1,1)$ 是平面 $PBC$ 的一个法向量，

因为 $\boldsymbol{m} \cdot \boldsymbol{n} = 0 \times 2 + 1 \times (-1) + 1 \times 1 = 0$，所以 $\boldsymbol{m} \perp \boldsymbol{n}$，故平面 $PCD$ ⊥ 平面 $PBC$。

<div style="text-align: center;"><img src="imgs/img_in_image_box_345_771_584_943.jpg" alt="Image" width="20%" /></div>


<div style="text-align: center;">图1</div>


<div style="text-align: center;"><img src="imgs/img_in_image_box_646_779_826_928.jpg" alt="Image" width="15%" /></div>


<div style="text-align: center;">图2</div>


【反思】用向量法证面面垂直，只需求出两个平面的法向量，再证明两个法向量垂直。但有的题不方便建系，这种情况下证明垂直关系，可以不建系，直接使用拆解法，我们来看下面的例14。

【例14】如图，平行六面体  $ ABCD-A_1B_1C_1D_1 $ 的底面  $ ABCD $ 是菱形，且  $ CD=CC_1=2 $， $ \angle C_1CB=\angle C_1CD=\angle BCD=60^\circ $，证明： $ CA_1 \perp $ 平面  $ C_1BD $。

证明：（要证结论成立，只需证  $ \overrightarrow{CA_1} $ 是平面  $ C_1BD $ 的法向量，即证  $ \overrightarrow{CA_1} \cdot \overrightarrow{BC_1}=0 $ 和  $ \overrightarrow{CA_1} \cdot \overrightarrow{BD}=0 $，怎么证？图中没有三条两两垂直的直线，建系比较麻烦，但注意到  $ \overrightarrow{CB} $， $ \overrightarrow{CD} $， $ \overrightarrow{CC_1} $ 这三个向量既知道长度，又知道两两夹角，故可用它们表示上述有关向量，再求数量积）





<div style="text-align: center;"><img src="imgs/img_in_image_box_870_1074_1094_1245.jpg" alt="Image" width="18%" /></div>


由图可知， $ CA_1 = CB + BA + AA_1 = CB + CD + CC_1 $， $ BC_1 = BC + CC_1 = CC_1 - CB $， $ BD = CD - CB $，所以 $ \overrightarrow{CA_1} \cdot \overrightarrow{BC_1} = (\overrightarrow{CB} + \overrightarrow{CD} + \overrightarrow{CC_1}) \cdot (\overrightarrow{CC_1} - \overrightarrow{CB}) $ = [(( $ CC_1^+ $ +  $ \overrightarrow{CB} $) +  $ \overrightarrow{CD} $] \cdot ( $ CC_1^+ $ -  $ \overrightarrow{CB} $) = (( $ CC_1^+ $ +  $ \overrightarrow{CB} $) \cdot ( $ CC_1^+ $ -  $ \overrightarrow{CB} $)) \cdot ( $ CC_1^2 $ -  $ \overrightarrow{CB} $)^2 +  $ \overrightarrow{CD} $ \cdot \overrightarrow{CC_1} - \overrightarrow{CD} $ \cdot  $ \overrightarrow{CB} $ = 2^2 - 2^2 + 2 \times 2 \times \cos 60^\circ - 2 \times 2 \times \cos 60^\circ = 0 $， $ \overrightarrow{CA_1} \cdot \overrightarrow{BD} = (\overrightarrow{CB} + \overrightarrow{CD} + \overrightarrow{CC_1}) \cdot (\overrightarrow{CD} - \overrightarrow{CB}) $ = [(( $ CD^+ $ +  $ \overrightarrow{CB} $) +  $ \overrightarrow{CC_1} $] \cdot ( $ \overrightarrow{CD} - \overrightarrow{CB} $) = ( $ \overrightarrow{CD} + \overrightarrow{CB} $) \cdot ( $ \overrightarrow{CD} - \overrightarrow{CB} $) +  $ \overrightarrow{CC_1} $ \cdot ( $ \overrightarrow{CD} - \overrightarrow{CB} $) =  $ \overrightarrow{CD}^2 - \overrightarrow{CB}^2 + \overrightarrow{CC_1} \cdot \overrightarrow{CD} - \overrightarrow{CC_1} \cdot \overrightarrow{CB} $ = 2^2 - 2^2 + 2 \times 2 \times \cos 60^\circ - 2 \times 2 \times \cos 60^\circ = 0 $，

从而  $ \overrightarrow{CA_{1}} $ 是平面  $ C_{1}BD $ 的法向量，故  $ CA_{1}\perp $ 平面  $ C_{1}BD $

【反思】用向量法证明直线与平面垂直，只需证直线上的一个向量u是平面的法向量，即证u与该平面内两个