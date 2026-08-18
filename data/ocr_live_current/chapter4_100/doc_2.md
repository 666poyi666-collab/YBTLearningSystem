系可以用一个式子来表示，那么这个式子叫做这个数列的前n项和公式.

显然  $ S_{1}=a_{1} $，而  $ S_{n-1}=a_{1}+a_{2}+\cdots+a_{n-1}(n\geq2) $，

所以  $ S_{n}-S_{n-1}=a_{n} $，于是我们有  $ a_{n}=\left\{\begin{aligned}&S_{1},n=1\\&S_{n}-S_{n-1},n\geq2\end{aligned}\right. $

注：对于由  $ a_n = S_n - S_{n-1} (n \geq 2) $ 求得的  $ a_n $ 的表达式  $ a_n = f(n) $，若  $ f(1) $ 恰好与利用  $ a_1 = S_1 $ 求得的  $ a_1 $ 相同，则说明  $ a_n = f(n) (n \geq 2) $ 也适合  $ n = 1 $ 的情况， $ a_n $ 可统一用  $ a_n = f(n) $ 表示；若  $ f(1) $ 与利用  $ a_1 = S_1 $ 求得的  $ a_1 $ 不同，则  $ a_n $ 应采用分段形式表示，即  $ a_n = \left\{ \begin{aligned} S_1, & n = 1 \\ S_n - S_{n-1}, & n \geq 2 \end{aligned} \right. $

## 知识点 5：数列的单调性

### 1 \. 数列的分类（按单调性分）


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>递增数列</td><td style='text-align: center; word-wrap: break-word;'>从第2项起，每一项都大于它的前一项的数列</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>递减数列</td><td style='text-align: center; word-wrap: break-word;'>从第2项起，每一项都小于它的前一项的数列</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>常数数列</td><td style='text-align: center; word-wrap: break-word;'>各项都相等的数列</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>摆动数列</td><td style='text-align: center; word-wrap: break-word;'>从第2项起，有些项大于它的前一项，有些项小于它的前一项的数列</td></tr></table>

2. 数列单调性的判断

①作差法和作商法：

对任意的数列  $ \{a_n\} $，有

 $ a_{n+1} - a_n > 0 \Leftrightarrow a_{n+1} > a_n \Leftrightarrow \{a_n\} $ 为递增数列；

 $ a_{n+1} - a_n < 0 \Leftrightarrow a_{n+1} < a_n \Leftrightarrow \{a_n\} $ 为递减数列。

对正项数列  $ \{a_n\} $，有

 $ \frac{a_{n+1}}{a_n} > 1 \Leftrightarrow a_{n+1} > a_n \Leftrightarrow \{a_n\} $ 为递增数列；

 $ \frac{a_{n+1}}{a_n} < 1 \Leftrightarrow a_{n+1} < a_n \Leftrightarrow \{a_n\} $ 为递减数列。

②结合数列图象判断；

③利用对应的函数的单调性判断。

## 知识点3

【例6】已知数列$\{a_n\}$满足$a_1=24$，

$a_{n+1}=\frac{1}{2}a_n$，则$a_3=$（ ）

A. 6          B. 7

C. 8          D. 9

解析：因为 $ a_{n+1}=\frac{1}{2}a_n $，所以当n=1时，

 $ a_2=\frac{1}{2}a_1=\frac{1}{2}\times24=12 $，

当n=2时， $ a_3=\frac{1}{2}a_2=\frac{1}{2}\times12=6 $。

答案：A

## 知识点4

【例 7】数列 $\{a_n\}$ 中，$a_1=2$，$a_{n+1}-a_n=2n+2(n\in\mathbb{N}^*)$，则数列 $\left\{\frac{1}{a_n}\right\}$ 的前 4 项的和为 ___.

解析：由题意， $ a_{n+1}-a_n=2n+2 $，

所以 $ a_{n+1}=a_n+2n+2 $，

当n=1时， $ a_2=a_1+2\times1+2=a_1+4=6 $，

当n=2时， $ a_3=a_2+2\times2+2=a_2+6=12 $，

当n=3时， $ a_4=a_3+2\times3+2=a_3+8=20 $，

所以 $ \frac{1}{a_1}+\frac{1}{a_2}+\frac{1}{a_3}+\frac{1}{a_4}=\frac{1}{2}+\frac{1}{6}+\frac{1}{12}+\frac{1}{20}=\frac{4}{5} $。

答案： $ \frac{4}{5} $

【例 8】若数列 $\{a_n\}$ 满足 $a_n = \frac{n-1}{n(n+1)}$，

则 $\{a_n\}$ 的前 3 项和 $S_3 = $___。

解析：由题意，$a_1 = \frac{1-1}{1 \times (1+1)} = 0$，

$a_2 = \frac{2-1}{2 \times (2+1)} = \frac{1}{6}$，$a_3 = \frac{3-1}{3 \times (3+1)} = \frac{1}{6}$，

所以 $S_3 = a_1 + a_2 + a_3 = 0 + \frac{1}{6} + \frac{1}{6} = \frac{1}{3}$。

答案：$\frac{1}{3}$