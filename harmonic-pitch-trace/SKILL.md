---
name: harmonic-pitch-trace
description: 从单声道 16 位 PCM WAV 稳态乐音估算基频，以 JSON 给出逐帧音高、跨帧稳定性与拒判理由。当用户询问音色中的基频、缺失基音或倍频误判时使用。
license: MIT
compatibility: Python 3.10+，仅标准库，单 CPU 即可离线运行。
metadata:
  author: "pending-owner"
  version: "1.1.0"
---

# 听见消失的基音

当最响的分音高出一个八度，录音里仍能找回演奏音高吗？

## 使用 1.1 版声学重复频率与声源音高分开判定

分析 WAV 的声学重复频率时使用原命令。若问题指向乐器真实演奏音或缺失基音的潜在来源，追加 --source-identity，并保留所有候选和拒判原因。不要用跨窗稳定给潜在来源作唯一归因。

在 5 个加 Hann 窗的片段内比较候选频率的半整数分音与整数分音振幅，结合相邻频带的本底估计决定是否拒判。中位比值超过 max(0.005, 4×本底比值) 时返回 octave_ambiguous。严格模式对支持范围内无法从波形区分的整数次缺基音解释返回 source_not_identifiable。

```console
python harmonic-pitch-trace/scripts/analyze.py harmonic-pitch-trace/assets/case3.wav --source-identity --out source.json
```

360 Hz 正弦与 180 Hz 源只留下第二谐波能生成逐字节相同的 PCM。严格模式对该文件拒判并列出候选。潜在声源判断依赖 130–500 Hz 的频带先验和整数谐波假设；未做真实乐器外部验证。

## 接收试听卡

输入单声道 16 位有符号小端 PCM WAV，采样率 4–48 kHz、时长 0.12–15 s，目标基频 130–500 Hz。可直接播放 assets 中 0.5 秒、8 kHz 的音频，或用随包的 scripts/synthesize.py 重新合成。

## 执行

1. 优先读取 status、accepted_frames 与各窗轨迹；若 steady，给出 Hz 和相邻八度候选风险。
2. 在可写工作目录中运行 `python <Skill目录>/scripts/analyze.py <输入文件> --out <输出JSON>`。脚本路径按本 Skill 实际安装位置替换。随包示范可从包含本 Skill 文件夹的目录运行以下命令。

```console
python harmonic-pitch-trace/scripts/analyze.py harmonic-pitch-trace/assets/case1.wav --out result.json
```

3. 打开新生成的 JSON 并报告状态与依据。JSON 给出 12 个窗起点 starts_s、各窗估计 frame_hz、通过数和状态。steady 时给出 fundamental_hz 与 spread_cents，静音或有效窗不足返回 insufficient，跨度过大返回 unstable。
4. 用另一份试听卡替换输入即可复用；若用户只给自然语言，先向用户核实无法由原文确定的测量参数或数据。

## 示例结果与验证边界

196 Hz 纯音的误差为 0.46 音分，过零率为 0.08。

面向 130–500 Hz 的稳态单音。和弦、滑音、整段只有偶次谐波或严重混响时，结果可能拒判或出现八度错误。

若导入端缺少样例音频，在可写工作目录执行 `python harmonic-pitch-trace/scripts/synthesize.py case3 --out demo.wav`，再将 `demo.wav` 送入分析脚本。可选 case1、case2、case3 或 boundary。

实现与单位约定见 [方法](references/method.md)。脚本仅读取一个本地输入文件，输出到指定路径，不访问网络。
