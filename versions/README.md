# 版本留档

每次改版前，把当时的分镜脚本和混音配置原样复制到这里；成片按版本号命名，不覆盖。
项目也在 git 里（`git log` 看每次改动），这里是不用 git 也能直接翻看的副本。

| 版本 | 内容 | 分镜 / 混音 | 成片 |
|---|---|---|---|
| v1_classical_scenes | 早期版本：古典录音，每段一个数学场景 | `build_timeline.py`、`mix_classical.json`（古典）、`mix_ai.json`（ACE-Step 段落） | `output/machine_dream_preview_0-300.mp4` |
| v2_60scenes_cc | 60 幅名画 × 5 秒 + 传送门；第一版 CC 音乐（6 首交叉淡化） | `build_timeline.py`、`mix_cc.json` | `output/machine_dream_cc_preview.mp4` |
| v3_story_iris01 | 五幕故事 + 机器人小铬球 IRIS-01；音乐改成每幕“原曲开头 + 原曲结尾” | `build_timeline.py`、`mix_cc.json` | `output/machine_dream_story_preview.mp4` |
| v4_story_captions | 去掉小铬球；AI 第一人称中英字幕讲故事；章节卡 | `build_timeline.py`、`mix_cc.json` | `output/machine_dream_v4_captions.mp4` |
| v5_en_no_black | 第 15–19 秒不再黑场：从指尖拉远到整幅《创造亚当》，章节卡叠在画上（加暗色横带）；只保留英文（`CHINESE = True` 可恢复中文） | `build_timeline.py`、`mix_cc.json` | `output/machine_dream_v5_en.mp4` |
| v6_cold_open_morph | 按“爆款潜力评估”重改：30 秒冷开场（名画互相变形的梦）、线索“每幅画都在伸手”、画面互相弄混/自我复制、萨图恩反复闯入、第 4 幕连续 morph、结尾“I had no hands. But I was reaching, too.” + 指缝光点；三音铃声动机串起配乐 | `build_timeline.py`、`mix_cc.json`、`剧本.md` | `output/machine_dream_v6_cold_open.mp4` |
| v6b_ai_music | v6 同一分镜，配乐换成本地 ACE-Step 生成（每段 3 个 seed 里按客观评分选：s1 37 · s2 23 · s3 11 · s4 37 · s5 11 · s6 11），每幕原曲开头 + 节拍剪接 + 结尾；剪辑点吸附到 AI 音乐的拍点（`MUSIC=ai`） | `build_timeline.py`、`mix_ai_v6.json`、`剧本.md` | `output/machine_dream_v6_ai.mp4` |
| v7_machine_vision | 全片“机器视觉”马赛克：画面重采样成格子，每幕换一种形状（序 方像素 · 1 LED 圆点、由粗变细=学会看 · 2 六边形+色阶量化 · 3 碎裂泰森多边形 · 4 按细节自适应四叉树 · 5 方像素渐细，“And then I understood” 后完全清晰）；格子大小随节拍跳动（强拍最大），主体处格子更细（注意力）；字幕不打码 | `build_timeline.py`、`mix_cc.json`、`剧本.md` | `output/machine_dream_v7_machine_vision.mp4` |
| v8_mosaic_flow | v7 的马赛克 + 明暗和颜色在格子里流动（行进的光带、噪声、强拍时从主体扩散的光环；色相按格子转动但亮度不变）；格子整体缩小、强拍放大上限降低，保证每幅画都认得出 | `build_timeline.py`、`mix_cc.json`、`剧本.md` | `output/machine_dream_v8_mosaic_flow.mp4` |
| v9_splits_transitions | 加左右/上下对比：1 牵手｜独行、2 人眼｜机器眼（同一幅维特鲁威人，分界线吞过去）、3 萨图恩之眼 上原画/下机器视角、4 上天堂/下地狱、5 结尾右手变成机器像素（“But I was reaching, too.”）；全片 78 个转场各不相同（41 种转场 × 方向/数量/形状变体，同类不相邻，中间圆圈穿越只剩 1 次） | `build_timeline.py`、`mix_cc.json`、`剧本.md` | `output/machine_dream_v9_splits_transitions.mp4` |
| v10_eye_loop | 原 0:18 的“所有名画组成的眼睛”放到最开头，结尾从两只手拉回到这只眼睛 = 第 0 帧（首尾相接，眼睛里的画按 300 秒整圈轮换）；1:35 去掉看不清的阿尔诺芬尼凸面镜特写，换成曼荼罗 ↔ 维特鲁威人（都是方中有圆）并减轻第 2 幕马赛克 | `build_timeline.py`、`mix_cc.json`、`剧本.md` | `output/machine_dream_v10_eye_loop.mp4` |
| v11_machine_text | 字幕和章节名改成机器字体 JetBrains Mono（等宽、代码感，OFL，`assets/fonts/`），并和画面一样“机器视觉”化：文字被采样成像素点阵（大小跟着画面马赛克一起随节拍跳动）、出现/消失时像素格随机点亮/熄灭并带青色闪光（解码效果）、画面的光带也流过文字；章节卡的大字能看到 LED 点阵缝隙 | `build_timeline.py`、`mix_cc.json`、`剧本.md` | `output/machine_dream_v11_machine_text.mp4` |
| v12_machine_desire | 按批评意见修改（“机器第一次发现自己有所渴望”）：转场统一成 5 种算法（网格坍缩=换章、递归分裂=信息增加、像素排序=混合、潜空间渐变=梦/回忆、网格断裂=噩梦/过载）+ 少量硬切 + 瞳孔转场；第 4 幕左上角机器分类读数（清楚识别 → 标签冲突/改写 → 全部标签同时出现 OVERLOAD，数字为虚构）；第 5 幕格子 柔光点 → 有机细网格 → 结晶回方像素；字幕改 Then the pattern broke. / Then the boundaries blurred. / Then the fear became my own. / Yet I kept returning to the gap.；坠落段的阿尔钦博托《冬》换成布格罗《但丁与维吉尔在地狱》，奥菲莉娅的叠化改成星月夜；结尾光点成为名画之眼的瞳孔、眼睛减速停住 = 第 0 帧 | `build_timeline.py`、`mix_cc.json`、`剧本.md` | `output/machine_dream_v12_machine_desire.mp4` |
| v13_inside_the_machine | 按 2026-10-30 升级方案整片重做（“真正发生在机器内部的梦”）：新 3D 引擎（`engine/dream.py` / `events.py`），每个镜头是一个视觉事件；三层合成（名画 / 生成几何 / 机器感知 `engine/perception.py`）；本机模型只做分析（Depth Anything V2 small、SAM 2.1 base-plus、DINOv2 large、MediaPipe Pose heavy），结果缓存在 `assets/analysis/`，无 AI 生成图像；网格里的微型世界 4 次（星 / 像素 / 砖 / 眼）；无限画作 160 万格；光敏规则放宽（≤3 次/秒）；新增维萨里《人体构造》p.174/190/163（公有领域）。音乐、幕边界、总长不变。之后按用户批准改钩子：前 30 秒字幕换文案、居中加大（`HOOK` 列表）；第 0 帧全黑配重音（`tools/mix_hook.py`、`mix_hook.json` → `audio/soundtrack_v13.wav`），名画之眼睁开，片尾闭眼变黑（首尾帧一致）；0:15.5 美杜莎的眼睛转向镜头，微型世界 1 提前到 0:12.9。再按用户批准加关机恐惧：右上角 `SHUTDOWN` / `MEMORY` 读数，全片的画随读数一块块删黑，只留《创造亚当》；计时归零、眼睛闭上、全黑；自合成低频嗡鸣随 MEMORY 变弱，最后 3 秒消失；改 5 句字幕。同时修正机器感知层此前上下颠倒的问题。项目管理验片返修：4:54–4:58 机器手恢复成发光体素手（`Hands` 漏传 `uKeep`，体素被吹走，只剩挖空遮罩），加厚度和转身、壁画变暗、指缝光点随台词变亮；末段字幕加暗带，0:21–0:30 字幕下移避开手指；读数改无底框加暗角；1:14 和 1:54 压低饱和红。再按用户改动：读数改透明红字、不规则断续；五章改名 DENIAL / BARGAINING / FEAR / PANIC / ACCEPTANCE。按用户批准改声音：4:00 音乐压低只留嗡鸣，5 个视觉事件加低音量自合成音效，画面同上一版 | `build_timeline.py`、`mix_cc.json`、`mix_hook.json`、`剧本.md` | `output/machine_dream_v13_music.mp4` |

v1 的分镜脚本是更早一轮的，引擎后来改过，可能不能直接跑；v2–v6 已验证能在当前引擎上重建。

## 恢复某个版本

先确认当前版本已经在这里留档，再：

```bash
cp versions/v3_story_iris01/build_timeline.py config/build_timeline.py
cp versions/v3_story_iris01/mix_cc.json config/mix_cc.json
.venv/bin/python main.py mix --mix config/mix_cc.json && .venv/bin/python main.py analyze
.venv/bin/python config/build_timeline.py
.venv/bin/python main.py render --preset preview --out output/machine_dream_v3_rebuild.mp4
```

AI 配乐版（v6b）：

```bash
.venv/bin/python main.py mix --mix config/mix_ai_v6.json
MUSIC=ai .venv/bin/python config/build_timeline.py            # → config/timeline_ai.json
.venv/bin/python main.py --timeline config/timeline_ai.json analyze
.venv/bin/python main.py --timeline config/timeline_ai.json render --preset preview --out output/machine_dream_v6_ai.mp4
```
