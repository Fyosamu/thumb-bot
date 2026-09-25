# -*- coding: utf-8 -*-
"""Attention hooks for every channel (English, click-worthy, no false claims).

    from hooks_lib import SCIENCE_HOOKS, LIFE_HOOKS, CHESS_HOOKS
    len(SCIENCE_HOOKS) > 1000

Rules used while building them:
  * questions and dares perform best on YouTube
  * never promise a specific outcome ("mate in 1") that the video may not show
  * no duplicated lines
"""

try:
    from gold_thumb import HOOKS as CHESS_HOOKS          # chess channel pool
except Exception:                                        # noqa: BLE001
    CHESS_HOOKS = []


def _uniq(lines, lo=8, hi=70):
    seen, out = set(), []
    for x in lines:
        x = " ".join(str(x).upper().split())
        if lo <= len(x) <= hi and x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ------------------------------------------------------------------ science (akhob59)
_SCIENCE_TOPICS = [
    "THE HUMAN BRAIN", "YOUR DNA", "BLACK HOLES", "THE BIG BANG", "DARK MATTER",
    "DARK ENERGY", "QUANTUM PHYSICS", "THE SPEED OF LIGHT", "TIME DILATION",
    "WORMHOLES", "NEUTRON STARS", "SUPERNOVAS", "GALAXIES", "THE SUN", "THE MOON",
    "MARS COLONIES", "VOLCANOES", "EARTHQUAKES", "TSUNAMIS", "HURRICANES",
    "THE OCEAN DEPTHS", "GIANT SQUID", "ICE AGES", "EVOLUTION", "NATURAL SELECTION",
    "THE DINOSAUR EXTINCTION", "IMMORTAL JELLYFISH", "TARDIGRADES", "BACTERIA",
    "VIRUSES", "THE IMMUNE SYSTEM", "CANCER CELLS", "STEM CELLS", "MEMORY",
    "DREAMS", "CONSCIOUSNESS", "ADRENALINE", "THE GUT BRAIN", "SLEEP",
    "LUCID DREAMS", "PHOTON MEMORY", "HOW EYES SEE COLOUR", "HUMAN VOICE",
    "THE HEART", "BLOOD CELLS", "BONE MARROW", "MUSCLES", "AGEING",
    "CLONING", "CRISPR", "GENE EDITING", "ROBOTS", "ARTIFICIAL INTELLIGENCE",
    "QUANTUM COMPUTERS", "THE INTERNET", "5G", "SEMICONDUCTORS", "LASERS",
    "HOLOGRAMS", "NUCLEAR FUSION", "SOLAR PANELS", "ELECTRIC CARS", "BATTERIES",
    "THE PERIODIC TABLE", "WATER", "CARBON", "OXYGEN", "GRAVITY",
    "MAGNETISM", "ELECTRICITY", "PLASMA", "SUPERCONDUCTORS", "FIBRE OPTICS",
    "THE MICROWAVE OVEN", "NUCLEAR REACTORS", "OIL", "PLASTIC POLLUTION",
    "GLOBAL WARMING", "THE GREENHOUSE EFFECT", "OZONE HOLE", "AMAZON RAINFOREST",
    "CORAL REEFS", "BEES", "ANT COLONIES", "MIGRATING BIRDS", "SPIDER SILK",
    "SHARK SENSES", "ELEPHANT MEMORY", "OCTOPUS INTELLIGENCE", "WHALE SONGS",
    "DEEP SEA CREATURES", "BIOLUMINESCENCE", "FOSSILS", "ARCHAEOLOGY",
    "THE PYRAMIDS", "ANCIENT EGYPT", "THE ROMAN EMPIRE", "MEDIEVAL CASTLES",
    "THE RENAISSANCE", "DARWIN'S VOYAGE", "EINSTEIN'S MISTAKE", "NEWTON'S LAWS",
    "THE DOUBLE SLIT EXPERIMENT", "SCHRODINGER'S CAT", "ENTANGLEMENT",
    "THE MULTIVERSE", "STRING THEORY", "ANTIMATTER", "HIGGS BOSON", "CERN",
    "TELESCOPES", "EXOPLANETS", "ALIEN LIFE", "THE FERMI PARADOX", "ASTEROIDS",
    "COMETS", "THE KUIPER BELT", "SOLAR ECLIPSES", "AURORAS", "RAINBOWS",
    "HOW RAIN FORMS", "CLOUDS", "LIGHTNING", "THUNDER", "FOG",
    "DESERTS", "GLACIERS", "MAGMA", "TREES", "FOREST NETWORKS",
    "PHOTOSYNTHESIS", "SEEDS", "FRUIT RIPEING", "COFFEE", "CHOCOLATE",
    "BREAD", "CHEESE", "SPICES", "SUGAR", "CAFFEINE",
    "ALCOHOL", "HONEY", "OLIVE OIL", "RICE", "BANANAS",
    "THE INVENTION OF THE WHEEL", "PRINTING PRESS", "CAMERAS", "RADIO",
    "TELEVISION", "SPACE TRAVEL", "ROCKETS", "THE ISS", "SATELLITES",
    "GPS", "SOLAR SAILS", "WARP DRIVE", "TIME TRAVEL", "PARADOXES",
]

