类型III：利用空间向量证明共面

【例 12】已知 $A, B, C$ 三点不共线，且平面 $ABC$ 外一点 $O$ 满足 $\overrightarrow{OM} = \frac{1}{3}\overrightarrow{OA} + \frac{1}{3}\overrightarrow{OB} + \frac{1}{3}\overrightarrow{OC}$，判断 $\overrightarrow{MA}, \overrightarrow{MB}, \overrightarrow{MC}$ 三个向量是否共面。

解：（要判断  $ \overrightarrow{MA} $， $ \overrightarrow{MB} $， $ \overrightarrow{MC} $ 是否共面，就看能否找到实数  $ \lambda $ 和  $ \mu $，使  $ \overrightarrow{MA} = \lambda \overrightarrow{MB} + \mu \overrightarrow{MC} $。题设条件给出了  $ \overrightarrow{OM} = \frac{1}{3} \overrightarrow{OA} + \frac{1}{3} \overrightarrow{OB} + \frac{1}{3} \overrightarrow{OC} $，而上述目标式中的向量不涉及点  $ O $，故考虑消去  $ O $，怎么消？观察发现可将  $ \overrightarrow{OM} $ 拆分成  $ \frac{1}{3} \overrightarrow{OM} + \frac{1}{3} \overrightarrow{OM} + \frac{1}{3} \overrightarrow{OM} $，再分别与  $ \frac{1}{3} \overrightarrow{OA} $， $ \frac{1}{3} \overrightarrow{OB} $， $ \frac{1}{3} \overrightarrow{OC} $ 组合，即可消去  $ O $，故尝试按此变形）

因为  $ \overrightarrow{OM} = \frac{1}{3} \overrightarrow{OA} + \frac{1}{3} \overrightarrow{OB} + \frac{1}{3} \overrightarrow{OC} $，所以  $ \frac{1}{3} \overrightarrow{OM} + \frac{1}{3} \overrightarrow{OM} + \frac{1}{3} \overrightarrow{OM} = \frac{1}{3} \overrightarrow{OA} + \frac{1}{3} \overrightarrow{OB} + \frac{1}{3} \overrightarrow{OC} $，

从而  $ \overrightarrow{OM} + \overrightarrow{OM} + \overrightarrow{OM} = \overrightarrow{OA} + \overrightarrow{OB} + \overrightarrow{OC} $，故  $ \overrightarrow{OA} - \overrightarrow{OM} = -(\overrightarrow{OB} - \overrightarrow{OM}) - (\overrightarrow{OC} - \overrightarrow{OM}) $，

所以  $ \overrightarrow{MA} = -\overrightarrow{MB} - \overrightarrow{MC} $，故  $ \overrightarrow{MA} $， $ \overrightarrow{MB} $， $ \overrightarrow{MC} $ 三个向量共面。

【反思】①类似于平面上的 $ \overrightarrow{OM}=x\overrightarrow{OA}+y\overrightarrow{OB} $， $ M $， $ A $， $ B $三点共线 $ \Leftrightarrow x+y=1 $，在空间中，若 $ \overrightarrow{OM}=x\overrightarrow{OA}+y\overrightarrow{OB}+z\overrightarrow{OC} $，则 $ M $， $ A $， $ B $， $ C $四点共面 $ \Leftrightarrow x+y+z=1 $（四点共面的系数和结论），本题结论实质上就是 $ M $， $ A $， $ B $， $ C $四点共面，故其处理方法与平面上证 $ M $， $ A $， $ B $共线类似，我们将 $ \overrightarrow{OM} $按 $ \overrightarrow{OA} $， $ \overrightarrow{OB} $， $ \overrightarrow{OC} $的系数进行了拆分。②要看三个不共线的向量是否共面，就看其中一个向量能否用另外两个向量表示。若能，则三个向量共面；若不能，则三个向量不共面。不仅证向量共面可以这么做，证四点共面，也可类似处理，我们来看一个变式。

【变式】如图，已知平行六面体 $ ABCD-A_1B_1C_1D_1 $中， $ E $， $ F $， $ G $， $ H $分别是棱 $ A_1D_1 $， $ C_1D_1 $， $ CC_1 $， $ AB $的中点。



