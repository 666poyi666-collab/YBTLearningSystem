所以与  $ a $ 平行的单位向量是  $ \pm \frac{1}{\sqrt{6}}a = \left(-\frac{\sqrt{6}}{6}, \frac{\sqrt{6}}{3}, \frac{\sqrt{6}}{6}\right) $ 或  $ \left(\frac{\sqrt{6}}{6}, -\frac{\sqrt{6}}{3}, -\frac{\sqrt{6}}{6}\right) $.

答案：（1） $ (-1,-9,4) $；（2） $ \sqrt{186} $；（3） $ \left(-\frac{\sqrt{6}}{6},\frac{\sqrt{6}}{3},\frac{\sqrt{6}}{6}\right) $或 $ \left(\frac{\sqrt{6}}{6},-\frac{\sqrt{6}}{3},-\frac{\sqrt{6}}{6}\right) $

【例 7】（1）已知空间四点  $ A(1,2,3) $， $ B(1,1,2) $， $ C(2,1,1) $， $ D(1,1,1) $，则  $ \overrightarrow{AB} - 2\overrightarrow{CD} = $ ___；

（2）在空间四边形 $ABCD$ 中，$\overrightarrow{AB}=(1,3,2)$，$\overrightarrow{BC}=(-2,-3,1)$，$\overrightarrow{AD}=(3,1,2)$，则 $\overrightarrow{CD}=$___。

解析：（1）由题意，$\overrightarrow{AB}=(1,1,2)-(1,2,3)=(1-1,1-2,2-3)=(0,-1,-1)$，$\overrightarrow{CD}=(1,1,1)-(2,1,1)=(1-2,1-1,1-1)=(-1,0,0)$，

所以 $\overrightarrow{AB}-2\overrightarrow{CD}=(0,-1,-1)-2(-1,0,0)=(0,-1,-1)-(-2,0,0)=(0-(-2),-1-0,-1-0)=(2,-1,-1)$。

（2）怎样由所给向量求  $ \overrightarrow{CD} $？观察发现可按  $ \overrightarrow{CD} = \overrightarrow{AD} - \overrightarrow{AC} = \overrightarrow{AD} - (\overrightarrow{AB} + \overrightarrow{BC}) $ 来计算，由题意， $ \overrightarrow{CD} = \overrightarrow{AD} - (\overrightarrow{AB} + \overrightarrow{BC}) = \overrightarrow{AD} - \overrightarrow{AB} - \overrightarrow{BC} = (3,1,2) - (1,3,2) - (-2,-3,1) $

 $ = (3-1-(-2),1-3-(-3),2-2-1) = (4,1,-1) $.

答案：（1）（2,-1,-1）；（2）（4,1,-1）

【反思】空间向量的线性运算坐标表示规则与平面向量的线性运算坐标表示规则类似，对于数乘运算，每个分量都要乘以相应的实数；加、减法运算时，对应坐标相加、减；向量  $ \overrightarrow{AB} $ 的坐标为“终点减起点”。这些规则务必熟悉，在后续章节用空间向量解决立体几何问题时会反复用到。

## 类型Ⅲ：空间向量数量积的坐标表示

【例 8】若向量  $ \boldsymbol{a} = (2, -3, 1) $， $ \boldsymbol{b} = (2, 0, 3) $， $ \boldsymbol{c} = (1, 2, 2) $，则  $ \boldsymbol{a} \cdot (\boldsymbol{b} + \boldsymbol{c}) $ 的值为（）

A. 4 B. 5 C. 6 D. 7

解析：由题意， $ b + c = (2,0,3) + (1,2,2) = (3,2,5) $，又 $ a = (2,-3,1) $，所以 $ a \cdot (b + c) = 2 \times 3 + (-3) \times 2 + 1 \times 5 = 5 $。

答案：B

【例 9】已知点  $ A(2,-1,1) $， $ B(3,-2,1) $， $ C(0,1,-1) $，则  $ \overrightarrow{AB} $ 在  $ \overrightarrow{AC} $ 上的投影向量的坐标为 ___.

解析：求投影向量，考虑  $ a $ 在  $ b $ 上的投影向量计算公式  $ \frac{a \cdot b}{|b|^2} b $，代此公式需要  $ a, b $ 的坐标，于是下面先求  $ \overrightarrow{AB} $ 和  $ \overrightarrow{AC} $ 的坐标，由题意， $ \overrightarrow{AB} = (3, -2, 1) - (2, -1, 1) = (1, -1, 0) $， $ \overrightarrow{AC} = (0, 1, -1) - (2, -1, 1) = (-2, 2, -2) $，所以  $ \overrightarrow{AB} \cdot \overrightarrow{AC} = 1 \times (-2) + (-1) \times 2 + 0 \times (-2) = -4 $， $ \left|\overrightarrow{AC}\right|^2 = (-2)^2 + 2^2 + (-2)^2 = 12 $，故由投影向量计算公式， $ \overrightarrow{AB} $ 在  $ \overrightarrow{AC} $ 上的投影向量为  $ \frac{\overrightarrow{AB} \cdot \overrightarrow{AC}}{|\overrightarrow{AC}|^2} \overrightarrow{AC} = \frac{-4}{12} \overrightarrow{AC} = -\frac{1}{3} \overrightarrow{AC} = -\frac{1}{3}(-2, 2, -2) = \left(\frac{2}{3}, -\frac{2}{3}, \frac{2}{3}\right) $。

答案： $ \left(\frac{2}{3},-\frac{2}{3},\frac{2}{3}\right) $

【反思】关于数量积、投影向量计算公式，空间向量与平面向量类似，它们是后续章节利用空间向量解决立体几何问题的基础，务必熟悉。