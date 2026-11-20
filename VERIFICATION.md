# tt_um_arcadia1_vco_adc 验证记录（2026-11-20，二阶版，版图 S8）

电路：伪差分二阶闭环 VCO ΔΣ ADC，sky130A，TT SKY26e 1x2 模拟 tile，2 个模拟引脚加 rst_n。每半路由输入电阻（49 kΩ）、5T OTA 加两块 MIM 电容（共约 2.4 pF）组成的积分器、7 级饿电流环振（V-to-I 电阻 234 kΩ，两路共质心阵列）、两级寄存器加 7 个 XOR，以及 7 元 NRZ 电阻 DAC（每元 1.04 MΩ）构成。共用部分是 Vref = VDD/2 分压加 MOS 去耦、OTA 尾电流偏置和 rst_n 反相器。输出引脚与第一版相同，片外解码为 y = yN − yP（积分器反相）。第一版开环一阶设计见 tag `v1.0-pseudodiff`。

签核在 eda-frankfurt 上完成，PDK 为 ciel 装的 sky130 0536d02d。版图由 layout/gen_layout.py 和 layout/devlib.py 生成，`layout/flow.sh` 出 GDS/LEF 并跑 magic DRC 与 netgen LVS，抽取用 magic 8.3.568（与 TT precheck 同版本）。后仿网表来自去掉 decap 区的副本（行电源轨照画），只抽电容。仿真用 sim/so_tran.py：VCO、OTA、DAC、偏置为晶体管级，触发器、XOR、反相器用 XSPICE 数字模型（后仿时保留这些单元外部的走线寄生），每条 4096 拍，fs 10 MHz，相干单音，Hann 窗。

| 项目 | 结果 |
|---|---|
| TT precheck 16 项 | 全部通过 |
| magic DRC（precheck 用的 GDS 版） | 0 |
| LVS（netgen） | match uniquely |
| 前仿差分 SNDR / 50 kHz，单边 0.15 V，12.2 kHz | tt 74.4，ss/85 °C 73.9，ff/−20 °C 74.4，sf 74.0，fs 74.8 dB |
| 后仿差分 SNDR / 50 kHz，同上 | tt 72.8，ss/85 °C 71.5，ff/−20 °C 70.4，sf 66.9，fs 71.1 dB |
| 后仿差分 SNR / 50 kHz（扣除谐波） | 80.0 到 86.3 dB |
| 后仿差分 HD2 / HD3 | −84 到 −89 dBc / −67 到 −73.5 dBc |
| 后仿差分 SNDR / 20 kHz | 80.6 到 89.3 dB |
| 前仿小信号单边 0.05 V（tt） | SNDR 69.8 dB / 50 kHz |
| 后仿大信号单边 0.25 V | tt 58.1 dB，ff/−20 °C 34.0 dB（码值碰到 0 和 7，环路过载） |
| 环振中心频率 | 各角均锁在约 fs/4（2.47 到 2.49 MHz），远低于 fs/2 |
| 电流（含测试平台 16 个 1 pF 输出负载） | 48 到 53 µA |

结论与限制：50 kHz 带宽内后仿 SNDR 为 67 到 73 dB，比第一版高约 15 到 20 dB；主要限制是 HD3，SNR 本身在 80 dB 以上。sf 角 HD3 最差（−67 dBc）。可用输入幅度为单边 0.2 V 以内，0.25 V 时环路过载、码值碰顶。ff/sf 角早先的 HD3 问题来自 V-to-I 管在 vctrl 高端退出饱和，把电阻从 351 kΩ 缩到 234 kΩ 后解决；缩到 175 kΩ 时 ss/85 °C 失锁，所以没有再缩。xhigh 电阻的工艺角没有单独扫：输入电阻与 DAC 电阻同类型，比值决定满量程，绝对值只平移环路增益。没有做失配蒙特卡洛。数字单元在仿真里用行为模型，其晶体管级时序只在 LVS 和第一版后仿中验证过。测试脚本没有在硬件上跑过。