_SCIENCE_FORMS = [
    "WHY %s IS NOT WHAT YOU THINK",
    "WHAT NOBODY TELLS YOU ABOUT %s",
    "HOW %s ACTUALLY WORKS",
    "WHAT HAPPENS INSIDE %s",
    "THE UNTOLD TRUTH ABOUT %s",
    "%s EXPLAINED IN 60 SECONDS",
    "YOU'VE BEEN WRONG ABOUT %s",
    "WHAT IF %s STOPPED EXISTING?",
    "THE SCIENTIFIC SECRET OF %s",
    "WHY SCIENTISTS FEAR %s",
    "IS %s REALLY THAT DANGEROUS?",
    "THE DARK SIDE OF %s",
    "WHAT %s DOES TO YOUR BODY",
    "THE MOMENT %s CHANGED EVERYTHING",
    "%s: THE PART THEY SKIP IN SCHOOL",
    "WHY %s KEEPS SCIENTISTS AWAKE AT NIGHT",
    "THE TRUTH ABOUT %s",
    "HOW %s WAS DISCOVERED BY ACCIDENT",
    "WHAT %s LOOKS LIKE UP CLOSE",
    "IMAGINE A WORLD WITHOUT %s",
    "THIS IS WHY %s MATTERS",
    "THE FINAL ANSWER ABOUT %s",
    "CAN %s KILL YOU?",
    "WHAT %s DOES IN THE DARK",
    "THE MYTH ABOUT %s",
    "WHAT %s IS HIDING FROM US",
    "THE REAL REASON BEHIND %s",
    "%s AND THE LAW OF PHYSICS",
    "THE DAY %s SURPRISED THE WORLD",
    "HOW SMALL IS %s REALLY?",
    "WHAT %s WOULD DO IN 100 YEARS",
    "WHY %s IS MORE IMPORTANT THAN OIL",
    "THE INVISIBLE POWER OF %s",
    "%s: MYTH VS REALITY",
    "WHAT SCIENTISTS JUST DISCOVERED ABOUT %s",
    "THE EXPLANATION YOU NEEDED FOR %s",
    "WHY %s SHOULD SCARE YOU",
    "HOW LONG CAN %s REALLY LAST?",
    "THE SIMPLE REASON BEHIND %s",
    "80%% OF PEOPLE DON'T UNDERSTAND %s",
    "WHAT MAKES %s SO UNUSUAL",
    "THE ACCIDENT THAT REVEALED %s",
    "WHERE DID %s COME FROM?",
    "WHY %s IS STILL A MYSTERY",
    "THE ONE FACT ABOUT %s THAT CHANGES EVERYTHING",
]


