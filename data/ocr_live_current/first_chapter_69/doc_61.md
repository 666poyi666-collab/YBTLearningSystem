$D_1Q \perp$ 平面 $A_1PD$ 等价于 $\overrightarrow{DQ} // m$，即存在常数 $\lambda$ 使 $\overrightarrow{DQ} = \lambda m$，也即 $\begin{cases} a = 3\lambda \\ 1 = -2\lambda \\ b - 1 = -3\lambda \end{cases}$，解得：$a = -\frac{3}{2}$，$b = \frac{5}{2}$，

不满足 $0 \leq a \leq 1$，$0 \leq b \leq 1$，所以不存在点 $Q$ 使 $D_1Q \perp$ 平面 $A_1PD$，故 B 项错误；

C 项，$\triangle A_1PD$ 不变，要使 $V_{Q-APD}$ 最大，只需点 $Q$ 到平面 $A_1PD$ 的距离最大，下面先用向量法求该距离，再分析最值，由 B 项的分析过程可知 $\overrightarrow{DQ} = (a, 1, b)$，$m = (3, -2, -3)$ 是平面 $A_1PD$ 的一个法向量，

所以点 $Q$ 到平面 $A_1PD$ 的距离 $d = \frac{|\overrightarrow{DQ} \cdot m|}{|\boldsymbol{m}|} = \frac{|a \times 3 + 1 \times (-2) + b \times (-3)|}{\sqrt{3^2 + (-2)^2 + (-3)^2}} = \frac{|3(a - b) - 2|}{\sqrt{22}}$，

因为 $a, b \in [0,1]$，所以 $-1 \leq a - b \leq 1$，从而 $-5 \leq 3(a - b) - 2 \leq 1$，故 $d_{\max} = \frac{|-5|}{\sqrt{22}} = \frac{5}{\sqrt{22}}$，

再算 $S_{\triangle APD}$，已有 $\overrightarrow{DA_1}$ 和 $\overrightarrow{DP}$ 的坐标，故可通过求模得到两边长，用夹角余弦公式求得夹角，进而算 $S_{\triangle APD}$，

$DA_1 = |\overrightarrow{DA_1}| = \sqrt{1^2 + 1^2} = \sqrt{2}$，$DP = |\overrightarrow{DP}| = \sqrt{1^2 + 1^2 + \left(\frac{1}{3}\right)^2} = \frac{\sqrt{19}}{3}$，$\cos \angle A_1DP = \cos \langle \overrightarrow{DA_1}, \overrightarrow{DP} \rangle = \frac{\overrightarrow{DA_1} \cdot \overrightarrow{DP}}{|\overrightarrow{DA_1}| \cdot |\overrightarrow{DP}|}$

$= \frac{1 \times 1 + 0 \times 1 + 1 \times \frac{1}{3}}{\sqrt{2} \times \frac{\sqrt{19}}{3}} = \frac{2\sqrt{2}}{\sqrt{19}}$，所以 $\sin \angle A_1DP = \sqrt{1 - \cos^2 \angle A_1DP} = \frac{\sqrt{11}}{\sqrt{19}}$，故 $S_{\triangle A_1PD} = \frac{1}{2} DA_1 \cdot DP \cdot \sin \angle A_1DP$

$= \frac{1}{2} \times \sqrt{2} \times \frac{\sqrt{19}}{3} \times \frac{\sqrt{11}}{\sqrt{19}} = \frac{\sqrt{22}}{6}$，所以 $(V_{Q-APD})_{\max} = \frac{1}{3} S_{\triangle A_1PD} \cdot d_{\max} = \frac{1}{3} \times \frac{\sqrt{22}}{6} \times \frac{5}{\sqrt{22}} = \frac{5}{18}$，故 C 项正确；

D 项，已有 $\overrightarrow{DQ}$ 和平面 $A_1PD$ 法向量的坐标，可直接计算 $\sin \theta$，由前面的分析过程可知，$\sin \theta = |\cos < m, \overrightarrow{DQ} >|$

$= \frac{|\boldsymbol{m} \cdot \overrightarrow{D_1Q}|}{|\boldsymbol{m}| \cdot |\overrightarrow{D_1Q}|} = \frac{|3 \times a + (-2) \times 1 + (-3) \times (b - 1)|}{\sqrt{22} \times \sqrt{a^2 + 1^2 + (b - 1)^2}} = \frac{|3(a - b) + 1|}{\sqrt{22} \times \sqrt{a^2 + (b - 1)^2} + 1}$ ①，

上式中有 $a, b$ 两个变量，求最值前应先消元，还有 $D_1Q = \frac{\sqrt{6}}{2}$ 没有翻译，故先翻译它，再看如何消元，