（1）设 $ \overrightarrow{EG} = x\overrightarrow{AB} + y\overrightarrow{AD} + z\overrightarrow{AA_1} $，其中 $ x, y, z \in \mathbb{R} $，求 $ x $， $ y $， $ z $的值；

（2）证明： $ E $， $ F $， $ G $， $ H $四点共面。

<div style="text-align: center;"><img src="imgs/img_in_image_box_879_813_1092_1011.jpg" alt="Image" width="17%" /></div>


解：（1）由图可知  $ \overrightarrow{EG} = \overrightarrow{ED_1} + \overrightarrow{D_1C_1} + \overrightarrow{C_1G} = \frac{1}{2}\overrightarrow{AD} + \overrightarrow{AB} - \frac{1}{2}\overrightarrow{AA_1} = \overrightarrow{AB} + \frac{1}{2}\overrightarrow{AD} - \frac{1}{2}\overrightarrow{AA_1} $，

又由题意， $ \overrightarrow{EG} = x\overrightarrow{AB} + y\overrightarrow{AD} + z\overrightarrow{AA_1} $，所以  $ x=1 $， $ y=\frac{1}{2} $， $ z=-\frac{1}{2} $。

（2）（要证  $ E, F, G, H $ 四点共面，只需证  $ \overrightarrow{EG}, \overrightarrow{EF}, \overrightarrow{EH} $ 共面，怎么证？直接把  $ \overrightarrow{EG} $ 用  $ \overrightarrow{EF} $ 和  $ \overrightarrow{EH} $ 表示不易注意到第（1）问已将  $ \overrightarrow{EG} $ 用  $ \overrightarrow{AB}, \overrightarrow{AD}, \overrightarrow{AA_1} $ 表示，故若能将  $ \overrightarrow{EF}, \overrightarrow{EH} $ 也用这三个向量表示，就能用待定系数法找到  $ \overrightarrow{EG} $ 与  $ \overrightarrow{EF}, \overrightarrow{EH} $ 的关系，故按此尝试）由图可知， $ \overrightarrow{EF} = \overrightarrow{ED_1} + \overrightarrow{D_1F} = \frac{1}{2}\overrightarrow{AD} + \frac{1}{2}\overrightarrow{AB} $，

 $ \overrightarrow{EH} = \overrightarrow{EA_1} + \overrightarrow{A_1A} + \overrightarrow{AH} = -\frac{1}{2}\overrightarrow{AD} - \overrightarrow{AA_1} + \frac{1}{2}\overrightarrow{AB} $，由（1）知  $ \overrightarrow{EG} = \overrightarrow{AB} + \frac{1}{2}\overrightarrow{AD} - \frac{1}{2}\overrightarrow{AA_1} $，设  $ \overrightarrow{EG} = \lambda\overrightarrow{EF} + \mu\overrightarrow{EH} $，则  $ \overrightarrow{AB} + \frac{1}{2}\overrightarrow{AD} - \frac{1}{2}\overrightarrow{AA_1} = \lambda\left(\frac{1}{2}\overrightarrow{AD} + \frac{1}{2}\overrightarrow{AB}\right) + \mu\left(-\frac{1}{2}\overrightarrow{AD} - \overrightarrow{AA_1} + \frac{1}{2}\overrightarrow{AB}\right) $，

化简得： $ \overrightarrow{AB} + \frac{1}{2}\overrightarrow{AD} - \frac{1}{2}\overrightarrow{AA_1} = \frac{\lambda + \mu}{2}\overrightarrow{AB} + \frac{\lambda - \mu}{2}\overrightarrow{AD} - \mu\overrightarrow{AA_1} $，所以  $ \begin{cases}1 = \frac{\lambda + \mu}{2}\\ \frac{1}{2} = \frac{\lambda - \mu}{2}\\ -\frac{1}{2} = -\mu\end{cases} $，解得： $ \lambda = \frac{3}{2} $， $ \mu = \frac{1}{2} $，

所以  $ \overrightarrow{EG} = \frac{3}{2}\overrightarrow{EF} + \frac{1}{2}\overrightarrow{EH} $，从而  $ \overrightarrow{EG}, \overrightarrow{EF}, \overrightarrow{EH} $ 共面，故  $ E, F, G, H $ 四点共面。



类型IV：空间向量的数量积