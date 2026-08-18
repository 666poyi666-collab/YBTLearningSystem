【例 4】设  $ f(x)=\frac{4^x}{4^x+2} $，记  $ S=f\left(\frac{1}{101}\right)+f\left(\frac{2}{101}\right)+f\left(\frac{3}{101}\right)+\cdots+f\left(\frac{100}{101}\right) $，则  $ S= $___。

解析：可以想象， $ f\left(\frac{1}{101}\right) $， $ f\left(\frac{2}{101}\right) $，⋯， $ f\left(\frac{100}{101}\right) $都不易代入解析式计算，怎么办呢？可尝试将和式中的某些项组合，注意到 $ \frac{1}{101}+\frac{100}{101}=\frac{2}{101}+\frac{99}{101}=\cdots=\frac{50}{101}+\frac{51}{101}=1 $，所以不妨看看当两个自变量之和为1时，它们的函数值之和有无规律，于是先计算 $ f(x)+f(1-x) $，

由题意， $ f(x)+f(1-x)=\frac{4^x}{4^x+2}+\frac{4^{1-x}}{4^{1-x}+2}=\frac{4^x}{4^x+2}+\frac{4}{4+2\times4^x}=\frac{4^x}{4^x+2}+\frac{2}{2+4^x}=\frac{4^x+2}{4^x+2}=1 $，

由题意， $ f(x) = \frac{1}{x^2} - 4x + 2 $， $ 4^{1-x} + 2 - 4x + 2 - 4x + 2 - 4x + 2 - 4x + 2 = -1 $。

确实有规律，故求和时两组合，把自变量凑成和为1的结构，为了便于观察，我们采用倒序相加法，

因为 $ S = f\left(\frac{1}{101}\right) + f\left(\frac{2}{101}\right) + f\left(\frac{3}{101}\right) + \cdots + f\left(\frac{100}{101}\right) $，所以 $ S = f\left(\frac{100}{101}\right) + f\left(\frac{99}{101}\right) + f\left(\frac{98}{101}\right) + \cdots + f\left(\frac{1}{101}\right) $，

两式相加得 $ 2S = \left[f\left(\frac{1}{101}\right) + f\left(\frac{100}{101}\right)\right] + \left[f\left(\frac{2}{101}\right) + f\left(\frac{99}{101}\right)\right] + \left[f\left(\frac{3}{101}\right) + f\left(\frac{98}{101}\right)\right] + \cdots + \left[f\left(\frac{100}{101}\right) + f\left(\frac{1}{101}\right)\right] = 1 + 1 + 1 + \cdots + 1 $（共100个1）=100，所以 $ S = 50 $。

答案：50

【反思】在求和时，若需要将关于中间对称的两项组合，则可采用倒序相加法.

## 强化训练

## A 组 夯实基础

1. (2025·广东模拟)

已知数列 $\{a_n\}$，$\{b_n\}$ 分别是等差、等比数列，且 $a_1 = -1$，$a_2 = b_1 = 1$，$b_2 = a_3$。

（1）求 $ \{a_{n}\} $， $ \{b_{n}\} $的通项公式；

（2）求数列 $ \left\{a_{n}+2b_{n}\right\} $的前n项和 $ S_{n} $

B组 强化能力

2.（2025·全国模拟）

若  $ f(x)=\frac{2x}{2x-1} $，则  $ f\left(\frac{1}{2025}\right)+f\left(\frac{2}{2025}\right)+\cdots+ $

 $ f\left(\frac{2024}{2025}\right)= $ ___.