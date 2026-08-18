### 5.2 导数的运算

习题：P1

## 知识梳理

## 知识点1：基本初等函数的导数

### 1. 基本初等函数的导数


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>函数</td><td style='text-align: center; word-wrap: break-word;'>导数</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=c $（ $ c $为常数）</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=0 $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=x^{\alpha} $（ $ \alpha\in\mathbf{Q} $且 $ \alpha\neq0 $）</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=\alpha x^{\alpha-1} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=\sin x $</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=\cos x $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=\cos x $</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=-\sin x $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=a^{x} $（ $ a&gt;0 $且 $ a\neq1 $）</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=a^{x}\ln a $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=\mathrm{e}^{x} $</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=\mathrm{e}^{x} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=\log_{a}x $（ $ a&gt;0 $且 $ a\neq1 $）</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=\frac{1}{x\ln a} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=\ln x $</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=\frac{1}{x} $</td></tr></table>

### 2. 常用函数的导数


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>函数</td><td style='text-align: center; word-wrap: break-word;'>导数</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=x $</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=(x^1)&#x27;=1\cdot x^{1-1}=1 $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=x^2 $</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=(x^2)&#x27;=2x $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=x^3 $</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=(x^3)&#x27;=3x^2 $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=\frac{1}{x} $</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=\left(\frac{1}{x}\right)&#x27;=(x^{-1})&#x27;=-1\cdot x^{-1-1}=-\frac{1}{x^2} $</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>$ f(x)=\sqrt{x} $</td><td style='text-align: center; word-wrap: break-word;'>$ f&#x27;(x)=(\sqrt{x})&#x27;=\left(x^{\frac{1}{2}}\right)&#x27;=\frac{1}{2}x^{\frac{1}{2}-1}=\frac{1}{2\sqrt{x}} $</td></tr></table>

注：若函数解析式中含有根式，在求导时一般将其转化为分数指数幂的形式，再利用  $ y=x^{\alpha} $ 的导数公式处理.

## 知识点 2：导数的四则运算法则

若函数  $ f(x) $ 与  $ g(x) $ 均为可导函数，则：

①和差运算： $ [f(x)\pm g(x)]'=f'(x)\pm g'(x) $；

推广： $ [f(x)+g(x)+\cdots+p(x)]'=f'(x)+g'(x)+\cdots+p'(x) $.

②乘积运算： $ [f(x)g(x)]'=f'(x)g(x)+f(x)g'(x) $；

特别地， $ [kf(x)]'=kf'(x)+kf'(x)=kf'(x) $，k为常数.

## 知识点1

【例 1】函数  $ f(x)=\sin x $ 的导函数为  $ f'(x) $，则  $ f'\left(\frac{\pi}{6}\right)= $___。

解析：由题意， $ f'(x)=(\sin x)'=\cos x $，

所以  $ f'\left(\frac{\pi}{6}\right)=\cos\frac{\pi}{6}=\frac{\sqrt{3}}{2} $。

答案： $ \frac{\sqrt{3}}{2} $

【例2】设 $ f(x)=\mathrm{e}^{x} $，若 $ f'(a)=1 $，则

 $ a= $___.

解析：由题意， $ f'(x)=(\mathrm{e}^{x})'=e^{x} $，

所以  $ f'(a) = e^{a} = 1 $，解得：a = 0。

答案：0

【例 3】已知  $ f(x) = \ln x $，则  $ f(x) $ 在点  $ (1, f(1)) $ 处的切线的斜率为___。

解析：由题意， $ f'(x) = (\ln x)' = \frac{1}{x} \Rightarrow f(x) $ 在点  $ (1, f(1)) $ 处的切线斜率  $ k = f'(1) = \frac{1}{1} = 1 $。

答案：1

## 知识点2

【例4】求出下列函数的导数：

(1)  $ f(x)=3^{x}+x^{2} $;

(2)  $ f(x) = -2x^{3} + 4x^{2} $;

(3)  $ f(x) = \sin x \cos x $;

(4)  $ f(x)=\frac{e^{x}}{x^{2}} $.

解：（1）（两函数相加再求导，只需分别求这两个函数的导数再相加即可）

由题意， $ f'(x)=(3^x)'+(x^2)'=3^x\ln3+2x $.