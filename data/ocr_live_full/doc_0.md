## 第一章 空间向量与立体几何

### 1.1 空间向量及其运算

习题：P1

## 知识梳理

## 知识点 1：空间向量的相关概念

### 1. 空间向量的定义及表示


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>定义</td><td colspan="2">空间中具有大小和方向的量</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>长度（模）</td><td colspan="2">空间向量的大小</td></tr><tr><td rowspan="3">表示方法</td><td style='text-align: center; word-wrap: break-word;'>几何表示</td><td style='text-align: center; word-wrap: break-word;'>与平面向量一样，空间向量也用有向线段表示，有向线段的长度表示空间向量的模</td></tr><tr><td rowspan="2">符号表示</td><td style='text-align: center; word-wrap: break-word;'>空间向量用字母 a，b，c 等表示，书写体用  $ \overrightarrow{a} $， $ \overrightarrow{b} $， $ \overrightarrow{c} $ 等表示</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>空间向量可用有向线段表示，如图，向量 a 的起点是 A，终点是 B，则向量 a 可记作  $ \overrightarrow{AB} $，其模记为  $ |a| $ 或  $ \left|AB\right| $</td></tr></table>

### 2. 几类特殊的空间向量


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>向量名称</td><td style='text-align: center; word-wrap: break-word;'>方向</td><td style='text-align: center; word-wrap: break-word;'>模</td><td style='text-align: center; word-wrap: break-word;'>记法</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>零向量</td><td style='text-align: center; word-wrap: break-word;'>任意</td><td style='text-align: center; word-wrap: break-word;'>0</td><td style='text-align: center; word-wrap: break-word;'>0, 或0</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>单位向量</td><td style='text-align: center; word-wrap: break-word;'>不作规定</td><td style='text-align: center; word-wrap: break-word;'>1</td><td style='text-align: center; word-wrap: break-word;'>与非零向量a共线的单位向量为 $ \pm\frac{a}{|a|} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>相反向量</td><td style='text-align: center; word-wrap: break-word;'>与原向量相反</td><td style='text-align: center; word-wrap: break-word;'>与原向量相等</td><td style='text-align: center; word-wrap: break-word;'>$ \overrightarrow{a} $的相反向量为 $ -a $， $ \overrightarrow{AB} $的相反向量为 $ \overrightarrow{BA} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>相等向量</td><td style='text-align: center; word-wrap: break-word;'>与原向量相同</td><td style='text-align: center; word-wrap: break-word;'>与原向量相等</td><td style='text-align: center; word-wrap: break-word;'>向量a与向量b相等记作 $ a=b $</td></tr></table>

注：①空间中任意两个向量都是共面的，因为可以通过平移将它们移到同一平面内.

②单位向量与零向量都只是对向量的长度（模）进行了规定，并没有规定方向，因此单位向量和零向量都有无数个，并且规定所有的零向量都相等.

③在空间中，若  $ A, B, C, D $ 不在同一直线上，且  $ \overrightarrow{AB} = \overrightarrow{DC} \Leftrightarrow $ 四边形  $ ABCD $ 为平行四边形.

④空间向量可以平移，若两个空间向量相等，则它们的方向相同、模相等，但起点和终点不一定相同.

## 知识点1

【例 1】如图所示，在长方体  $ ABCD-A_1B_1C_1D_1 $ 中，以长方体的八个顶点中的两点为起点和终点的向量中.

<div style="text-align: center;"><img src="imgs/img_in_image_box_781_502_1031_635.jpg" alt="Image" width="20%" /></div>


（1）试写出与 $ \overrightarrow{AB} $相等的所有向量；

（2）试写出  $ \overrightarrow{AA_{1}} $ 的所有相反向量.

解：（1）（要找与 $ \overrightarrow{AB} $相等的向量，就看哪些向量与 $ \overrightarrow{AB} $方向相同，长度相等）

在长方体  $ ABCD-A_{1}B_{1}C_{1}D_{1} $ 中，DC， $ A_{1}B_{1} $， $ D_{1}C_{1} $ 与 AB 平行且相等，所以与  $ \overrightarrow{AB} $ 相等的向量有  $ \overrightarrow{DC} $， $ \overrightarrow{A_{1}B_{1}} $， $ \overrightarrow{D_{1}C_{1}} $。

（2）在长方体  $ ABCD-A_1B_1C_1D_1 $ 中， $ BB_1 $， $ CC_1 $， $ DD_1 $ 与  $ AA_1 $ 平行且相等，所以  $ \overrightarrow{AA_1} $ 的相反向量有  $ \overrightarrow{A_1A} $， $ \overrightarrow{B_1B} $， $ \overrightarrow{C_1C} $， $ \overrightarrow{D_1D} $。

## 知识点2

【例 2】如图， $ ABCD-A_1B_1C_1D_1 $ 为平行六面体，则  $ \overrightarrow{AB} + \overrightarrow{AD} + \overrightarrow{CC_1} = (\ ) $

A.  $ \overrightarrow{CA} $    B.  $ \overrightarrow{AC} $

C.  $ \overrightarrow{AC_1} $    D.  $ \overrightarrow{C_1A} $

<div style="text-align: center;"><img src="imgs/img_in_image_box_802_1336_1011_1523.jpg" alt="Image" width="17%" /></div>


解析：如图，由空间向量加法的平行四边形