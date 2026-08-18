故 $ \frac{18c^{2}-8a^{2}}{9\sqrt{3}c^{2}}=-\frac{18c^{2}-2a^{2}}{9\sqrt{3}c^{2}} $，化简得椭圆的离心率 $ e=\frac{\sqrt{10}}{6} $。

解法2：注意到 $ |PF_{1}| $， $ |PF_{2}| $， $ |OP| $都容易用点 $ P $的坐标表示，故也可按此翻译已知条件，建立方程求离心率，由焦半径公式， $ |PF_{1}|=a+ex_{p} $， $ |PF_{2}|=a-ex_{p} $，代入 $ |PF_{1}|=2|PF_{2}| $得 $ a+ex_{p}=2(a-ex_{p})\Rightarrow x_{p}=\frac{a}{3e}=\frac{a^{2}}{3c} $，

代入椭圆方程得 $ \frac{a^{2}}{9c^{2}}+\frac{y^{2}}{b^{2}}=1\Rightarrow y^{2}=b^{2}-\frac{a^{2}b^{2}}{9c^{2}} $，所以 $ y_{p}^{2}=b^{2}-\frac{a^{2}b^{2}}{9c^{2}} $，故 $ |OP|=\sqrt{x_{p}^{2}+y_{p}^{2}}=\sqrt{\frac{a^{4}}{9c^{2}}+b^{2}-\frac{a^{2}b^{2}}{9c^{2}}} $

 $ =\sqrt{\frac{a^{2}(a^{2}-b^{2})}{9c^{2}}+b^{2}}=\sqrt{\frac{a^{2}}{9}+b^{2}} $，代入 $ |OP|=\frac{\sqrt{3}}{2}|F_{1}F_{2}| $得 $ \sqrt{\frac{a^{2}}{9}+b^{2}}=\frac{\sqrt{3}}{2}\cdot2c $，

所以 $ \frac{a^{2}}{9}+b^{2}=3c^{2} $，从而 $ \frac{a^{2}}{9}+a^{2}-c^{2}=3c^{2} $，化简得： $ \frac{5a^{2}}{9}=2c^{2} $，故椭圆离心率 $ e=\frac{\sqrt{10}}{6} $。

答案：D

【反思】涉及 $ \left|PF_{1}\right| $和 $ \left|PF_{2}\right| $时，除了联系椭圆定义处理外，还可以考虑用焦半径公式处理，尤其是当问题需要点 $ P $的坐标时，用焦半径公式处理会很方便，我们再来看一个变式1.

【变式 1】已知  $ F_1 $， $ F_2 $ 是椭圆  $ \frac{x^2}{a^2} + \frac{y^2}{b^2} = 1 (a > b > 0) $ 的左、右焦点，若椭圆上存在点  $ P $ 使  $ |PF_1| = 7|PF_2| $，则椭圆的离心率的取值范围是（ ）

A.  $ \left(0, \frac{3}{4}\right) $      B.  $ \left(0, \frac{3}{4}\right] $      C.  $ \left[\frac{3}{4}, 1\right) $      D.  $ \left(\frac{3}{4}, 1\right) $

解法1：怎样翻译$|PF_1|=7|PF_2|$，建立不等式求离心率的范围？注意到椭圆上的点$P$满足$-a\leq x_p\leq a$，故可用焦半径公式翻译$|PF_1|=7|PF_2|$，求出$x_p$，代入$-a\leq x_p\leq a$即可求得离心率的范围，

由焦半径公式，$|PF_1|=a+ex_p$，$|PF_2|=a-ex_p$，代入$|PF_1|=7|PF_2|$得$a+ex_p=7(a-ex_p)\Rightarrow x_p=\frac{3a}{4e}=\frac{3a^2}{4c}$，

因为$-a\leq x_p\leq a$，所以$-a\leq\frac{3a^2}{4c}\leq a$，故$-1\leq\frac{3}{4e}\leq1$，结合$0<e<1$可得$\frac{3}{4}\leq e<1$。

解法2：看到$|PF_1|=7|PF_2|$，也容易想到联系椭圆定义，可求出$|PF_1|$，$|PF_2|$由题意，$|PF_1|=7|PF_2|$，结合$|PF_1|+|PF_2|=2a$可得$|PF_2|=\frac{a}{4}$①，

$|PF_2|$有天然的范围吗？若有就能结合式①建立不等式，求离心率的范围，我们结合焦半径公式来看看。

因为$|PF_2|=a-ex_p=a-\frac{c}{a}x_p$，且$-a\leq x_p\leq a$，所以$a-c\leq|PF_2|\leq a+c$，

结合①得$a-c\leq\frac{a}{4}\leq a+c$，同时除以$a$可得$1-e\leq\frac{1}{4}\leq1+e$，所以$e\geq\frac{3}{4}$，结合$0<e<1$可得$\frac{3}{4}\leq e<1$。

答案：C

【变式 2】已知椭圆  $ C:\frac{x^{2}}{a^{2}}+\frac{y^{2}}{b^{2}}=1(a>b>0) $ 的左焦点为  $ F $，经过点  $ F $ 且倾斜角为  $ 30^{\circ} $ 的直线与  $ C $ 交于  $ A $， $ B $ 两点，若  $ |AF|=3|BF| $，则  $ C $ 的离心率为（ ）

A.  $ \frac{1}{3} $ \quad B.  $ \frac{\sqrt{3}}{3} $ \quad C.  $ \frac{\sqrt{2}}{2} $ \quad D.  $ \frac{2}{3} $

解法 1：条件  $ \left|AF\right|=3\left|BF\right| $ 怎么用？注意到给出了直线 AB 的倾斜角，故考虑用角版焦半径公式计算  $ \left|AF\right|,\left|BF\right| $