# 第五章 一元函数的导数及其应用

# 5.1 导数的概念及其意义

习题：P1

## 知识梳理

## 知识点 1：变化率与导数的概念

### 1. 物理中的平均速度和瞬时速度


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>平均速度</td><td style='text-align: center; word-wrap: break-word;'>设物体运动的位移与时间的关系是 $ s=s(t) $，从 $ t_0 $到 $ t_0+\Delta t $时间段内的平均速度 $ \overline{v}=\frac{\Delta s}{\Delta t}=\frac{s(t_0+\Delta t)-s(t_0)}{\Delta t} $.</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>瞬时速度</td><td style='text-align: center; word-wrap: break-word;'>我们把物体在某一时刻的速度称为瞬时速度.当 $ \Delta t $无限趋近于0时，平均速度 $ \overline{v}=\frac{\Delta s}{\Delta t}=\frac{s(t_0+\Delta t)-s(t_0)}{\Delta t} $将越来越趋近于物体在 $ t_0 $时刻的瞬时速度.</td></tr></table>

### 2. 平均变化率

一般地，若函数  $ y = f(x) $ 的定义域为  $ D $，且  $ x_1, x_2 \in D $， $ x_1 \neq x_2 $， $ y_1 = f(x_1) $， $ y_2 = f(x_2) $，则称  $ \Delta x = x_2 - x_1 $ 为自变量的改变量；称  $ \Delta y = y_2 - y_1 $（或  $ \Delta f = f(x_2) - f(x_1) $）为相应的因变量的改变量；称  $ \frac{\Delta y}{\Delta x} = \frac{y_2 - y_1}{x_2 - x_1} $（或  $ \frac{\Delta f}{\Delta x} = \frac{f(x_2) - f(x_1)}{x_2 - x_1} $）为函数  $ y = f(x) $ 在  $ [x_1, x_2] $ 上的平均变化率。

注：①两个“改变量”可以是正数或负数，但 $ \Delta x $为分母，所以不能为0.

②平均变化率为0不能说明该函数在此区间上的函数值都相等，如 $ f(x)=|x| $在 $ [-1,1] $上的平均变化率为0，但 $ f(x) $在 $ [-1,1] $上先递减后递增.

### 3. 导数（瞬时变化率）

若当  $ \Delta x $ 无限趋近于 0（记作  $ \Delta x \to 0 $）时，平均变化率  $ \frac{\Delta y}{\Delta x} = \frac{f(x_0 + \Delta x) - f(x_0)}{\Delta x} $ 无限趋近于某确定的值，即  $ \frac{\Delta y}{\Delta x} $ 有极限，则称  $ y = f(x) $ 在  $ x = x_0 $ 处可导，并把该确定值叫做

## 知识点1

【例1】某质点沿直线运动，其位移 s（单位：m）与时间 t（单位：s）之间的关系为  $ s(t)=t^{2} $，则该质点在  $ [1,1+\Delta t] $ 内的平均速度是（）

A.  $ 2 + \Delta t $ B.  $ 2 - \Delta t $

C.  $ -1+2\Delta t $ D.  $ -2+\Delta t $

解析：由题意，该质点的运动时间为  $ \Delta t $，

其位移  $ \Delta s = s(1 + \Delta t) - s(1) = (1 + \Delta t)^2 - 1^2 $

 $ = 2\Delta t + (\Delta t)^2 $，

所以平均速度  $ \bar{v} = \frac{\Delta s}{\Delta t} = \frac{2\Delta t + (\Delta t)^2}{\Delta t} = 2 + \Delta t $。

答案：A

【例2】下列函数中，在区间[1,2]上的平均变化率最大的是（）

A.  $ y=x^{3} $ B. y=2x+1

C.  $ y=2^{x} $ D.  $ y=\log_{2}x $

解析：A 项，$\Delta x = 2 - 1 = 1$，$\Delta y = 2^3 - 1^3 = 7$，所以平均变化率为 $\frac{\Delta y}{\Delta x} = 7$；B 项，$\Delta y = 2 \times 2 + 1 - (2 \times 1 + 1) = 2$，所以平均变化率为 $\frac{\Delta y}{\Delta x} = 2$；C 项，$\Delta y = 2^2 - 2^1 = 2$，所以 $\frac{\Delta y}{\Delta x} = 2$；D 项，$\Delta y = \log_2 2 - \log_2 1 = 1$，所以 $\frac{\Delta y}{\Delta x} = 1$；综上所述，A 项的平均变化率最大。

答案：A

【例 3】若  $ f(x)=x^{2} $，则  $ f'(1)= $ ___.

解析：求函数在某一点处的导数，可套用导数的定义，