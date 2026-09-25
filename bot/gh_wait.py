"""Wait for one specific sd-gen run and pull its image.

    python bot/gh_wait.py <run_id> <out.jpg>

Used when a dispatch already went out but the polling client died, so the
run keeps cooking on GitHub and we just re-attach to it.
"""
import sys
import time

import gh_gen

def main(run_id, out, timeout=3600):
    t_end = time.time() + timeout
    while time.time() < t_end:
        r = gh_gen._req("GET", "/repos/%s/actions/runs/%s" % (gh_gen.REPO, run_id))
        st, con = r.get("status"), r.get("conclusion")
        print("[gh] run %s %s %s" % (run_id, st, con or ""), flush=True)
        if st == "completed":
            if con != "success":
                raise SystemExit("run %s failed: %s" % (run_id, con))
            gh_gen.download(run_id, out)
            print("saved %s" % out, flush=True)
            return
        time.sleep(30)
    raise SystemExit("run %s still not finished after %ss" % (run_id, timeout))

if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2])
