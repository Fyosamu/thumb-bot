@echo off
rem Daily automation for the three channels: chess -> science -> biography.
rem Task Scheduler runs this; it only ever publishes from its own machine.
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d C:\Users\USER\Desktop\chess-repo\factory
rem every mass-bank long needs its Short before the cursor reaches it
python gen_mass_shorts.py >> "C:\Users\USER\Desktop\chess-repo\factory\state\logs\task.log" 2>&1
python daily_local.py >> "C:\Users\USER\Desktop\chess-repo\factory\state\logs\task.log" 2>&1
rem Drip new thumbnails onto the chess channel (quota-limited, remembers done).
python _set_thumbs.py 2 >> "C:\Users\USER\Desktop\chess-repo\factory\state\logs\task.log" 2>&1
