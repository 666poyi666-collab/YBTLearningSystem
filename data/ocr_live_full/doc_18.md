# 1.2 空间向量基本定理

# 1.3 空间向量及其运算的坐标表示

习题：P1

知识梳理

## 知识点 1：空间向量基本定理

### 1. 空间向量基本定理

如果空间中三个向量  $ a $,  $ b $,  $ c $ 不共面，那么对于任意一个空间向量  $ p $，存在唯一的有序实数组  $ (x, y, z) $，使得  $ p = x a + y b + z c $。

### 2. 基底与基向量

如果三个向量  $ a $,  $ b $,  $ c $ 不共面，那么所有空间向量组成的集合就是  $ \{p \mid p = x a + y b + z c, x, y, z \in \mathbb{R}\} $。这个集合可看作由向量  $ a $,  $ b $,  $ c $ 生成的，我们把  $ \{a, b, c\} $ 叫做空间的一个基底， $ a $,  $ b $,  $ c $ 都叫做基向量。空间中任意三个不共面的向量都可以构成空间的一个基底。

注：①基底不是唯一的，只要三个向量不共面，它们就能作为空间中的一个基底；

②一般情况下，同一向量在不同基底下的表示结果不同.

### 3. 单位正交基底

若空间中一个基底的三个基向量两两垂直，且长度都为1，则该基底叫做单位正交基底，常用 $ \{i,j,k\} $表示.

由空间向量基本定理可知，对空间中的任意一个向量  $ a $，均能找到唯一的有序实数组  $ (x, y, z) $，使  $ a = x\mathbf{i} + y\mathbf{j} + z\mathbf{k} $。像这样，把一个空间向量分解为三个两两垂直的向量，叫做把空间向量进行正交分解。

## 知识点2：空间向量的坐标表示

### 1. 空间直角坐标系

在空间选定一点 O 和一个单位正交基底  $ \{i, j, k\} $。如图，以点 O 为原点，分别以  $ i, j, k $ 的方向为正方向，以它们的长为单位长度建立三条数轴：x 轴，y 轴，z 轴，它

## 知识点1

【例 1】平行六面体  $ ABCD-A_1B_1C_1D_1 $ 中，下面一定能作为空间中的一个基底的是（ ）

A.  $ \{\overrightarrow{AB}, \overrightarrow{AD}, \overrightarrow{B_1D_1}\} $

B.  $ \{\overrightarrow{AB}, \overrightarrow{AA_1}, \overrightarrow{C_1D_1}\} $

C.  $ \{\overrightarrow{AB}, \overrightarrow{A_1A}, \overrightarrow{A_1D_1}\} $

D.  $ \{\overrightarrow{AA_1}, \overrightarrow{AC}, \overrightarrow{CC_1}\} $

解析：三个向量能否构成基底，就看这三个向量是否满足不共面，

A 项，如图，平行六面体  $ ABCD-A_1B_1C_1D_1 $ 中， $ \overrightarrow{B_1D_1}=\overrightarrow{BD} $，而  $ \overrightarrow{AB} $， $ \overrightarrow{AD} $， $ \overrightarrow{BD} $ 共面，所以  $ \overrightarrow{AB} $， $ \overrightarrow{AD} $， $ \overrightarrow{B_1D_1} $ 也共面，

从而  $ \{\overrightarrow{AB},\overrightarrow{AD},\overrightarrow{B_1D_1}\} $ 不能作为基底，

故 A 项错误；

B 项， $ \overrightarrow{C_1D_1}=\overrightarrow{CD}=\overrightarrow{BA} $，而  $ \overrightarrow{AB} $， $ \overrightarrow{AA_1} $， $ \overrightarrow{BA} $ 都是平面  $ ABB_1A_1 $ 内的向量，它们共面，

所以  $ \overrightarrow{AB} $， $ \overrightarrow{AA_1} $， $ \overrightarrow{C_1D_1} $ 也共面，

从而  $ \{\overrightarrow{AB},\overrightarrow{AA_1},\overrightarrow{C_1D_1}\} $ 不能作为基底，

故 B 项错误；

C 项，由图可知，由  $ \overrightarrow{AB} $ 和  $ \overrightarrow{A_1A} $ 确定的平面是平面  $ ABB_1A_1 $，而  $ \overrightarrow{A_1D_1} $ 不在该平面内，

所以  $ \overrightarrow{AB} $， $ \overrightarrow{A_1A} $， $ \overrightarrow{A_1D_1} $ 不共面，故 C 项正确；

D 项，由图可知  $ \overrightarrow{AA_1} $， $ \overrightarrow{AC} $， $ \overrightarrow{CC_1} $ 都在平面  $ ACC_1A_1 $ 内，所以它们共面， $ \{\overrightarrow{AA_1},\overrightarrow{AC},\overrightarrow{CC_1}\} $ 不能作为基底，故 D 项错误。

答案：C



<div style="text-align: center;"><img src="imgs/img_in_image_box_804_1346_1008_1516.jpg" alt="Image" width="17%" /></div>
