# tt_um_arcadia1_vco_adc 验证记录（2026-11-20，版图 G3）

电路：伪差分环振 VCO ΔΣ ADC，sky130A，TT SKY26e 1x2 模拟 tile，2 个模拟引脚。VINP（ua[0]）和 VINN（ua[1]）各驱动一个 M1 加 351 kΩ xhigh 电阻的 V-to-I，镜像到 7 级饿电流环振；两路电阻做成中轴上的一个共质心阵列（D N P P N D）。每路 7 个 dfxtp_4 在 clk 上升沿采样相位：P 路在 uo_out[6:0]，监视脚 uo_out[7]；N 路在 uio_out[7:1]，监视脚 uio_out[0]，uio_oe 全部拉高。片外每路对相邻相位字异或数 1，ADC 输出为 P 减 N。版图左右镜像对称，触发器四行贴在各自 8 个输出引脚正下方，每个输出短接一段 met3 后直上引脚；输入对走平行 met3，两侧 VGND 屏蔽。

签核在 eda-frankfurt 上完成，PDK 为 ciel 装的 sky130 0536d02d（与 tt-gds-action ttsky26e 锁定版本一致）。版图由 layout/gen_layout.py 生成，触发器块的布置由 layout/plan_ff.py 搜索得到（无 met2/met3 间距冲突）。`layout/flow.sh` 出 GDS/LEF 并跑 magic DRC 与 netgen LVS；官方 precheck 用 tt-support-tools 的 precheck.py。后仿网表来自去掉 decap 区的副本（decap 只给理想电源加负载），主跑只抽电容，另跑一次完整 RC 对照。

| 项目 | 结果 |
|---|---|
| TT precheck 16 项（magic DRC、klayout FEOL/BEOL、offgrid、pin、boundary、power、analog pin 等） | 全部通过 |
| magic DRC（precheck 用的 GDS 版） | 0 |
| LVS（netgen，含 1756 个 decap_12 与电阻阵列） | match uniquely，无属性误差 |
| 后仿差分 SNDR / 50 kHz，fs 10 MHz，单边 0.15 V，12.2 kHz | tt 53.6，ss/85 °C 55.8，ff/−20 °C 55.0，sf 49.8，fs 51.4 dB |
| 后仿差分 SNR / 50 kHz（扣除谐波） | 53.7 到 61.7 dB |
| 后仿差分 HD2 / HD3 | −66 到 −84 dBc / −52 到 −62 dBc |
| 后仿只看 P 路 SNDR / 50 kHz | 35.2 到 41.3 dB（差分提升 14 到 18 dB） |
| tt 完整 RC 与只抽电容对照（1024 点） | 频率 1.914 / 1.911 MHz，SNDR 56.0 / 53.9 dB，差别在短记录波动内 |
| 前仿 tt（新电容尺寸） | SNDR 55.8 dB，SNR 66.4 dB / 50 kHz |
| 数字码换算频率与监视脚直测频率 | 所有工况偏差小于 0.1% |
| 两路频率失配（后仿） | 小于 0.1% |
| VCO 中心频率（VIN 1.0 V，后仿） | 1.63（ff/−20 °C）到 2.21 MHz（ss/85 °C），低于 fs/2 = 5 MHz |

结论与限制：差分 SNDR 在 50 kHz 带宽内为 50 到 56 dB，主要受 HD3 和一阶量化噪声限制，与行为模型一致；sf/fs 角稍低，是 HD3 与 SNR 同时略差所致。仿真里 Idd 约 68 µA（tt），其中大部分是测试平台在 16 个输出上挂的 1 pF 负载被 10 MHz 翻转所耗，核心本身每路约 7 µA 量级，芯片实测时还会算进 TT 的 IO 开关。电阻工艺角（xhigh poly 约 ±20%）没有单独扫，它按比例平移两路调谐曲线，两路同向，差分抵消；最坏情况下若码值碰到 7，就提高 fs 或降低输入共模。没有做失配蒙特卡洛：两路电阻共质心，晶体管失配只引入小的增益差，行为模型显示 5% 增益失配下 HD2 仍在 −62 dBc 以下。测试脚本 test/capture_vco_adc.py 按 DB v3 引脚表写成，没有在硬件上跑过；解码器已用按真实引脚映射合成的数据验证。
