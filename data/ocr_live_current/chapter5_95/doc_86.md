解：（1）当 $ a=1 $时， $ f(x)=(x-1)e $， $ x\in\mathbb{R} $，所以 $ f(x)=xe $，从而 $ f(x)>0<x>0 $， $ f(x)<0<x<0 $，故 $ f(x) $在 $ (-\infty,0) $上单调递减，在 $ (0,+\infty) $上单调递增。

（2）因为当 $ x>0 $时， $ f(x)<-1 $，所以 $ xe^{\omega x}-e^x+1<0 $ ①，

（经尝试，直接构造函数求导分析较困难，且造成困难的原因主要是无论求多少次导，式子中总会同时有 $ e^{\omega x} $和 $ e^x $，于是可考虑将 $ e^x $换元成 $ t $，这样求两次导后就不再含有 $ t $这一项的残留了）

令 $ t=e^x $，则 $ t>1 $，且 $ x=\ln t $，不等式①即为 $ t^a\ln t-t+1<0 $，

设 $ g(t)=t^a\ln t-t+1 $， $ t>1 $，则 $ g(t)<0 $，且 $ g'(t)=at^{a-1}\ln t+t^{a-1}-1 $，

 $ g''(t)=a(a-1)t^{a-2}\ln t+at^{a-1}\cdot\frac{1}{t}+(a-1)t^{a-2}=a(a-1)t^{a-2}\ln t+at^{a-2}+(a-1)t^{a-2}=t^{a-2}[a(a-1)\ln t+2a-1] $，

（到此可发现只要有 $ a $的范围，就能判断 $ g''(t) $的正负，故不用再求导了。接下来对参数进行讨论，讨论的分界点怎么找呢？观察可得 $ g(1)=g'(1)=0 $，有端点效应，故要使 $ g(t)<0 $，应有 $ g''(1)=2a-1\leq0 $，据此可找到讨论的分界点）

当 $ a\leq\frac{1}{2} $时，（此时可猜测 $ g(t)<0 $是恒成立的，故先将参数进行放缩，转化为无参的不等式来证明）

 $ g(t)\leq\sqrt{t}\ln t-t+1=\sqrt{t}\left(\ln t-\sqrt{t}+\frac{1}{\sqrt{t}}\right)=\sqrt{t}\left(2\ln\sqrt{t}-\sqrt{t}+\frac{1}{\sqrt{t}}\right) $，设 $ \varphi(u)=2\ln u-u+\frac{1}{u} $， $ u>1 $，

则 $ \varphi'(u)=\frac{2}{u}-1-\frac{1}{u^2}=-\frac{(u-1)^2}{u^2}<0 $，所以 $ \varphi(u) $在 $ (1,+\infty) $上单调递减，又 $ \varphi(1)=0 $，所以 $ \varphi(u)<0 $，

取 $ u=\sqrt{t} $可得 $ 2\ln\sqrt{t}-\sqrt{t}+\frac{1}{\sqrt{t}}<0 $，所以 $ g(t)\leq\sqrt{t}\left(2\ln\sqrt{t}-\sqrt{t}+\frac{1}{\sqrt{t}}\right)<0 $，满足题意；

（还需论证当 $ a>\frac{1}{2} $时， $ g(t)<0 $不能恒成立，观察 $ g'(t) $的解析式可发现在 $ a\geq1 $时，容易得出 $ g'(t)>0 $，故接下来先考虑这种简单的情况）

当 $ a\geq1 $时， $ g'(t)=at^{a-1}\ln t+t^{a-1}-1>t^{a-1}-1\geq0 $，所以 $ g(t) $在 $ (1,+\infty) $上单调递增，

又 $ g(1)=0 $，所以 $ g(t)>0 $恒成立，不合题意；

 $$ a=1 $$ 

 $$ f(x)=(x-1)\mathrm{e}^{x},\quad x\in\mathbf{R} $$ 

 $$ f^{\prime}(x)=x\mathrm{e}^{x} $$ 

 $$ f^{\prime}(x)>0\Leftrightarrow x>0,\quad f^{\prime}(x)<0\Leftrightarrow x<0 $$ 

（最后再看 $ \frac{1}{2}<a<1 $时的情形，此时 $ g'(t) $不易直接判断正负，但 $ g''(t) $可以，故先判断 $ g''(t) $的正负）当 $ \frac{1}{2}<a<1 $时， $ g''(t)>0\Leftrightarrow a(a-1)\ln t+2a-1>0\Leftrightarrow a(1-a)\ln t<2a-1\Leftrightarrow\ln t<\frac{2a-1}{a(1-a)}\Leftrightarrow1<t<\mathrm{e}^{\frac{2a-1}{a(1-a)}} $，所以 $ g'(t) $在 $ \left(1,\mathrm{e}^{\frac{2a-1}{a(1-a)}}\right) $上单调递增，又 $ g'(1)=0 $，所以 $ g'(t)>0 $在 $ \left(1,\mathrm{e}^{\frac{2a-1}{a(1-a)}}\right) $上恒成立，故 $ g(t) $在 $ \left(1,\mathrm{e}^{\frac{2a-1}{a(1-a)}}\right) $上单调递增，因为 $ g(1)=0 $，所以当 $ t\in\left(1,\mathrm{e}^{\frac{2a-1}{a(1-a)}}\right) $时， $ g(t)>0 $，不合题意；综上所述，实数 $ a $的取值范围是 $ \left(-\infty,\frac{1}{2}\right] $。

（3）（目标不等式左侧为求和结构，且无法直接求和，故考虑将右侧也化为求和结构，通过比较左右两侧的通项来证明目标不等式，可按 $ \ln(n+1)=[\ln(n+1)-\ln n]+[\ln n-\ln(n-1)]+\cdots+(\ln 3-\ln 2)+(\ln 2-\ln 1) $来化，此式右侧可写成 $ \sum_{k=1}^{n}[\ln(k+1)-\ln k] $，即 $ \sum_{k=1}^{n}\ln\frac{k+1}{k} $，目标不等式左侧为 $ \sum_{k=1}^{n}\frac{1}{\sqrt{k^2+k}} $，故只需证 $ \frac{1}{\sqrt{k^2+k}}>\ln\frac{k+1}{k} $，直接构造函数求导来证可行，但第（2）问我们得到了不等式 $ 2\ln u-u+\frac{1}{u}<0(u>1) $，所以先试试看能否由它直接变出 $ \frac{1}{\sqrt{k^2+k}}>\ln\frac{k+1}{k} $，为了产生 $ \ln\frac{k+1}{k} $，可取 $ u=\sqrt{\frac{k+1}{k}} $）

由（2）可得当 $ u>1 $时， $ 2\ln u-u+\frac{1}{u}<0 $，取 $ u=\sqrt{\frac{k+1}{k}}(k\in\mathbb{N}^*) $可得 $ 2\ln\sqrt{\frac{k+1}{k}}-\sqrt{\frac{k+1}{k}}+\frac{1}{\sqrt{\frac{k+1}{k}}}<0 $，