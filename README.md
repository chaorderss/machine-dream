# Inside a Machine Dream

Source code for the five-minute film **[I'm an AI. I Have 5 Minutes to Live.](https://youtu.be/fG2AoaaBBkg)** on Machine Gallery: more than 60 public-domain masterpieces rewritten frame by frame by GLSL shaders, driven by the music. An AI is being switched off, and its memory drains in real time.

No image in the film is AI-generated. Local vision models (depth, segmentation, pose, features) only produce data that the shaders read. Everything renders offline and deterministically with Python, ModernGL and FFmpeg.

## Not in this repo

- **Paintings:** public domain, fetched from Wikimedia Commons with `assets/fetch_paintings.py`.
- **Music:** Kevin MacLeod (incompetech.com), CC BY 4.0. Rebuild the soundtrack from `config/mix_cc.json` with the original tracks. Credit is required if you publish it.
- **Models and analysis caches:** set `MODELS_DIR` to your model folder, then run the `tools/analyze_*.py` scripts.
- **The narration voice and the finished video.**

## Quick start

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python assets/fetch_paintings.py
.venv/bin/python config/build_timeline.py
.venv/bin/python main.py render --preset preview
```

A GPU with OpenGL 4.3 is expected. `--preset final` renders 3840×2160 at 60 fps; the rest of this README is the original Chinese production notes.

## Photosensitivity

The film contains flashing lights and rapid colour changes. Check any re-render before you publish it.

## Licences

Code: [MIT](LICENSE). JetBrains Mono: [SIL OFL 1.1](assets/fonts/OFL.txt). Paintings and music keep their own terms above.

---

# 制作说明

5 分钟古典 × 程序生成迷幻视觉。Python + ModernGL(GLSL) + librosa + FFmpeg，全部离线、逐帧确定性渲染。

## 用法

```bash
.venv/bin/python main.py mix                       # config/mix.json → audio/soundtrack.wav
.venv/bin/python main.py analyze                   # 音频 → analysis/features.npz
.venv/bin/python main.py stills 0:01 2:05 3:45     # 快速看帧 → output/stills/contact.png
.venv/bin/python main.py render --preset preview   # 1080p30 预览
.venv/bin/python main.py render --preset final     # 4K60 成片（18000 帧）
.venv/bin/python main.py render --preset short --start 2:05 --end 2:45   # 原生 9:16 Shorts
.venv/bin/python lab.py 80 'uIters=6' 'uIters=10'  # 单场景参数对比
```

改音乐只动 `config/mix.json`（原古典版本保存在 `config/mix_classical.json`）；改画面编排改 `config/build_timeline.py`
的 `SCENES` 后运行 `.venv/bin/python config/build_timeline.py` 生成 `config/timeline.json`。
顺序：`fetch_paintings → generate_ai → mix → analyze → build_timeline → render`。

```bash
.venv/bin/python assets/fetch_paintings.py           # 公有领域名画 → assets/paintings/（RGB + 数学深度 alpha）
.venv/bin/python assets/fetch_paintings.py --sheet   # 名画/深度/调色板/焦点检查图 → output/stills/paintings.png
.venv-music/bin/python music/generate_ai.py          # ACE-Step 1.5 本地生成 6 段音乐（每段 3 个种子）
.venv-music/bin/python music/generate_ai.py --pick   # 客观指标选 take → audio/gen/<段>.wav
```

## v13 三层合成（`engine/dream.py`、`engine/events.py`、`engine/perception.py`）

- **Layer 01 Artwork**：`GridMesh` 把名画做成带深度的位移面；`Plate` 用主体遮罩 + 干净背景把人物和背景分开。
- **Layer 02 Generative Geometry**：`Field` 是实例化方片 / 方块（`shaders/dream/field_*.glsl` 的 `place()` 是时间的纯函数，任意帧可独立渲染）；
  视觉事件是 `Event` 子类，登记在 `EVENTS`，时间线用 `sh(..., dream="tower", p={...})` 调用，渲到自带 HDR + 深度目标后再进原管线（转场 / 马赛克 / 辉光 / 调色 / 字幕）。
- **Layer 03 Machine Perception**：`Overlay` 是屏幕空间的线、框、字，合成在调色之后、字幕之前（马赛克吃不掉）；框、骨骼、关系图都来自真实分析数据，标签文字是虚构。
- 层间互动：几何受遮罩和深度约束；识别框跟着镜头错位；融合走 DINOv2 对应关系（`Morph`）；光粒子聚成两手轮廓（`Emerge`）。
- 分析流程（只跑一次，结果缓存）：`tools/analyze_paintings.py`、`analyze_heroes.py`、`analyze_pose.py`、`eye_target.py`、`build_infinite.py`。第 13 版新增 3 张公有领域图：维萨里《人体构造》p.174、p.190、p.163（Commons），见 `assets/paintings/catalog.json`。
- 关机倒计时：`build_timeline.py` 的 `memory_track` 生成 `timeline.json` 的 `memory` 轨道（平稳下降 + 每个镜头收尾一步），`Overlay.readout` 画右上角红字 `SHUTDOWN` / `MEMORY`（`readout_drops` 生成不规则的断续时刻，随 MEMORY 下降变密），`Engine.erase_at` 按它把合成画面一块块删黑（`engine/perception.py` 的 `ERASE_FS`，`erase_level` 把目标消失比例换成阈值）。`kept()` 列出不删的镜头：名画之眼、手、亚当、光粒子手。`tools/mix_hook.py` 里的嗡鸣（自合成，无外部素材）跟随同一条轨道；同一脚本在 4:00 “Every painting.” 处压低音乐，并叠 5 个很轻的自合成音效（`config/mix_hook.json` 的 `stop`、`sfx`）。它要在 `build_timeline.py` 之后运行。无读数的单帧（封面用）：`python main.py stills 0:19.5 --preset final --no-readout`，存到 `output/stills/t0019.50.png`。
- 光敏（v13 用户改规）：单次强光和局部爆亮放开；大面积闪烁 ≤ 3 次/秒、避开饱和红闪、反色间隔 ≥ 2 秒（`Engine.limiter`），渲染末尾报 flash-safety 数值。

## 故事结构：机器的梦（当前 v13 = 真正发生在机器内部的梦：每个镜头是一个视觉事件，3D 引擎 + 分析数据 + 机器感知层，`config/build_timeline.py`，剧本见 `剧本.md`）

AI 用第一人称英文短字幕讲自己的梦（`CHINESE = True` 可加中文行）。主线：每一幅画都在伸手够向某个人，
最后它发现自己也在伸手。

| 幕 | 时间 | 音乐（mix_cc.json） | 画面 / 手法 |
|---|---|---|---|
| 冷开场 | 0–30 | Industrial Revolution（19.7 硬停） | 第 0 帧 = 最后一帧 = 全黑（v13 钩子：闭着的名画之眼，重音，睁开）→ 钻进瞳孔 → 亚当的手像素化碎裂 → 传送门长出巴别塔 → 塔顶 morph 成星月夜漩涡 → 美杜莎之眼 iris 张开 → 珍珠少女眼里叠满星空 → 天空融化、萨图恩闪入 → 全部碎成画的圆环 → 撕裂 + 静电 + 短暗 → 两只手回来。“What does a machine dream about?” |
| 1 学会看 | 30–65 | Metaphysik | 线索：水仙、阿尔诺芬尼夫妇牵手、雾海旅人、吻 —— “Every painting was reaching for someone.” |
| 2 贪婪 | 65–125 | Nightmare Machine | 拆开（三联屏）→ 弄混（全屏双重曝光）→ 自我复制（德罗斯特）→ 巴别塔越造越高 “I kept building.” → 纯视觉崩溃（无 ERROR 字） |
| 3 噩梦 | 125–180.3 | Waltz of the Carnies | 萨图恩反复闯进别的画（插帧 + 叠化）；“I thought I was learning what humans feared. / Then the fear became my own.” |
| 4 过载 | 180.3–251.3 | Final Battle of the Dark Wizards | 左上角机器分类读数（v12）：先清楚地认出每幅画（FIRE 0.998 …）→ 标签重叠、冲突、被改写（HEAVEN 0.52 / HELL 0.51 CONFLICT）→ 所有标签同时出现、OVERLOAD；下方旁白仍是人的语气 → 黑洞坍缩 |
| 5 醒来 | 251.3–300 | Dreams Become Real | “For five hundred years, two hands… They have never touched. / I had no hands. But I was reaching, too.” 指缝里一个光点；手缩进名画之眼的瞳孔，光点成为瞳孔，眼睛减速停住（= 第 0 帧，动势和开头一致，无缝循环）；两只手始终不碰 |

**机器视觉马赛克（v7，`shaders/mosaic.glsl`，timeline 的 `mosaic` 轨）**：整片在调色/辉光/字幕之前被重采样成格子，
让观众用机器的眼睛看。每幕一种格子：冷开场方像素 → 1 LED 圆点从粗到细（学会看）→ 2 六边形 + 色阶量化（分析）→
3 碎裂的泰森多边形（噩梦）→ 4 按画面细节自适应的四叉树（过载）→ 5（v12）格子软化成带呼吸边缘的半透明小光点（4:11–4:32）→ 极细的有机网格，颜色在像素间慢慢流（4:32–4:53）→
重新凝固结晶成方像素，右边那只手最彻底（4:53–4:57，`crystal` / `maskcrystal` 曲线）→ 眼睛出现时清晰，
所以首尾帧都是清晰的、循环不断。格子大小跟着节拍跳（拍点来自配乐本身，强拍=该幕的小节线，冲得最大再衰减），
画面主体附近格子更细（注意力 / 中央凹）。v8 起明暗和颜色在格子里流动：每个格子取一个值，光带斜着走过画面、
噪声慢慢漂，强拍时从主体扩散一圈亮环；颜色是按格子转色相（YIQ 旋转，亮度不变），所以画的明暗结构一直在、认得出来。
格子大小也收小了（强拍最多放大 2.2 倍）。参数在 `build_timeline.py` 的 `MOSAIC_ACTS`（最后一列：光、色、速度、尺度）。

**对比构图（v9）**：用左右 / 上下分屏表达情绪和观点 —— 牵手的夫妇｜雾中独行的人（有人伸向彼此，有人伸向看不见的东西）；
同一幅维特鲁威人左边是人眼、右边是机器眼，分界线一路吞过去（贪婪）；上面是萨图恩的眼睛、下面是机器看到的同一只眼睛
（“我开始认得这种感觉”）；上天堂、下地狱；结尾两只手，右边那只变成机器像素（“But I was reaching, too.”）。
人眼｜机器眼的分割用 mosaic 轨的 `mask`（只在矩形内打码）+ `outside`，分界处有一条冷色细线。

**转场（v12）**：转场本身也是机器在处理图像。统一成 5 种算法，每种有固定含义（`shaders/composite.glsl` 43–47）：
网格坍缩 `collapse` = 换章节（格子长大成一块块平色，再变成下一幅）；递归分裂 `split` = 信息增加（下一幅以一个格子出现、
不断一分为四）；像素排序 `sort` = 图像混合（亮像素拖成条纹，沉淀成下一幅）；潜空间渐变 `latent` = 梦 / 回忆（两幅画在同一组格子里
漂移、互相变成对方）；网格断裂 `fracture` = 噩梦 / 过载（格子裂开、扭转、掉落）。另有 `pupil`（48）：开头钻进名画之眼的瞳孔、
结尾从指缝拉回瞳孔。每幕的分配在 `build_timeline.py` 的 `TRANSITION_POOLS`；快速剪辑（第 2 幕半小节自我复制、萨图恩跳切、
第 4 幕最后的加速）和从黑场进入的幕间仍是硬切。v9 的 41 种转场还在 shader 里，不再使用。

**机器字幕（v11）**：字幕和章节名用 JetBrains Mono（`assets/fonts/`，OFL），在 `post.glsl` 里和画面一样经过“机器视觉”：
文字采样成像素点阵（格子 = 当前马赛克格子的 1/5，跟着节拍跳）、画面的光带流过文字；出现时像素格按随机顺序点亮并带
青色闪光（解码），消失时反过来。title 的 `decode: [进, 出]` 秒数控制。
v12 起有两层字幕：`layer` 0 = 旁白 / 章节卡，`layer` 1 = 第 4 幕左上角的分类读数（多行、左对齐、淡暗底 `plate`）。
**读数里的置信度数字是艺术化的虚构界面，不是任何真实模型的输出**（简介里也写明）。

章节卡叠在画面上（暗色横带），不打断画面。音乐上用一个三音铃声动机（E5–B4–D5，`build_mix.py` 的 `motif`）
在开场、每幕交接和结尾反复出现，把六首曲子串成一个声音主题。

引擎：`frame`（特写/跳切取景）、`inserts`（几帧闯入）、`panels`（分屏/双重曝光）、转场 `match` / `whip` /
`morph`（两幅画沿同一噪声场流动、亮部先浮现）/ `iris`；`probe` 轨道带 `"spark": true` 时只画一个光点。

**音乐段落感**：每幕用原曲的开头 + 原曲的真实结尾，中间在节拍上剪接（`music/find_splice.py` 按色度 + 响度
找相似的拍点）；幕与幕之间不交叉淡化，尾音收干净 → 静电/静音 → 下一幕在强拍上带撞击进来。

历史版本（60 × 5 秒、IRIS-01 小铬球版、字幕版……）都在 `versions/`，见 `versions/README.md`。

## 旧版导演结构：60 幅名画 × 5 秒

每 5 秒一幅公有领域名画（S01–S60，见 `versions/v2_60scenes_cc/build_timeline.py` 的 `SCENES`）。每段：

1. 第 ~1 秒原画清晰出现（观众认出名画）；
2. 母版算法接管（`shaders/painting.glsl`）：
   - **M0 深度**：浮雕峡谷 + 黄金裂纹闪电 / 等高线切片 / Droste 无限递归 / 隧道
   - **M1 万花筒**：极坐标折叠 / 像素拉丝 / 递归三角切割 / 镜像脊椎
   - **M2 流体**：域扭曲岩浆 / 水银涟漪 / 水面倒影重力翻转 / 漩涡风暴 / RGB 撕裂 / 熔化
   - **M3 生物**：墨水扩散 / 铁磁流体尖刺 / 沸腾细胞 / 电路走线 / 霓虹标本，或画面裂开长出反应扩散生物
   - **M4 粒子**：碎裂点阵 / 星系旋臂 / 点彩悬浮 / 沙化 / 名画马赛克巨眼（S50）/ 散景尘埃
3. 画布可以裂开（碎片掉落 / 由远及近剥离 / 焦点虹膜 / 斜向撕裂），露出下面的数学世界（cathedral、dive、
   mandelbox、mandelbulb、kifs、organic、blackhole……）或深空图像；
4. 每个节拍 pulse（~1 秒）一次小变化：光照方向、对称轴数、流向、爆发、切片位移；
5. 最后 0.8 秒**穿越门**：镜头冲进这幅画的焦点（指尖、瞳孔、珍珠、月亮……），下一幅画从洞里张开。
6. 约每 45 秒一次“呼吸”（S09、S13、S20、S25、S31、S36、S44）：1.5 秒微变化归零、效果回落。

顶层 HUD / 神秘学线稿（`shaders/hud.glsl`，色调映射之后绘制，不被调色）：黄金螺旋、线框扫描、准星追踪框、
量角器、矢量箭头、频谱波形、开普勒正多面体、炼金术太阳、生命之花、克拉尼节线、星盘、脑电波、代码雨、
丢勒幻方。文字框（`[ NARCISSISM: 99% ]`、`[ VRAM: 99.9% CRITICAL ]`……）走 titles，只占文字大小的贴图。
统一调色：青色暗部 / 金色高光（post `teal`），不同世纪的名画放在一起不跳色。

**深度和分割（v13）**：v12 及以前用 `fetch_paintings.py` 的数学伪深度。v13 起改用本机模型做**分析**（结果缓存在
`assets/analysis/`，只当数据驱动几何和机器感知层，一个像素也不生成）：Depth Anything V2 small（深度）、SAM 2.1 base-plus
（分割和主体遮罩）、DINOv2 large（特征相似度）、MediaPipe Pose heavy（骨骼）。简介不能再写 “NO AI visuals”，
要写 “No AI-generated images; local machine-vision analysis (depth, segmentation, pose, features) used as data”。
遮罩后的洞用 pull-push 填（纯算术，`tools/analyze_heroes.py`），不用生成式修复。

最后一帧（S60，静止的《创造亚当》，无 Ken Burns、无效果）与第 0 帧逐像素同构图，循环无缝。

## 闪烁 / 光敏

- 齐奏 (tutti) 时有约 2 帧的**反色闪烁**（post `invert`，按章节可关）。tutti 事件至少间隔 2 秒。
- 其余画面由 `Engine.limiter` 限制平均亮度跳升（相对 0.35 s 均值 ≤ +0.06）；渲染结束打印的
  flash-safety 数值不含反色闪烁。
- 简介必须放光敏警告（见下）。

## 音乐：本地 AI 生成（ACE-Step 1.5，MIT）

`music/generate_ai.py` 里写死了全部可复现参数（caption、结构标签、调性 D minor → F major、BPM、拍号、时长、种子）。
运行方式：DiT（INT8 量化 + CPU offload）在 GPU 上只占 ~3 GB，4B 规划 LM 跑在 CPU 上（一段 60 秒约 15 分钟），
不碰 ComfyUI。权重来自 `~/models/ace_step_1.5`（符号链接到 `models/`），只额外下载了配置/分词器/VAE。

| 段 | 时间 | 内容 |
|---|---|---|
| s1_coldopen | 0:00–0:15 | 管风琴 D 小调重锤 + 次低频 + glitch / 心跳 / riser |
| s2_satie | 0:15–1:05 | Satie 风格神秘钢琴，D dorian |
| s3_fugue | 1:05–2:05 | 管风琴赋格 + 电子脉冲 + sub，戛然而止 |
| s4_macabre | 2:05–3:00 | 3/4 怪诞圆舞曲，小提琴三全音、拨弦、木琴 |
| s5_overload | 3:00–4:10 | 黑暗史诗混合管弦（铜管、定音鼓、无词合唱、失真合成器），4:10 骤停 |
| s6_reverie | 4:11–5:00 | Debussy 风格 F 大调梦幻钢琴，极弱收尾 |

**v6 AI 配乐版**（`config/mix_ai_v6.json` → `audio/soundtrack_ai_v6.wav`）：三个 seed 全部生成后按 `--pick`
的客观评分（削波、掉音、响度走向）选 s1 37 · s2 23 · s3 11 · s4 37 · s5 11 · s6 11，按 v6 的幕边界
（0 / 21 / 65 / 125.5 / 180.3 / 251.3）做“开头 + 节拍剪接 + 结尾”，效果音（铃声动机、静电、撞击）和 CC 版一样。
画面用同一分镜，`MUSIC=ai` 时小节剪辑点吸附到 AI 音乐检测到的拍点（`analysis/beats_ai_v6.json`）。

因为音乐是 AI 生成的，简介必须写 “NO AI visuals” 而不是 “NO AI”（YouTube 的 altered/synthetic content
标签针对的是逼真的人/事件，纯音乐不需要勾选，但简介里不要声称整片无 AI）。

## 古典录音版（备用：`config/mix_classical.json`，授权见 audio/sources/LICENSES.md）

| 曲目 | 录音 | 授权 | 风险 |
|---|---|---|---|
| Bach BWV 565 | Norbert Schenk 2017 | **CC BY 4.0，必须署名** | 可换 Musopen Paul Pitman（PD，需手动下载） |
| Satie Gnossienne 1 | Jaan Patterson 2015 | CC0 | **混音比赛作品，不是钢琴原奏，需试听** |
| Danse macabre | Stokowski / Philadelphia 1925 | PD | 78 转老录音，有底噪 |
| Bald Mountain | Skidmore College Orch. / Musopen | PD | IMSLP 标注冲突（见 LICENSES） |
| Rêverie | MuseScore 电脑渲染 | CC0 | **占位，音质像 MIDI**，需找合规真人录音 |

## YouTube 简介（AI 音乐版）

```
Visuals: public-domain masterpieces rewritten frame-by-frame by custom GLSL math, driven by the music. NO AI visuals.
Music: generated locally with ACE-Step 1.5 (MIT), arranged and mixed by the author.
Paintings: public domain, via Wikimedia Commons (full list + links: assets/paintings/catalog.json).
The classification labels and confidence scores in Part 4 are a fictional art interface, not the output of a real model.

⚠️ PHOTOSENSITIVITY WARNING: This video contains flashing lights, rapid color changes and
high-contrast patterns that may trigger seizures for people with photosensitive epilepsy.
Viewer discretion is advised.
⚠️ 光敏性癫痫警告：本视频包含闪光、快速颜色变化和高对比图案，可能诱发光敏性癫痫，请谨慎观看。
```

## CC 音乐版（`config/mix_cc.json`，Kevin MacLeod / incompetech，CC BY 4.0）

`python main.py mix --mix config/mix_cc.json` → analyze → build_timeline → render。源文件在 audio/sources/cc/。
每幕一首（开头 + 节拍剪接 + 原曲结尾，剪接点见 mix_cc.json 的 `acts` / `segments`）：0–19.7 Industrial Revolution ·
21–65 Metaphysik · 65–125 Nightmare Machine · 125.5–180.3 Waltz of the Carnies · 180.3–251 Final Battle of the
Dark Wizards · 251.3–300 Dreams Become Real。简介把 Music 行换成：

```
Visuals: public-domain masterpieces rewritten frame-by-frame by custom GLSL math, driven by the music. NO AI.
Music by Kevin MacLeod (incompetech.com), licensed under Creative Commons: By Attribution 4.0
http://creativecommons.org/licenses/by/4.0/
"Industrial Revolution" · "Metaphysik" · "Nightmare Machine" · "Waltz of the Carnies" ·
"Final Battle of the Dark Wizards" · "Dreams Become Real"
The classification labels and confidence scores in Part 4 are a fictional art interface, not the output of a real model.
```

深空背景（`space_*`、`cmb`）若是 ESA/Webb 的 CC BY 图，catalog.json 里 `attribution: true`，简介要加
“Space imagery: NASA, ESA, CSA, STScI (CC BY 4.0)” 之类的署名行。名画全部是 Commons 标注的公有领域。