因为 $D_1Q = \sqrt{a^2 + 1^2 + (b - 1)^2} = \frac{\sqrt{6}}{2}$，所以式①即为 $\sin \theta = \frac{|3(a - b) + 1|}{\sqrt{22} \times \frac{\sqrt{6}}{2}} = \frac{|3(a - b) + 1|}{\sqrt{33}}$，且 $a^2 + (b - 1)^2 = \frac{1}{2}$ ②，

故核心是由式②求 $|3(a - b) + 1|_{\max}$，不易由式②反解出 $a$ 或 $b$，再代入 $|3(a - b) + 1|$ 消元，怎么办呢？由式②的平方和为常数结构可联想到 $\cos^2 \alpha + \sin^2 \alpha = 1$，由此进行三角换元，可将变量统一成 $\alpha$，但式②的右边不是常数 $1$，怎么办呢？可先将其变形成 $(\sqrt{2}a)^2 + (\sqrt{2}b - \sqrt{2})^2 = 1$，再把 $\sqrt{2}a$ 和 $\sqrt{2}b - \sqrt{2}$ 分别换成 $\cos \alpha$ 和 $\sin \alpha$ 即可，

设 $\begin{cases} a = \frac{\sqrt{2}}{2} \cos \alpha \\ b = 1 + \frac{\sqrt{2}}{2} \sin \alpha \end{cases}$，则 $3(a - b) + 1 = 3\left(\frac{\sqrt{2}}{2} \cos \alpha - 1 - \frac{\sqrt{2}}{2} \sin \alpha\right) + 1 = 3\left[\cos\left(\alpha + \frac{\pi}{4}\right) - 1\right] + 1 = 3\cos\left(\alpha + \frac{\pi}{4}\right) - 2$，

求上式的最值需要先分析 $\alpha$ 的范围，怎样分析？可结合 $0 \leq a \leq 1$ 和 $0 \leq b \leq 1$ 来看，

由 $\begin{cases} 0 \leq a \leq 1 \\ 0 \leq b \leq 1 \end{cases}$ 可得 $\begin{cases} 0 \leq \frac{\sqrt{2}}{2} \cos \alpha \leq 1 \\ 0 \leq 1 + \frac{\sqrt{2}}{2} \sin \alpha \leq 1 \end{cases}$，所以 $\begin{cases} 0 \leq \cos \alpha \leq \sqrt{2} \\ -\sqrt{2} \leq \sin \alpha \leq 0 \end{cases}$，即 $\begin{cases} \cos \alpha \geq 0 \\ \sin \alpha \leq 0 \end{cases}$，故不妨取 $\alpha \in \left[-\frac{\pi}{2}, 0\right]$，

此时 $\alpha + \frac{\pi}{2} \in \left[-\frac{\pi}{4}, \frac{\pi}{7}\right]$，所以 $\cos\left(\alpha + \frac{\pi}{4}\right) \in \left[\frac{\sqrt{2}}{2}, 1\right]$，故 $3(a - b) + 1 = 3\cos\left(\alpha + \frac{\pi}{4}\right) - 2 \in \left[\frac{3\sqrt{2}}{2} - 2, 1\right]$，

求上式的最值需要先分析$\alpha$的范围，怎样分析？可结合$0\leq a\leq1$和$0\leq b\leq1$来看，

由$\begin{cases}0\leq a\leq1\\0\leq b\leq1\end{cases}$可得$\begin{cases}0\leq\frac{\sqrt{2}}{2}\cos\alpha\leq1\\0\leq1+\frac{\sqrt{2}}{2}\sin\alpha\leq1\end{cases}$，所以$\begin{cases}0\leq\cos\alpha\leq\sqrt{2}\\-\sqrt{2}\leq\sin\alpha\leq0\end{cases}$，即$\begin{cases}\cos\alpha\geq0\\\sin\alpha\leq0\end{cases}$，故不妨取$\alpha\in\left[-\frac{\pi}{2},0\right]$，

此时$\alpha+\frac{\pi}{4}\in\left[-\frac{\pi}{4},\frac{\pi}{4}\right]$，所以$\cos\left(\alpha+\frac{\pi}{4}\right)\in\left[\frac{\sqrt{2}}{2},1\right]$，故$3(a-b)+1=3\cos\left(\alpha+\frac{\pi}{4}\right)-2\in\left[\frac{3\sqrt{2}}{2}-2,1\right]$，

所以$|3(a-b)+1|_{\max}=1$，结合$\sin\theta=\frac{|3(a-b)+1|}{\sqrt{33}}$可得$(\sin\theta)_{\max}=\frac{1}{\sqrt{33}}=\frac{\sqrt{33}}{33}$，故D项正确。