从概念层面来看，空间向量与平面向量有很多类似的地方。我们学习空间向量的目的是希望能用它来解决一些立体几何问题，所以本节核心题型的设计思路都是从概念出发，再到应用。首先我们设计了类型Ⅰ来巩固空间向量的线性运算，接着又设计了两组题（类型Ⅱ的利用空间向量证平行、共线和类型Ⅲ的利用空间向量证共面）来强化空间向量线性运算的应用，类型Ⅳ针对空间向量的数量积计算，巩固了数量积的概念后，我们又设计了类型V和类型VI这两组题来教大家如何用数量积来解决长度、距离、角度的问题。请同学们跟着例题和反思好好去学习、体悟吧。

## 类型 I：空间向量的线性运算

【例9】化简下列算式：

(1)  $ 3(2a - b - 4c) - 4(a - 2b + 3c) $; (2)  $ \overrightarrow{OA} - [\overrightarrow{OB} - (\overrightarrow{AB} - \overrightarrow{AC})] $.

解：（1） $ 3(2a-b-4c)-4(a-2b+3c)=6a-3b-12c-4a+8b-12c=2a+5b-24c $

（2） $ \overrightarrow{OA}-[\overrightarrow{OB}-(\overrightarrow{AB}-\overrightarrow{AC})]=\overrightarrow{OA}-\overrightarrow{OB}+(\overrightarrow{AB}-\overrightarrow{AC})=\overrightarrow{OA}+\overrightarrow{BO}+(\overrightarrow{AB}+\overrightarrow{CA})=\overrightarrow{BO}+\overrightarrow{OA}+(\overrightarrow{CA}+\overrightarrow{AB})=\overrightarrow{BO}+\overrightarrow{OA}+\overrightarrow{CB}=\overrightarrow{BA}+\overrightarrow{CB}=\overrightarrow{CB}+\overrightarrow{BA}=\overrightarrow{CA} $

【例 10】在平行六面体  $ ABCD-A_1B_1C_1D_1 $ 中，化简下列表达式，并在图中标出化简结果的向量.



(1)  $ \overrightarrow{DC} + \overrightarrow{A_1D_1} + \frac{1}{2}\overrightarrow{CC_1} $; (2)  $ \overrightarrow{AA_1} + \frac{1}{2}\overrightarrow{AB} + \frac{1}{2}\overrightarrow{AD} $.

<div style="text-align: center;"><img src="imgs/img_in_image_box_867_654_1095_827.jpg" alt="Image" width="19%" /></div>


解：（1）（所给向量没有连成首尾相接的形式，不方便直接相加，怎么办呢？由于图形是平行六面体，有丰富的平行关系，所以可考虑通过平移一些向量来使相加的向量连成首尾相接的形式）

设 $P$ 为 $CC_1$ 的中点，则如图 1，$\overrightarrow{DC} + \overrightarrow{A_1D_1} + \frac{1}{2}\overrightarrow{CC_1} = \overrightarrow{DC} + \overrightarrow{AD} + \overrightarrow{CP} = \overrightarrow{AD} + \overrightarrow{DC} + \overrightarrow{CP} = \overrightarrow{AP}$。

<div style="text-align: center;"><img src="imgs/img_in_image_box_341_979_565_1153.jpg" alt="Image" width="18%" /></div>


<div style="text-align: center;">图1</div>


<div style="text-align: center;"><img src="imgs/img_in_image_box_623_981_849_1152.jpg" alt="Image" width="18%" /></div>


<div style="text-align: center;">图2</div>


（2）（相加的三项中，后两项的系数都是 $ \frac{1}{2} $，故可考虑先把这两项提 $ \frac{1}{2} $出来，再相加）

如图2，设 $ A_1C_1 \cap B_1D_1 = O $，则 $ O $为 $ A_1C_1 $的中点，所以 $ \frac{1}{2}\overrightarrow{AB} + \frac{1}{2}\overrightarrow{AD} = \frac{1}{2}(\overrightarrow{AB} + \overrightarrow{AD}) = \frac{1}{2}\overrightarrow{AC} $，

故 $ \overrightarrow{AA_1} + \frac{1}{2}\overrightarrow{AB} + \frac{1}{2}\overrightarrow{AD} = \overrightarrow{AA_1} + \frac{1}{2}\overrightarrow{AC} = \overrightarrow{AA_1} + \frac{1}{2}\overrightarrow{A_1C_1} = \overrightarrow{AA_1} + \overrightarrow{A_1O} = \overrightarrow{AO} $。

【反思】对于空间向量的线性运算，其处理方法与平面向量的线性运算类似。若参与运算的向量是用诸如a，b，c这种符号表示的，则只需将算式展开，再合并同类项；若参与运算的向量是用起点和终点表示的，则常通过平移来产生有关运算法则需要的图形（如连成首尾相接，或构成平行四边形等），再进行运算。

## 类型Ⅱ：利用空间向量证明平行、共线