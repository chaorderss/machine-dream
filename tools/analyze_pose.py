#!/usr/bin/env python3
"""MediaPipe pose on every figure-sized SAM segment → assets/analysis/pose/<id>.json. Run with the mediapipe venv:
  python tools/analyze_pose.py judgment athens liberty ...
"""
import json,os,sys,numpy as np,cv2
from pathlib import Path
import mediapipe as mp
from mediapipe.tasks import python as P
from mediapipe.tasks.python import vision as V
R=Path(__file__).resolve().parent.parent/'assets'
opts=V.PoseLandmarkerOptions(base_options=P.BaseOptions(model_asset_path=str(Path(os.environ.get('MODELS_DIR',R.parent/'models'))/'pose/pose_landmarker_heavy.task')),num_poses=1,min_pose_detection_confidence=.3,min_pose_presence_confidence=.3)
lm=V.PoseLandmarker.create_from_options(opts)
out=R/'analysis/pose'; out.mkdir(exist_ok=True)
for pid in sys.argv[1:]:
    im=cv2.cvtColor(cv2.imread(str(R/f'paintings/{pid}.png')),cv2.COLOR_BGR2RGB)
    H,W=im.shape[:2]
    seg=json.load(open(R/f'analysis/seg/{pid}.json'))
    res=[]
    # run the pose model on every figure-sized segment's crop
    for i,s in enumerate(seg):
        if s is None or not(.0015<s['area']<.15): continue
        x0,y0,x1,y1=s['bbox']; bw,bh=x1-x0,y1-y0
        if bh*H<80: continue
        x0=max(0,x0-bw*.2);x1=min(1,x1+bw*.2);y0=max(0,y0-bh*.2);y1=min(1,y1+bh*.2)
        c=im[int(y0*H):int(y1*H),int(x0*W):int(x1*W)]
        r=lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=c.copy()))
        if not r.pose_landmarks: continue
        pts=[[x0+p.x*(x1-x0),y0+p.y*(y1-y0),p.visibility] for p in r.pose_landmarks[0]]
        vis=np.mean([p[2] for p in pts[11:29]])
        if vis<.45: continue
        res.append({"seg":i+1,"bbox":s['bbox'],"pts":pts,"vis":float(vis)})
    json.dump(res,open(out/f'{pid}.json','w'))
    print(pid,len(res),flush=True)
