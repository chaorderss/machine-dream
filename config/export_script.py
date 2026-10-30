#!/usr/bin/env python3
"""Export the storyboard in config/build_timeline.py as a readable script (Markdown): time, shot, narration EN + 中文.

  .venv/bin/python config/export_script.py versions/v5_en_no_black/剧本.md
  MUSIC=ai .venv/bin/python config/export_script.py versions/v6b_ai_music/剧本.md
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_timeline as bt  # noqa: E402

PARTS = {"P": "序章 · 钩子", "I": "Part 1 · Denial（否认）", "II": "Part 2 · Bargaining（讨价还价）",
         "III": "Part 3 · Fear（恐惧）", "IV": "Part 4 · Panic（恐慌）", "V": "Part 5 · Acceptance（接受）"}
MUSIC = {"P": "Industrial Revolution", "I": "Metaphysik", "II": "Nightmare Machine", "III": "Waltz of the Carnies",
         "IV": "Final Battle of the Dark Wizards", "V": "Dreams Become Real"}
if bt.MUSIC == "ai":                               # MUSIC=ai: local ACE-Step takes (config/mix_ai_v6.json)
    MUSIC = {"P": "AI · 管风琴冷开场 (seed 37)", "I": "AI · 萨蒂风钢琴 (seed 23)", "II": "AI · 管风琴赋格 (seed 11)",
             "III": "AI · 骷髅华尔兹 (seed 37)", "IV": "AI · 史诗管弦 (seed 11)", "V": "AI · 德彪西风钢琴 (seed 11)"}


NAMES = {
    "adam": "米开朗基罗《创造亚当》", "saturn": "戈雅《农神吞噬其子》", "babel": "勃鲁盖尔《巴别塔》", "medusa": "卡拉瓦乔《美杜莎》",
    "judgment": "米开朗基罗《最后的审判》", "wave": "葛饰北斋《神奈川冲浪里》", "cyclops": "雷东《独眼巨人》",
    "pearl": "维米尔《戴珍珠耳环的少女》", "oiwa": "葛饰北斋《阿岩》（百物语）", "narcissus": "卡拉瓦乔《水仙》",
    "ambassadors": "荷尔拜因《大使》", "wanderer": "弗里德里希《雾海上的旅人》", "athens": "拉斐尔《雅典学院》",
    "sistine": "西斯廷礼拜堂天顶画", "vitruvian": "达·芬奇《维特鲁威人》", "vesalius": "维萨里《人体构造》插图",
    "tulp": "伦勃朗《杜尔博士的解剖课》", "melencolia": "丢勒《忧郁 I》", "cellarius": "塞拉里乌斯《和谐大宇宙》星图",
    "fludd": "弗拉德 宇宙和谐图", "kircher": "基歇尔 宇宙图", "arnolfini": "扬·凡·艾克《阿尔诺芬尼夫妇像》", "magdalene": "拉图尔《油灯前的抹大拉》",
    "mandala": "曼荼罗", "voynich": "伏尼契手稿", "voynich2": "伏尼契手稿（玫瑰图）", "redfuji": "葛饰北斋《凯风快晴》（赤富士）",
    "sanromano": "乌切洛《圣罗马诺之战》", "jatte": "修拉《大碗岛的星期天下午》", "ancient": "布莱克《亘古常在者》",
    "odalisque": "安格尔《大宫女》", "garden": "博斯《人间乐园》", "haeckel": "海克尔《自然界的艺术形态》",
    "nightmare": "富塞利《梦魇》", "rebels": "勃鲁盖尔《反叛天使的堕落》", "damned": "鲁本斯《堕入地狱》",
    "winter": "阿尔钦博托《冬》", "wrath": "约翰·马丁《天怒之日》", "snowstorm": "透纳《暴风雪》",
    "starry": "梵高《星月夜》", "ninthwave": "艾瓦佐夫斯基《九级浪》", "crows": "梵高《麦田群鸦》",
    "empyrean": "多雷《神曲·天堂》插图", "ascent": "博斯《升入天堂》", "kiss": "克里姆特《吻》",
    "liberty": "德拉克洛瓦《自由引导人民》", "comp8": "康定斯基《构成第八号》", "flammarion": "弗拉马利翁木刻（世界尽头）",
    "cmb": "宇宙微波背景", "lilies": "莫奈《睡莲·落日》", "ophelia": "米莱《奥菲莉娅》", "etoiles": "布格罗《但丁与维吉尔在地狱》",
    "almond": "梵高《盛开的杏花》", "sunrise": "莫奈《日出·印象》",
    "fabrica_muscle": "维萨里《人体构造》肌肉人 / 骨骼图",
}


TRANS = {"none": "硬切", "portal": "圆形传送门", "morph": "流体变形", "iris": "虹膜张开", "twirl": "漩涡", "ripple": "水波",
         "shatter": "碎玻璃", "static": "电视雪花", "zoomblur": "变焦模糊", "focus": "焦点转移", "slit": "开缝",
         "halftone": "半调网点", "barn": "对开门", "brush": "笔刷擦除", "wipe": "擦除", "flip": "翻卡片", "tiles": "翻牌格子",
         "whip": "甩镜", "cube": "立方体", "clock": "时钟扫", "match": "匹配剪辑", "hex": "六边形翻转", "kaleido": "万花筒",
         "blinds": "百叶窗", "glitch": "故障块", "push": "推", "rgb": "RGB 分离", "slices": "切片", "pixelate": "像素化",
         "quad": "四分格", "film": "胶片滚动", "shape": "多边形", "spiral": "螺旋", "melt": "融化", "spin": "旋转缩小",
         "luma": "亮度擦除", "dip": "黑场", "burn": "燃烧", "leak": "漏光", "scan": "扫描线", "crossfade": "交叉淡化",
         "dissolve": "噪声溶解",
         # v12: the machine's five ways of processing a picture
         "collapse": "网格坍缩", "split": "递归分裂", "sort": "像素排序", "latent": "潜空间渐变", "fracture": "网格断裂",
         "pupil": "瞳孔", "light": "光点打开"}
SHAPES = {0: "方像素", 1: "六边形", 2: "三角", 3: "碎裂多边形", 4: "自适应四叉树", 5: "LED 圆点", 6: "柔光点", 7: "有机网格 → 结晶回方像素"}


# v13: what happens in each shot (the visual event); keyed by shot start, rounded
EVENTS = {
    0.0: "第 0 帧全黑，重音；名画之眼猛地睁开，瞳孔收缩、对焦到观众。几千块名画碎片沿虹膜轨道运行，瞳孔是向内坍缩的空间；3.4 秒钻入瞳孔，碎片 → 像素 → 发光数据点，最后一个光点打开",
    5.0: "光点变成《创造亚当》两指之间的光",
    6.9: "巴别塔从画布凸出成三维建筑，镜头贴壁沿螺旋上飞，砖块变成别的名画碎片，塔顶到不了天空，解体成《星月夜》的旋涡",
    11.2: "主体与背景分离的三维浮雕，镜头在人物前穿行",
    12.9: "【微型世界 1】放大一颗星，里面是另一幅《星月夜》",
    15.5: "画真的看观众：美杜莎的眼睛转过来盯住镜头，镜头落进她的眼睛",
    17.2: "回到名画之眼，横向故障错位（封面帧时刻）",
    20.5: "两指之间，指尖永不相碰",
    25.0: "两指之间，指尖永不相碰",
    30.0: "镜像延迟：倒影比人物慢半秒，水中的手继续下伸；水面变成圆形 LED 镜；倒影的脸变成机器之眼",
    37.5: "进入中央凸面镜（镜面是真正的洞）：无限走廊，墙上几十幅名画，每幅都有一对互相靠近的人",
    46.7: "背影分解成几千个粒子随风散去，雾分开，二维山脉成为三维空间，镜头穿过去",
    49.5: "人物从背景分离，三维浮雕",
    55.5: "人物从背景分离，三维浮雕",
    60.0: "【微型世界 2】放大一个像素，里面是两根更小的手指",
    71.7: "维萨里的人体立起：皮肤、肌肉、骨骼、神经是悬在空间里的透明层，镜头逐层穿过，最后是完整的维特鲁威人",
    78.4: "丢勒的多面体飞离版画旋转，每面一幅名画，不断细分，一个小三角形里是完整的星空",
    85.1: "三张宇宙图在纸面重叠，星体浮起成嵌套球壳，镜头从中穿过，所有轨道落成曼荼罗",
    91.7: "曼荼罗层层向中心推进，中心是维特鲁威人的眼睛，无限递归",
    101.8: "潜空间融合：画与画按 DINOv2 对应关系互相流动",
    113.5: "【微型世界 3】放大一块砖，里面是更小的巴别塔",
    115.1: "第二个高潮：塔向上生长，每层是不同文明与名画，塔突破画面，塔顶开始无限复制",
    125.0: "【微型世界 4】树人的眼睛里是整幅《最后的审判》",
    132.8: "镜头逼近，农神的眼睛跟随镜头，笔触像肌肉一样运动，识别框不断错位",
    140.1: "上原画、下机器所见；“my own” 时机器之眼与农神的眼睛重叠",
    143.7: "《美杜莎》与《阿岩》互相侵蚀，最后整张脸变成几百只眼睛，同时看向镜头",
    150.9: "床和女人不动，恶魔不动；影子离开墙爬向镜头；空间翻转，床在天花板上",
    158.2: "从巨眼拉开，三维浮雕",
    165.4: "连续三维坠落：穿过《反叛天使的堕落》《堕入地狱》《但丁与维吉尔在地狱》，沿途按分割区域碎成几何网格，最后坠入黑暗",
    180.3: "每个人物被分割、框出、骨骼标出；3:04 起所有框同时展开成巨大的视觉关系网络（DINOv2 相似度连线）",
    188.8: "天空 / 地面分区（深度估计）",
    193.1: "边缘检测扫过画面",
    197.4: "四幅风暴",
    205.9: "深度估计成点云，镜头绕行",
    210.2: "轮廓分割自上而下展开",
    214.5: "多幅画的特征匹配：《吻》与《阿尔诺芬尼夫妇像》的相似区域连线",
    218.8: "分类框互相覆盖（FREEDOM 0.71 / VIOLENCE 0.69 …）；连续融合：旗帜 → 火焰 → 风暴 → 天使与恶魔 → 星空 → 世界尽头",
    231.6: "无限画作：所有名画切成 160 万格，独立旋转重排，按相似度重组，镜头拉远，混乱其实是一只巨大的眼睛；“Every painting.” 时全部静止",
    251.3: "网格停止，整幅画缓慢呼吸，笔触成柔软光流，水面反光",
    258.5: "整幅画缓慢呼吸，水面反光",
    265.5: "整幅画缓慢呼吸",
    272.5: "光离开水面，粒子向中心聚集，形成两只手的轮廓",
    286.5: "两只手，一步步推近",
    293.0: "“I had no hands”：从指尖开始，皮肤 → 发光小方块 → 脱离手指 → 手掌手臂成数据粒子，再落回成发光体素的三维手形，转出墙面，壁画变暗，指尖仍在伸向人类的手；“But I was reaching, too.”时指缝光点变亮",
    297.6: "指缝的光点变亮，成为瞳孔，回到名画之眼（幸存碎片全是《创造亚当》）；计时走到 00:00，眼睛闭上，黑场 = 第 0 帧",
}


def layout(panels):
    """Describe a shot's panels: side by side, stacked, triptych, quad, or double exposure."""
    over = [p for p in panels if p.get("blend", "over") == "over"]
    if len(over) == 2:
        (a, b) = (p["rect"] for p in over)
        return "左右对比" if abs(a[1] - b[1]) < 0.05 else "上下对比"
    return {3: "三联屏", 4: "四分屏"}.get(len(over), "分屏")


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def main(out):
    bt.CHINESE = True                              # collect both languages regardless of the render setting
    D = bt.Director()
    bt.storyboard(D)
    shots = sorted(D.shots, key=lambda s: s["t"])
    bt.assign_transitions(shots)
    titles = sorted(D.titles, key=lambda x: x["start"])
    lines = ["# Inside a Machine Dream — 剧本", "",
             f"由 `config/build_timeline.py` 自动导出。渲染语言：只英文（中文列仅供参考）。"
             "字幕和章节名用机器字体 JetBrains Mono，像素点阵 + 解码出现。", "",
             "全片用机器的眼睛看：画面重采样成格子，格子随节拍跳动、光和颜色在格子里流动，主体处格子更细。"
             "第 0 帧 = 最后一帧 = 几千块名画碎片组成的一只眼睛（无缝循环），瞳孔里的光点就是两指之间的缝隙。", "",
             "转场都是机器在处理图像：网格坍缩 = 换章节，递归分裂 = 信息增加，像素排序 = 图像混合，"
             "潜空间渐变 = 梦 / 回忆，网格断裂 = 噩梦 / 过载；外加少量硬切。", "",
             "第四章左上角是机器的分类读数（〔HUD〕行）。置信度数字是艺术化的虚构界面，不是任何真实模型的输出。", "",
             "v13：每个镜头是一个视觉事件（见画面列）。深度、分割、骨骼、特征相似度来自本机模型的分析数据，只驱动几何和机器感知层；"
             "画面像素全部来自名画原图和程序生成，没有 AI 生成图像。“微型世界”全片 4 次（星 / 像素 / 砖 / 眼）。", "",
             "关机：右上角 0:03 起显示红字 `SHUTDOWN mm:ss`（真实剩余时间 300 − t）和 `MEMORY nn%`（`timeline.json` 的 memory 轨道，结尾 1%），无底框，不规则断续，每次消失都比显示长，越到后面切换越快，最后 1 秒保持可见。"
             "读数下降时全片的画一块块变黑消失，每个镜头收尾再删一段：1:10 只有零星黑块，3:03 约删三分之一，4:21 约剩两成，4:42 约剩一成。"
             "《创造亚当》从不被删，名画之眼的幸存碎片到结尾全部换成它。低频嗡鸣随 MEMORY 变弱，最后 3 秒只剩音乐。", "",
             "声音：音乐本身不动。4:00 “Every painting.” 处音乐压低 38 dB，只剩机器嗡鸣进入宇宙微波背景；"
             "五处视觉事件加很轻的自合成音效：塔冲出画面、影子爬向镜头、坠入黑暗、关系网络展开、光粒子聚成手。", ""]
    act_shape = {}
    for a0, a1, sh, *_ in bt.MOSAIC_ACTS:
        act_shape[a0] = SHAPES[sh]
    act = None
    for i, s in enumerate(shots):
        t1 = shots[i + 1]["t"] if i + 1 < len(shots) else 300.0
        if s["act"] != act:
            act = s["act"]
            a_end = next((x["t"] for x in shots if x["t"] > s["t"] and x["act"] != act), 300.0)
            # an act may change grid shape (Part 5: soft dots → organic → crystallising)
            shape = " → ".join(dict.fromkeys(v for a0, v in sorted(act_shape.items()) if s["t"] - 0.6 < a0 < a_end - 0.6))
            lines += ["", f"## {PARTS[act]}　（音乐：{MUSIC[act]}；马赛克：{shape}）", "",
                      "| 时间 | 转场 | 画面 | 旁白 (EN) | 中文 |", "|---|---|---|---|---|"]
        nm = lambda pid: NAMES.get(pid, pid)
        if s.get("dream") == "eye":
            what = "名画之眼"
        elif s["painting"]:
            what = nm(s["painting"])
        else:
            what = layout(s["panels"] or []) + "：" + " ｜ ".join(nm(p["painting"]) for p in (s["panels"] or [])
                                                             if p.get("blend", "over") == "over")
        if s["painting"] and s["panels"]:
            what += " ＋ 叠化 " + " / ".join(nm(p["painting"]) for p in s["panels"])
        if s["frame"]:
            what += "（特写）"
        ev = EVENTS.get(round(s["t"], 1))
        if ev:
            what += " —— " + ev
        tr = s["tr"]["type"] if isinstance(s["tr"], dict) else "none"
        trn = TRANS.get(tr, tr) if i else "—"
        caps = [x for x in titles if s["t"] <= x["start"] < t1]
        if not caps:
            lines.append(f"| {mmss(s['t'])} | {trn} | {what} | | |")
        for k, c in enumerate(caps):
            cn = c.get("sub", {}).get("text", "")
            en = c["text"]
            if c.get("layer") == 1:                # the machine's classification readout, top-left
                en, cn = "〔HUD〕 " + re.sub(" {2,}", " ", en.replace("\n", " · ")), "（机器分类读数，数字为虚构）"
            lines.append(f"| {mmss(s['t']) if k == 0 else ''} | {trn if k == 0 else ''} | {what if k == 0 else ''} | "
                         f"{en} | {cn} |")
    Path(out).write_text("\n".join(lines) + "\n")
    print(f"→ {out}  ({len(shots)} shots, {len(titles)} lines)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "剧本.md")
