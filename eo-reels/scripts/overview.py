"""One sheet of the whole video, to see who appears and find chapter cards. Reads keyframes only, so it is quick.
usage: overview.py <source.mp4> <out.jpg> [seconds-between-tiles, default fits about 60 tiles]"""
import sys
from common import probe, run_ff

src, out = sys.argv[1:3]
dur = probe(src)["duration"]
step = float(sys.argv[3]) if len(sys.argv) > 3 else max(dur / 60, 2)
n = int(dur / step) + 1; rows = (n + 5) // 6
run_ff("-skip_frame", "nokey", "-i", src, "-vf",
       f"fps=1/{step},scale=320:-1,drawtext=text='%{{pts\\:hms}}':x=4:y=4:fontsize=16:fontcolor=yellow,tile=6x{rows}",
       "-frames:v", "1", "-q:v", "4", out)
print(f"{n} tiles, one every {step:.0f} s, left to right from 0:00")
