答案：ACD

【反思】遇到平方和为常数的双变量式子  $ [f(a)]^2 + [g(b)]^2 = M^2 $，可尝试将其变形成  $ \left[\frac{f(a)}{M}\right]^2 + \left[\frac{g(b)}{M}\right]^2 = 1 $，再令  $ \frac{f(a)}{M} = \cos\alpha $， $ \frac{g(b)}{M} = \sin\alpha $，若由此二式能反解出  $ a $ 和  $ b $，就能将变量统一成  $ \alpha $，便于后续分析。

## 类型IV：动态二面角问题中的三角方法

【例 6】（2012·浙江卷）已知矩形  $ ABCD $ 中， $ AB=1 $， $ BC=\sqrt{2} $，将  $ \triangle ABD $ 沿对角线  $ BD $ 所在的直线翻折，在翻折过程中（ ）

A. 存在某个位置，使得直线  $ AC $ 与直线  $ BD $ 垂直

B. 存在某个位置，使得直线  $ AB $ 与直线  $ CD $ 垂直

C. 存在某个位置，使得直线  $ AD $ 与直线  $ BC $ 垂直

D. 对任意位置，直线 “ $ AC $ 与  $ BD $”，“ $ AB $ 与  $ CD $”，“ $ AD $ 与  $ BC $” 均不垂直

解：由角  $ A-BD-C $ 的大小确定，故先作出该二面角的平面角，再作观察，

如图1，在矩形  $ ABCD $ 中，过  $ A $ 作  $ AE \perp BD $ 于  $ O $ 交  $ BC $ 于  $ E $，由题意， $ BD = \sqrt{3} $，

由  $ S_{\triangle ABD} = \frac{1}{2}AB \cdot AD = \frac{1}{2}BD \cdot AO $ 可得  $ AO = \frac{AB \cdot AD}{BD} = \frac{\sqrt{6}}{3} $，所以  $ BO = \sqrt{AB^2 - AO^2} = \frac{\sqrt{3}}{3} = \frac{1}{3}BD $，

故  $ O $ 为  $ BD $ 的一个三等分点， $ OD = \frac{2\sqrt{3}}{3} $，在如图2所示的三棱锥  $ A-BCD $ 中， $ BD \perp OA $， $ BD \perp OE $，

所以  $ BD \perp $ 平面  $ AOE $，怎样建系比较方便？观察图2可发现，核心是要让点  $ A $ 的坐标好写，注意到点  $ A $ 的位置

由  $ \angle AOE $ 确定，故可考虑以  $ O $ 为原点建系，并设  $ \angle AOE $ 为变量，用该变量表示点  $ A $ 的坐标，

以  $ O $ 为原点建立如图2所示的空间直角坐标系，设  $ \angle AOE = \theta $，其中  $ 0^\circ \leq \theta < 180^\circ $，

<div style="text-align: center;"><img src="imgs/img_in_image_box_198_966_392_1111.jpg" alt="Image" width="16%" /></div>


<div style="text-align: center;">图1</div>


<div style="text-align: center;"><img src="imgs/img_in_image_box_461_956_724_1114.jpg" alt="Image" width="22%" /></div>


<div style="text-align: center;">图2</div>


<div style="text-align: center;"><img src="imgs/img_in_image_box_769_962_992_1123.jpg" alt="Image" width="18%" /></div>


<div style="text-align: center;">图3</div>


为了找到点  $ A $ 的坐标，需先作  $ A $ 在平面  $ BCD $ 内的射影，再分析几何关系。方便起见，先看  $ \theta $ 为锐角的情形当  $ \theta $ 为锐角时，如图2，作  $ AI \perp OE $ 于点  $ I $，由  $ BD \perp $ 平面  $ AOE $ 可知， $ AI \perp BD $，所以  $ AI \perp $ 平面  $ BCD $，在  $ \triangle AOI $ 中， $ OI = AO \cdot \cos \angle AOI = \frac{\sqrt{6}}{3} \cos \theta $， $ AI = AO \cdot \sin \angle AOI = \frac{\sqrt{6}}{3} \sin \theta $，所以  $ A\left(0, \frac{\sqrt{6}}{3} \cos \theta, \frac{\sqrt{6}}{3} \sin \theta\right) $，可以想象，上述点  $ A $ 的坐标对  $ \theta = 0^\circ $ 或  $ \theta $ 为直角、钝角时也成立，于是所有情况下点  $ A $ 的坐标就都有了，由图2和图3可知， $ B\left(\frac{\sqrt{3}}{3}, 0, 0\right) $， $ C\left(-\frac{\sqrt{3}}{3}, \frac{\sqrt{6}}{3}, 0\right) $， $ D\left(-\frac{2\sqrt{3}}{3}, 0, 0\right) $，

需要的点的坐标都有了，下面来看选项，四个选项均涉及线线垂直，可用数量积来翻译。

A 项， $ \overrightarrow{AC}=\left(-\frac{\sqrt{3}}{3},\frac{\sqrt{6}}{3}(1-\cos\theta),-\frac{\sqrt{6}}{3}\sin\theta\right) $， $ \overrightarrow{BD}=(-\sqrt{3},0,0) $，所以  $ \overrightarrow{AC}\cdot\overrightarrow{BD}=1\neq0 $，

从而直线 AC 与直线 BD 始终不垂直，故 A 项错误；