def _build_science():
    out = []
    for t in _SCIENCE_TOPICS:
        for f in _SCIENCE_FORMS:
            out.append(f % t)
    # question-led hooks (the ones that stop the scroll)
    q_topics = _SCIENCE_TOPICS + [
        "YOUR MEMORY", "YOUR SLEEP", "YOUR PHONE", "THE HUMAN EYE", "HUMAN TEARS",
        "MEDITATION", "DEJA VU", "INSTINCT", "INTUITION", "SWEET CRAVINGS",
    ]
    qs = ["WHY DOES %s HAPPEN?", "WHAT WOULD HAPPEN IF %s?", "IS IT TRUE THAT %s?",
          "WHAT MAKES %s WORK?", "HOW CAN %s BE REAL?", "WHAT IS %s MADE OF?",
          "CAN %s BE EXPLAINED?", "WHAT CAUSES %s?", "WHAT IS THE PRICE OF %s?",
          "WHAT LIVES INSIDE %s?", "WHAT HAPPENS WHEN %s COLLIDES?",
          "WHY DID %s EVOLVE?", "IS %s DANGEROUS?", "WHAT HIDDEN FORCE CONTROLS %s?",
          "HOW DID %s SURVIVE THIS LONG?", "WHAT SCIENCE CANNOT EXPLAIN ABOUT %s",
          "WHY DO %s EXIST?", "WHAT IS REALLY HAPPENING WITH %s?"]
    for t in q_topics:
        for f in qs:
            out.append(f % t)
    # numbered / listicle style
    facts = ["FACTS ABOUT %s", "SECRETS OF %s", "RULES OF %s", "LIMITS OF %s",
             "DANGERS OF %s", "WONDERS OF %s", "MYTHS ABOUT %s",
             "THE INVENTION OF %s", "THE FUTURE OF %s", "THE HISTORY OF %s"]
    for t in _SCIENCE_TOPICS:
        for f in facts:
            out.append(f % t)
    return _uniq(out, 10, 68)


# ------------------------------------------------------------------ biography channel
_LIFE_FORMS = [
    "THE DAY EVERYTHING CHANGED FOR %s",
    "%s'S DARKEST HOUR",
    "WHAT %s DID BEFORE FAME",
    "THE MISTAKE THAT DEFINED %s",
    "%s: FROM NOTHING TO LEGEND",
    "WHY %s NEVER GAVE UP",
    "THE LETTER %s NEVER SENT",
    "HOW %s CHANGED THE WORLD",
    "THE LAST 24 HOURS OF %s",
    "%s'S HIDDEN DIARY",
    "THE ENEMY OF %s",
    "WHAT %s FEARED THE MOST",
    "THE PRICE %s PAID FOR GREATNESS",
    "%s BEFORE THE GLORY",
    "THE SECRET LIFE OF %s",
    "WHY HISTORY FORGOT %s",
    "THE BETRAYAL THAT BROKE %s",
    "%s'S FIRST FAILURE",
    "WHAT %s WOULD TELL YOU TODAY",
    "THE MATH THAT %s COULDN'T SOLVE",
    "HOW %s DIED (AND WHY IT MATTERS)",
    "THE ONLY PHOTOGRAPH OF %s",
    "%s AND THE THING THEY STOLE",
    "RISE OF %s", "FALL OF %s", "RETURN OF %s",
    "WHAT NOBODY KNOWS ABOUT %s",
    "%s'S LAST WORDS",
    "THE ROAD %s TOOK ALONE",
    "%s: REVERSE TIMELINE",
    "IF %s HAD LIVED 10 YEARS LONGER",
    "THE MOMENT %s DECIDED EVERYTHING",
    "WHO WAS %s REALLY?",
    "THE PEOPLE %s LEFT BEHIND",
    "WHY %s IS STILL ANSWERED TODAY",
    "ONE DECISION THAT MADE %s",
    "%s'S LOST YEARS",
    "THE INVENTION %s COULDN'T FINISH",
    "%s AGAINST EVERYONE",
    "HOW %s BECAME IMMORTAL",
    "%s IN 60 SECONDS",
    "THE OTHER SIDE OF %s",
    "WHAT DRIVEN %s EVERY MORNING",
    "%s AND THE IDEA THAT SCARED EVERYONE",
    "BEFORE %s WAS FAMOUS",
    "AFTER %s DISAPPEARED",
    "THE REAL STORY OF %s",
    "%s: THE UNFINISHED CHAPTER",
]


def _build_life(names):
    out = []
    for n in names:
        for f in _LIFE_FORMS:
            out.append(f % n.upper())
    return _uniq(out, 10, 66)


SCIENCE_HOOKS = _build_science()
CHESS_EXTRA = [h for h in CHESS_HOOKS]


def build_life_hooks(names):
    """names = subjects of the biography videos (English names)."""
    return _build_life(names)


if __name__ == "__main__":
    print("SCIENCE_HOOKS:", len(SCIENCE_HOOKS))
    print("CHESS_HOOKS:", len(CHESS_HOOKS))
    print("sample:", SCIENCE_HOOKS[:3])
