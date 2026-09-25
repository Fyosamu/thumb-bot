# -*- coding: utf-8 -*-
"""Chess thumbnails: 16:9 (long) and 9:16 (short).
Gold Impact text on black bordered boxes, centered, attention hooks."""
import os, sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps

IMPACT = r"C:\Windows\Fonts\impact.ttf"
ALT = [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\ariblk.ttf"]

GOLD_TOP = (255, 238, 140)
GOLD_MID = (255, 197, 34)
GOLD_BOT = (166, 112, 0)

MODES = {"long": (1280, 720), "short": (720, 1280)}


def _build_hooks():
    """Big rotating pool of attention hooks.

    Rules: no "mate in 1/2" claims (the answer may be 3 moves deep),
    no fixed move counts, every line is a question or a dare.
    """
    h = [
        "HOW ARE YOU GOING TO SOLVE THIS?",
        "TELL ME YOU CAN SOLVE THIS",
        "SO... HOW DO YOU SOLVE THIS?",
        "THIS ONE WILL HURT YOUR BRAIN",
        "YOU CAN'T SOLVE THIS PUZZLE",
        "CAN YOU SOLVE THIS PUZZLE?",
        "ONLY 1% SOLVE THIS",
        "IMPOSSIBLE CHESS PUZZLE",
        "FIND THE MOVE OR LOSE",
        "THIS POSITION IS A LIE",
        "99% PLAY THE WRONG MOVE",
        "GRANDMASTER LEVEL TRAP",
        "SOLVE IT IN 5 SECONDS",
        "THE PUZZLE THAT BREAKS ENGINES",
        "HIDDEN KILL IS HERE",
        "LOOK CLOSER AT F7",
        "NOBODY SEES THIS COMING",
        "BLACK IS DOOMED... OR IS HE?",
        "THE SILENT KILLER MOVE",
        "SACRIFICE THAT WINS IT ALL",
        "STOP! LOOK AT THE BOARD",
        "WHY IS THIS A TRAP?",
        "YOU'LL MISS THIS MOVE",
        "FIND THE WINNING BLOW",
        "TEST YOUR BRAIN NOW",
        "THE BRILLIANT MOVE",
        "SPOT THE WINNING LINE",
        "CAN YOU CRACK THIS?",
        "THE FORK NOBODY SAW",
        "YOUR MOVE... FIND IT",
        "MISS IT AND YOU LOSE",
        "THE TRAP IS SET",
        "SHOCKING FINAL MOVE",
        "HISTORY'S BEST SACRIFICE",
        "EVERY GRANDMASTER KNOWS THIS",
        "THE MOVE THEY FEAR",
        "THIS LOSES THE GAME",
        "HIDDEN IN PLAIN SIGHT",
        "DON'T MOVE THE KNIGHT",
        "THE PERFECT AMBUSH",
        "NOT EVEN ENGINE CAN SAVE THIS",
        "THE KING IS TRAPPED",
        "NOBODY SEES THE FORK",
        "PLAY THIS AND WIN",
        "THE DEADLIEST SQUARE",
        "CALCULATE IT NOW",
        "THE CHESS ILLUSION",
        "THIS CHANGES EVERYTHING",
        "IF YOU SEE IT, YOU'RE GOOD",
        "BLUNDERS EVERYONE MAKES",
        "SOLVE OR SCROLL AWAY",
        "ARE YOU A CHESS MASTER?",
        "WILL YOU FIND IT?",
        "THE BEST MOVE IS NOT OBVIOUS",
        "CHESS GENIUSES ONLY",
        "STARE AT THIS FOR 10 SECONDS",
        "WHY IS EVERYONE BLUNDERING HERE?",
        "THE MOVE NO CLUB PLAYER SEES",
        "ONE CLICK AND YOU'RE STUCK",
        "STOP SCROLLING. SOLVE THIS.",
        "READ THE BOARD OR REGRET IT",
        "YOUR EYES WILL LIE TO YOU",
        "THE QUIET MOVE THAT HURTS MOST",
        "EVERY SQUARE IS A TRAP HERE",
        "CAN YOU SEE WHAT THE ENGINE SEES?",
        "9 OUT OF 10 MISS THIS",
        "THIS LOOKS SAFE. IT ISN'T.",
        "FIND IT BEFORE I FLIP THE BOARD",
        "THE MOST MISSED MOVE ONLINE",
        "WHAT WOULD YOU PLAY HERE?",
        "YOUR TURN. THINK.",
        "DON'T GUESS. CALCULATE.",
        "THE DEFENCE NOBODY BELIEVES IN",
        "SACRIFICE FIRST, THINK LATER",
        "ONE MOVE DECIDES EVERYTHING",
        "WHY IS THE ROOK SITTING THERE?",
        "THE HANGING PIECE IS A BAIT",
        "IT LOOKS LOSING. IT'S NOT.",
        "IT LOOKS WINNING. IT'S NOT.",
        "THE COUNTER NOBODY EXPECTS",
        "SOLVE THIS LIKE A GRANDMASTER",
        "YOU HAVE ONE TRY. USE IT.",
        "SHARP EYES ONLY",
        "THE TACTIC HIDDEN IN 3 PIECES",
        "FIND THE ONLY MOVE THAT WORKS",
        "EVERY OTHER MOVE LOSES",
        "TRY IT. I'LL WAIT.",
        "THE POSITION THAT FOOLS ENGINES",
        "CAN YOU HOLD THIS DEFENCE?",
        "THIS IS WHY YOU LOSE ENDGAMES",
        "THE PAWN THAT WINS THE GAME",
        "WATCH THE DARK SQUARES",
        "THE FORK IS ALREADY THERE",
        "COUNT THE DEFENDERS FIRST",
        "ONE SQUARE CHANGES EVERYTHING",
        "THE MOVE THAT SHOOK THE TOURNAMENT",
        "TRUST YOUR CALCULATION",
        "NO HINTS. JUST THE BOARD.",
        "THE LAST PIECE THAT MATTERS",
        "YOU ARE ABOUT TO BLUNDER",
        "SOLVE IT BEFORE THE CLOCK HITS 0",
        "WHY DID THEY GIVE UP THE PIECE?",
        "IS THE KING REALLY SAFE?",
        "THE OPEN FILE IS THE KEY",
        "MISS THIS AND IT'S OVER",
        "THE DEFLECTION THAT WINS MATERIAL",
        "FIND THE PIN BEFORE IT'S TOO LATE",
        "THE EXCHANGE THAT CHANGES EVERYTHING",
        "CAN YOU SPOT THE BACK RANK?",
        "THIS ENDGAME ISN'T DRAWN",
        "THE MOVE THAT BREAKS THE FORTRESS",
        "WHY IS THE KNIGHT SO STRONG HERE?",
        "YOUR FIRST INSTINCT IS WRONG",
        "CALCULATE TO THE END",
        "THE SILENT THREAT ON THE NEXT MOVE",
        "GRANDMASTERS SEE THIS INSTANTLY",
        "ONLY PATIENT PLAYERS FIND THIS",
        "THE QUIETEST WIN OF THE DAY",
        "LOOK TWICE BEFORE YOU TOUCH A PIECE",
        "WHY IS EVERY PIECE DEFENDING?",
        "THE SACRIFICE THAT MAKES NO SENSE",
        "IT'S NOT ABOUT THE PIECES",
        "THE MOVE YOU'LL WISH YOU FOUND",
        "ARE YOU BRAVE ENOUGH TO SACRIFICE?",
        "TWO PIECES ARE AWAITING YOU",
        "FIND THE MOVE EVERYONE MISSES",
        "THE LONGEST CALCULATION WINS",
        "THIS PUZZLE DOESN'T FORGIVE",
        "STEP BY STEP. MOVE BY MOVE.",
        "WHY IS THE QUEEN THERE?",
        "THE MOVE THAT SILENCES THE ROOM",
        "YOU SEE A DRAW. I SEE A WIN.",
        "THE ONLY CHANCE IS HIDDEN",
        "BLINK AND IT'S GONE",
        "THE WIN IS IN THE DETAILS",
        "PLAY THE MOVE THAT SCARES THEM",
        "HUNT THE WEAK KING",
        "THE PAWN STORM STARTS NOW",
        "COULD YOU DEFEND THIS?",
        "THE TACTIC YOUR COACH TAUGHT YOU",
        "IT ALL DEPENDS ON ONE MOVE",
        "YOUR CALCULATION STARTS NOW",
        "SEE THE FORK BEFORE YOU MOVE",
        "THE BEST DEFENCE IS A COUNTERATTACK",
        "WHY IS THIS POSITION DRAWN?",
        "FIND THE ONLY RESOURCE",
        "THE MOVE THAT SAVES THE GAME",
        "PLAY LIKE A CHAMPION",
        "THIS BOARD IS FULL OF SECRETS",
        "ONE MISTAKE ENDS IT",
        "THE HIDDEN DEFENCE",
        "CAN YOU OUTPLAY THE ENGINE?",
        "THE MOST BEAUTIFUL MOVE HERE",
        "WHERE IS THE COUNTERPLAY?",
        "THE REASON BEHIND THE SACRIFICE",
        "THINK BEFORE YOU RECAREER",
        "THE SQUARE THEY ALL FORGET",
        "YOU ARE CLOSER THAN YOU THINK",
        "SOLVE IT LIKE THE WORLD CHAMPION",
        "THE MOVE THAT ENDS THE ARGUMENT",
        "NO SHORTCUTS HERE",
        "THE ENDGAME TRICK THAT WORKS EVERY TIME",
        "WHY IS THE BISHOP AIMING THERE?",
        "SPOT THE UNDEFENDED PIECE",
        "THE STRATEGIC MOVE NOBODY TALKS ABOUT",
        "READ MY MIND. FIND THE MOVE.",
        "THIS POSITION HAS ONE ANSWER",
        "FIND IT AND YOU'RE READY",
        "THE CRITICAL MOMENT",
        "DARE TO CALCULATE DEEPER",
        "THE MOVE THAT OPENS EVERYTHING",
        "WATCH THE COUNTERPLAY",
        "YOU'LL THANK ME AFTER THIS",
        "THE LAST DEFENCE COLLAPSES",
        "WHY DID THE ENGINE PANIC?",
        "WHERE IS THE CHECKMATE NET?",
        "THE MOVE THAT CHANGES THE PLAN",
        "TRY TO FIND IT WITHOUT MOVING",
        "ATTACK FROM THE OTHER SIDE",
        "THE OPENING TRAP RETURNS",
        "NOTHING HERE IS WHAT IT SEEMS",
        "THE KING WISHES IT HAD AN ESCAPE",
        "EVERY MOVE HAS A PRICE",
        "THE ACCURATE MOVE IS SURPRISING",
        "THINK LIKE A MACHINE",
        "THIS BOARD IS A LIE",
        "FIND THE WIN THE CROWD MISSED",
        "THE FINAL PIECE OF THE PUZZLE",
        "LOOK AT THE H FILE",
        "THE MOST UNLUCKY BLUNDER",
        "WHY IS BLACK SMILING HERE?",
        "WHY IS WHITE SMILING HERE?",
        "COUNT THE TEMPI",
        "ONE INACCURACY AND IT'S GONE",
        "THE MOVE THAT WINS THE TIEBREAK",
        "THE ONLY SQUARE THAT WORKS",
        "YOU ARE ONE MOVE AWAY",
        "IT'S NOT OVER UNTIL IT'S OVER",
        "TRUST THE FORK",
        "THIS IS HOW CHAMPIONS THINK",
        "THE PUZZLE EVERYONE GETS WRONG",
        "SOLVE IT NOW. DON'T WAIT.",
        "THE PIN THAT DECIDES THE GAME",
        "THE MOVES SPEAK FOR THEMSELVES",
        "WATCH OUT FOR THE BACK RANKER",
        "THE SMOTHERED KING IS WAITING",
        "DISCOVER THE HIDDEN ATTACK",
        "THE MOVE THAT SHOCKED THE COMMENTATORS",
        "WHY IS THIS SO DIFFICULT?",
        "YOUR CLOCK IS TICKING",
        "A SINGLE PAWN CAN WIN THIS",
        "THE OPENING YOU SHOULD FEAR",
        "THE STRATEGY BEHIND THE SACRIFICE",
        "CAN YOU FINISH THE JOB?",
        "THE ONLY LINE THAT SURVIVES",
        "SPOT IT BEFORE THE ENGINE DOES",
        "WHY IS THE ROOK SACRIFICED?",
        "THE MOVE THAT ENDS THE DEBATE",
        "IT'S A TRAP. OR IS IT?",
        "THE MATERIAL IS EQUAL. THE POSITION ISN'T.",
        "SOLVE IT WITH YOUR EYES CLOSED",
        "EVERY CHESS PLAYER SHOULD KNOW THIS",
        "THE COUNTERATTACK YOU MISSED",
        "WHEN THE DEFENCE BECOMES AN ATTACK",
        "FIND THE ONLY KING MOVE THAT WINS",
        "THE QUEEN SAC EVERYONE DREAMS ABOUT",
        "YOU WOULDN'T DARE",
        "THE MOVE THAT WRITES HISTORY",
        "YOU HAVE TO SEE THIS",
        "WHAT IS THE BEST MOVE HERE?",
        "THE HIDDEN MOVE BEHIND THE MASK",
        "THE BOARD IS WAITING FOR YOU",
        "THE DEEPEST CALCULATION WINS",
        "LOOK AT THE FORKS IN THE CENTER",
        "THE SMALL MOVE WITH A BIG PUNCH",
        "CAN YOU SPOT THE STALEMATE TRICK?",
        "THIS IS PURE CHESS ART",
        "THE REASON THEY RESIGNED",
        "ONE PIECE DOES ALL THE WORK",
        "WHY IS THE BISHOP SO POWERFUL?",
        "YOU'LL NEVER GUESS THE FIRST MOVE",
        "THE SHARPEST LINE ON THE BOARD",
        "SOLVE IT LIKE YOU MEAN IT",
        "THE CHECK THAT CHANGES EVERYTHING",
        "ARE YOU READY FOR THE COMBINATION?",
        "IT'S TIME TO CALCULATE",
        "THE MATE NET IS ALREADY THERE",
        "THE LAST THING YOUR OPPONENT EXPECTS",
        "FIND THE HIDDEN GEOMETRY",
        "THE MOST SATISFYING FINISH",
        "WHY ARE ALL PIECES POINTING AT THE KING?",
        "ONE DEFENDER IS MISSING",
        "THE FINAL BLOW IS CLOSE",
        "NO ENGINE CAN SAVE THIS POSITION",
        "FIND THE SECOND BEST MOVE? NO. THE BEST.",
        "THE TRICK THAT WINS ON TIME",
        "WHEN EVERY MOVE IS A THREAT",
        "YOU MUST SEE THE COMBINATION",
        "THE TACTIC THAT NEVER FAILS",
        "BLUNDER OR BRILLIANCY?",
        "TRUST THE PROCESS. FIND THE MOVE.",
        "WHY IS THIS THE CRITICAL POSITION?",
        "YOU'LL BE SURPRISED BY THE ANSWER",
        "THE ANSWER IS NOT OBVIOUS",
        "LET'S SEE HOW YOU THINK",
        "PROVE YOU'RE A 2000+ PLAYER",
        "THIS IS YOUR DAILY CHESS TEST",
        "SOLVE IT BEFORE YOU SCROLL",
        "THE WIN IS HIDING IN PLAIN SIGHT",
        "SPOT THE MATING NET",
        "WHY IS THE KING WALKING FORWARD?",
        "THE MOVE THAT BREAKS EVERYTHING",
        "FIND THE ONLY MOVE OR GAME OVER",
        "THE CLEVEREST MOVE TODAY",
        "CAN YOU FIND THE UNICORN MOVE?",
        "THE ENDGAME HAS SECRETS",
        "HOW DID THEY MISS THIS?",
        "THE MOST BEAUTIFUL TACTIC ONLINE",
        "YOU ARE BEING TESTED",
        "DO YOU SEE THE THREAT?",
        "WHAT COMES AFTER THE SACRIFICE?",
        "IT TAKES COURAGE TO PLAY THIS",
        "THE POSITION THAT MAKES YOU THINK",
        "STOP. CALCULATE. MOVE.",
        "THE WIN STARTS WITH A PAWN",
        "WHY IS THE KNIGHT ON THE RIM?",
        "YOU'LL WANT TO TAKE THAT PIECE. DON'T.",
        "THE ONLY CHANCE TO ESCAPE",
        "ONE MOVE SEPARATES YOU FROM VICTORY",
        "THE UNEXPECTED RESOURCE",
        "FIND THE MOVE BEFORE I DO",
        "THIS IS WHERE THE GAME IS WON",
        "THE KING HUNT BEGINS NOW",
        "ARE YOU SURE THE PIN WORKS?",
        "THE FORGOTTEN DEFENSIVE MOVE",
        "DOES THE QUEEN HAVE ENOUGH SQUARES?",
        "THE MOST MISUNDERSTOOD POSITION",
        "YOU HAVE TO CALCULATE TWICE",
        "FIND THE MOVE THAT MAKES THE CROWD CHEER",
        "THIS IS PURE MAGIC",
        "ONE MISTAKE AND IT'S A DRAW",
        "WHY IS THIS ENDGAME WON?",
        "WHAT IS THE ONLY MOVE THAT WINS?",
        "THE HIDDEN GEM OF THIS POSITION",
        "I CHALLENGE YOU TO SOLVE THIS",
        "THE MOVE THAT BREAKS THE INTERNET",
        "THE LONG CALCULATION PAYS OFF",
        "YOUR OPPONENT HOPES YOU MISS IT",
        "PLAY THE MOVE THAT LOOKS WRONG",
        "THE CRITICAL SQUARE IS OPEN",
        "WHY DID THEY LEAVE THE PIECE HANGING?",
        "THE ATTACK NOBODY SAW COMING",
        "IT'S A BRILLIANCY. CAN YOU FIND IT?",
        "THE FINAL SEQUENCE",
        "YOU ARE LOOKING AT THE WRONG PIECE",
        "THE MOVE THAT SURPRISED THE ENGINE",
        "WHEN PATIENCE BECOMES A WEAPON",
        "THE ONLY MOVE I WOULD PLAY",
        "CAN YOU HOLD THE TENSION?",
        "THE SECRET OF THIS POSITION",
        "YOUR TURN TO BE CREATIVE",
        "THE MOVE THAT DESERVES A ROUND OF APPLAUSE",
        "WHY IS THIS GAME STILL ALIVE?",
        "SHOW ME YOU CAN FINISH THIS",
        "THE MOST PAINFUL MOVE TO FACE",
        "EVERY CHESS FAN SHOULD SOLVE THIS",
        "LOOK BEYOND THE OBVIOUS",
        "FIND THE MOVE THAT MAKES IT ALL CLICK",
        "DOES THE FORK REALLY WORK?",
        "THE CHESS PUZZLE THAT NEVER GETS OLD",
        "YOU ARE ONE INSIGHT AWAY",
        "IS THE SACRIFICE SOUND?",
        "WHAT WOULD A GRANDMASTER PLAY?",
        "THE MOVE YOU DIDN'T EXPECT",
        "TAKE A DEEP BREATH AND SOLVE",
        "THIS IS THE MOMENT OF TRUTH",
        "WHY IS THE PAWN SO DANGEROUS NOW?",
        "THE LAST MOVE WAS A MISTAKE",
        "CAN YOU PUNISH IT?",
        "THE ONE MOVE THAT MAKES EVERYTHING WORK",
        "NOW OR NEVER",
        "THE FINISHING SEQUENCE IS RIGHT THERE",
        "THE POSITION DEMANDS A SACRIFICE",
        "FIND THE MOVE THAT SILENCES DOUBT",
        "WHEN YOUR OPPONENT'S BEST MOVE IS A RETREAT",
        "YOU'LL WANT TO PAUSE THE VIDEO",
        "THE MOST UNEXPECTED WIN",
        "WHERE IS THE COUNTERATTACK?",
        "THE BOARD IS SET FOR A COMBINATION",
        "YOU WILL NOT BELIEVE THIS ONE",
        "THIS POSITION IS PURE CHAOS",
        "WHY IS THE ENGINE SCREAMING?",
        "TRY NOT TO BLUNDER",
        "THE MOVE THAT CLOSES THE GAME",
        "SOLVE IT LIKE A PRO",
        "FIND THE ONLY PATH TO VICTORY",
        "WHAT IS THE CORRECT ORDER OF MOVES?",
        "THE PUZZLE THAT SEPARATES AMATEURS FROM PROS",
        "THE HIT THAT ENDS THE DEBATE",
        "PROVE YOU UNDERSTAND THIS POSITION",
        "WHY IS THE ROOK SACRIFICED?",
        "SOLVE IT BEFORE THE HINT COMES",
        "WHAT IS YOUR FIRST MOVE?",
        "THE MASTERCLASS MOVE",
        "YOU'VE SEEN THIS PATTERN BEFORE",
        "ONE SQUARE AWAY FROM VICTORY",
        "THE REASON THIS POSITION IS FAMOUS",
        "FIND THE MOVE THAT MAKES HISTORY",
        "WHEN THE DEFENCE FINALLY CRACKS",
        "THE FINAL WORD IS YOURS",
    ]
    # combinatorial families -> grows the pool past 1000 unique lines
    who = ["YOU", "99% OF PLAYERS", "EVERY BEGINNER", "MOST CHESS FANS", "NOBODY",
           "ALMOST EVERYONE", "CLUB PLAYERS", "YOUNG TALENTS", "YOUR FRIENDS",
           "EXPERTS AT FIRST GLANCE", "STREAMERS", "PEOPLE ONLINE"]
    fail = ["CAN'T SOLVE THIS", "WILL NEVER SEE THIS", "MISS THIS EVERY TIME",
            "BLUNDER THIS POSITION", "FAIL THIS TEST", "GET THIS WRONG",
            "PLAY THE OBVIOUS MOVE", "FALL FOR THIS TRAP", "CHOOSE THE WRONG SQUARE",
            "GIVE UP ON THIS POSITION"]
    for a in who:
        for b in fail:
            h.append("%s %s" % (a, b))
    for p in (1, 2, 3, 4, 5, 7, 10, 12, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 95, 99):
        h += ["ONLY %d%% SOLVE THIS" % p, "%d%% GET THIS WRONG" % p,
              "%d%% PLAY THE WRONG MOVE" % p, "%d%% CAN'T FIND IT" % p,
              "CAN YOU BEAT THE %d%%?" % p, "THE MOVE %d%% MISS" % p,
              "ONLY %d%% SEE THE SECOND MOVE" % p]
    for s in (3, 5, 7, 8, 10, 12, 15, 20, 30, 60):
        h += ["CAN YOU FIND IT IN %d SECONDS?" % s, "SOLVE IT IN %d SECONDS" % s,
              "YOU HAVE %d SECONDS. GO." % s, "%d SECONDS TO FIND THE MOVE" % s]
    for adj in ("BRILLIANT", "SHOCKING", "SILENT", "DEADLY", "CUNNING", "BEAUTIFUL",
                "STRATEGIC", "TACTICAL", "UNEXPECTED", "HIDDEN", "DANGEROUS", "PAINFUL",
                "RUTHLESS", "CLEVER", "TRICKY", "QUIET", "SHARP", "DEEP", "EASY",
                "TRAGIC", "MAGICAL", "TEXTBOOK", "GENIUS", "NASTY", "CLEAN", "PURE",
                "INSANE", "CRAZY", "LEGENDARY", "MASTERFUL", "DELICIOUS", "DEVASTATING",
                "SPOT-ON", "SURPRISING", "FAMOUS", "CLASSIC", "MODERN", "VINTAGE",
                "FEARLESS", "PATIENT", "BRUTAL", "GENTLE", "LOADED", "PICTURE-PERFECT"):
        h += ["THE %s MOVE THEY ALL MISS" % adj,
              "THIS %s TACTIC ALWAYS WORKS" % adj,
              "WHY IS THIS THE %s MOVE?" % adj,
              "%s! CAN YOU SEE WHY?" % adj]
    for target in ("THE HANGING QUEEN", "THE OPEN FILE", "THE WEAK KING", "THE LONE PAWN",
                   "THE SLEEPING BISHOP", "THE TRAPPED KNIGHT", "THE EMPTY BACK RANK",
                   "THE CENTRAL PAWN", "THE DEFENCE", "THE FORGOTTEN ROOK",
                   "THE CASTLED KING", "THE PASSED PAWN"):
        h += ["PUNISH %s NOW" % target, "ATTACK %s BEFORE IT'S TOO LATE" % target,
              "EVERYTHING ABOUT %s" % target, "WHY IS %s SO IMPORTANT?" % target]
    for thing in ("ENGINE", "GRANDMASTER", "COMMENTATORS", "WORLD CHAMPION",
                  "YOUR COACH", "THE CROWD", "YOUR OPPONENT", "THE ARBITER",
                  "SOCIAL MEDIA", "THE EXPERTS"):
        h += ["THE MOVE THAT SHOCKED THE %s" % thing, "WHY DID THE %s MISS IT?" % thing,
              "NOBODY TOLD THE %s" % thing, "THE %s COULDN'T BELIEVE THIS" % thing]
    for area in ("F7", "THE CENTER", "THE BACK RANK", "THE H FILE", "THE D FILE",
                 "THE QUEENSIDE", "THE DARK SQUARES", "THE OPEN FILE", "THE KING SIDE",
                 "THE PASSING PAWN", "THE BACK RANK", "THE CORNER", "THE LAST RANK"):
        h += ["LOOK CLOSER AT %s" % area, "EVERYTHING DEPENDS ON %s" % area,
              "THE SECRET IS IN %s" % area, "WATCH %s CAREFULLY" % area]
    for verb in ("FIND THE WINNING MOVE", "SPOT THE HIDDEN THREAT", "CRACK THIS POSITION",
                 "BREAK THE DEFENCE", "SEE THE COMBINATION", "FINISH THE GAME",
                 "PUNISH THE MISTAKE", "TURN THE TIDE", "ESCAPE THE TRAP",
                 "WIN THE ENDGAME", "HOLD THE POSITION", "SAVE THE GAME"):
        h += [verb + " NOW", verb + " BEFORE IT'S TOO LATE", verb + " OR LOSE",
              "CAN YOU " + verb + "?", verb + " LIKE A PRO"]
    seen, out = set(), []
    for x in h:
        x = " ".join(x.upper().split())
        if 8 <= len(x) <= 44 and x not in seen:
            seen.add(x)
            out.append(x)
    return out


HOOKS = _build_hooks()
# aliases kept for older scripts
CHESS_HOOKS = HOOKS


def load_font(size):
    for p in [IMPACT] + ALT:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def fit_cover(img, w, h):
    img = img.convert("RGB")
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    img = img.resize((max(w, int(sw * scale + 0.5)), max(h, int(sh * scale + 0.5))), Image.LANCZOS)
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def gold_gradient(w, h):
    g = Image.new("RGB", (w, h))
    px = g.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.55:
            k = t / 0.55
            c = tuple(int(GOLD_TOP[i] + (GOLD_MID[i] - GOLD_TOP[i]) * k) for i in range(3))
        else:
            k = (t - 0.55) / 0.45
            c = tuple(int(GOLD_MID[i] + (GOLD_BOT[i] - GOLD_MID[i]) * k) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return g


def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make(src, out, mode="long", hook_idx=0, color_base=True, hook_text=None):
    W, H = MODES[mode]
    img = Image.open(src)
    img = fit_cover(img, W, H)

    if color_base:
        base = ImageEnhance.Color(img).enhance(0.9)
        base = ImageEnhance.Contrast(base).enhance(1.12)
    else:
        base = ImageOps.grayscale(img)
        base = ImageEnhance.Contrast(base).enhance(1.35).convert("RGB")

    # clone a neighbouring strip over the generator watermark (bottom-right)
    wm_w, wm_h = int(W * 0.26), int(H * 0.11)
    x0, y0 = W - wm_w, H - wm_h
    src_x = max(0, x0 - wm_w)
    patch = base.crop((src_x, y0, x0, H))
    patch = patch.transpose(Image.FLIP_LEFT_RIGHT)
    base.paste(patch, (x0, y0))

    # vignette
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.35, -H * 0.45, W * 1.35, H * 1.45], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    base = Image.composite(base, Image.new("RGB", (W, H), (6, 6, 6)), vig)

    hook = (hook_text or HOOKS[hook_idx % len(HOOKS)]).upper()
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    maxw = W - (120 if mode == "long" else 70)
    maxh = int(H * (0.40 if mode == "long" else 0.28))

    size = int(W * 0.085) if mode == "long" else int(W * 0.115)
    while size >= 36:
        f = load_font(size)
        lines = wrap(probe, hook, f, maxw)
        if len(lines) * int(size * 1.06) <= maxh:
            break
        size -= 4
    font = load_font(size)
    lines = wrap(probe, hook, font, maxw)
    lh = int(size * 1.06)

    pad_x, pad_y, gap = 22, 12, 10
    boxes = []
    total_h = 0
    for ln in lines:
        tw = probe.textlength(ln, font=font)
        bw, bh = int(tw) + pad_x * 2, lh + pad_y * 2
        boxes.append((ln, int(tw), bw, bh))
        total_h += bh + gap
    total_h -= gap

    y0 = int(H * (0.055 if mode == "long" else 0.045))  # glued to top

    # darken exactly behind the text block
    band = Image.new("L", (W, H), 0)
    bd = ImageDraw.Draw(band)
    top, bot = y0 - 45, y0 + total_h + 45
    for i in range(H):
        if top <= i <= bot:
            v = 170
        else:
            d = min(abs(i - top), abs(i - bot))
            v = int(max(0, 155 - d * 0.5))
        bd.line([(0, i), (W, i)], fill=v)
    base = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), base, band)

    # shadow pass
    sh = Image.new("L", (W, H), 0)
    shd = ImageDraw.Draw(sh)
    yy = y0
    for ln, tw, bw, bh in boxes:
        bx = (W - bw) // 2 + 7
        shd.rounded_rectangle([bx, yy + 7, bx + bw, yy + bh + 7], radius=10, fill=255)
        yy += bh + gap
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    base.paste((0, 0, 0), (0, 0), sh)

    # black boxes with gold border
    d = ImageDraw.Draw(base)
    yy = y0
    text_mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(text_mask)
    for ln, tw, bw, bh in boxes:
        bx = (W - bw) // 2
        d.rounded_rectangle([bx, yy, bx + bw, yy + bh], radius=10, fill=(0, 0, 0))
        md.text(((W - tw) // 2, yy + pad_y - int(lh * 0.14)), ln, font=font, fill=255)
        yy += bh + gap

    grad = gold_gradient(W, H)
    base.paste(grad, (0, 0), text_mask)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    base.save(out, quality=95)
    return out, hook


if __name__ == "__main__":
    src = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "long"
    idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    out = sys.argv[4] if len(sys.argv) > 4 else (
        r"C:\Users\USER\Desktop\chess_sample\thumb_%s.jpg" % mode)
    color = not (len(sys.argv) > 5 and sys.argv[5] == "bw")
    p, h = make(src, out, mode, idx, color_base=color)
    print("saved:", p, "| hook:", h)
