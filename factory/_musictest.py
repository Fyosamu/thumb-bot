import sys, json, os
repo = r"C:\Users\USER\Desktop\chess-repo"
sys.path.insert(0, os.path.join(repo, "bot"))
sys.path.insert(0, os.path.join(repo, "factory"))
import music_lib
ff = music_lib.get_ffmpeg()
demo = json.loads(open(os.path.join(repo, "puzzles_pool.jsonl"), encoding="utf-8").readline())
outd = os.path.join(repo, "factory", "work", "musictest")
v = music_lib.make_video([demo], outd, "mt", ff=ff)
s = music_lib.make_short(demo, outd, "mt", 1, ff=ff)
print("LONG:", v)
print("SHORT:", s)
