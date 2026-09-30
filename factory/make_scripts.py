"""Refill the content queue without any paid API.

Writes new script JSONs from a curated fact bank that lives in this file.
Each fact carries its stock-footage search term, so the rendered video always
has matching visuals. Nothing here calls an LLM - the scripts are assembled
locally and for free.

Usage:
    python make_scripts.py --count 5
    python make_scripts.py --count 5 --seed 7      # different selection
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content"

VOICE = "en-US-AvaMultilingualNeural"

# (slug, title, thumb_text, thumb_stock, fact[narration, stock])
FACTS: dict[str, dict] = {
    "ocean": {
        "title": "The Deep Ocean Is Hiding Something Terrifying",
        "thumb": "80% UNSEEN", "stock": "deep ocean dark water",
        "lines": [
            ("We have mapped Mars in more detail than our own ocean floor. Eighty percent of the sea has never been seen by a human being.", "deep ocean dark water"),
            ("Mars is fully photographed. The ocean is a guess, drawn mostly from sound.", "spaceship mars surface"),
            ("Sunlight dies at one thousand meters. Below that there is no warmth, no color, and pressure enough to crush a submarine.", "diver descending underwater"),
            ("And yet life is everywhere. Most deep sea creatures make their own light. Glowing is not rare. Being visible is.", "jellyfish glowing dark"),
            ("We have found canyons deeper than the Grand Canyon. None of them have a name.", "underwater canyon abyss"),
            ("The largest world we have is the one we live on top of, and we have barely looked.", "surface of the sea horizon"),
        ],
    },
    "coffee": {
        "title": "What Coffee Actually Does To Your Brain In 10 Minutes",
        "thumb": "10 MINUTES", "stock": "coffee cup steam dark",
        "lines": [
            ("Coffee does not give you energy. Nothing in that cup adds fuel to your body.", "coffee pouring cup"),
            ("While you are awake your brain stacks up a chemical called adenosine. That pressure is what you feel as tiredness.", "sleepy person morning"),
            ("Caffeine looks almost identical to adenosine, so it slips into the same receptors and blocks them. The tiredness is still there. You just cannot feel it.", "molecule abstract science"),
            ("Ten minutes in, your pupils dilate. Forty five minutes in, adenosine production stops and you hit peak alertness.", "energetic person running"),
            ("Six hours later half the caffeine is still in your blood. A three o'clock coffee is still working at nine tonight.", "hourglass sand passing"),
            ("Since the adenosine was only blocked and never cleared, it returns all at once. That is the crash. You were borrowing from tomorrow.", "person sleeping bed night"),
        ],
    },
    "procrastination": {
        "title": "The Real Reason You Procrastinate (It's Not Laziness)",
        "thumb": "NOT LAZINESS", "stock": "tired man desk office",
        "lines": [
            ("You are not lazy. If you were lazy you would not feel guilty. The fact that you care is proof something else is going on.", "man tired desk office"),
            ("Procrastination is not a time management problem. It is an emotion regulation problem. You are not avoiding the work. You are avoiding the feeling.", "brain neurons abstract"),
            ("When you think about a hard task your amygdala reads it as a threat and floods you with stress. Your brain reaches for anything that makes it stop. Usually your phone.", "clock ticking time"),
            ("The relief from delay is real but it lasts about six seconds. Then the guilt returns, stronger, and now you are fighting two problems.", "person writing notebook plan"),
            ("Pick the task that scares you most. Set a timer for ten seconds. And start. Not finish. Start.", "sunrise morning window"),
            ("Do that for a week and the shame loop breaks. You were never broken. You were managing feelings instead of minutes.", "person working focused laptop"),
        ],
    },
    "time": {
        "title": "Why Time Disappears As You Get Older",
        "thumb": "IT'S REAL", "stock": "old clock time passing",
        "lines": [
            ("When you were five, one year was twenty percent of your whole life. Summer lasted forever. Now a year vanishes before you finish describing it.", "children playing outside summer"),
            ("The obvious answer is proportion. A year at fifty is two percent of your life. That is real, but it is only half of it.", "calendar pages turning"),
            ("Your brain does not record time evenly. It records change. New experiences get written down. Repeats get compressed into nothing.", "person routine commuting train"),
            ("Think about your last trip. The first day feels long because everything was new. The ride home feels like minutes, because your brain skipped it.", "first day new city travel"),
            ("Childhood was dense because everything was a first. Your brain had a reason to keep all of it.", "first day new city travel"),
            ("Time did not speed up. You just stopped giving it anything worth remembering. Do something unfamiliar this week.", "person hiking mountain new view"),
        ],
    },
    "sleep": {
        "title": "You Can't Sleep Off A Week Of Bad Sleep",
        "thumb": "NO CATCHING UP", "stock": "person sleeping bed dark",
        "lines": [
            ("You lost sleep all week. Saturday you sleep eleven hours and still feel wrecked. That is not in your head.", "person tired coffee morning"),
            ("Researchers call it sleep debt, and the body treats it like real debt. Partially repayable, never all at once.", "laboratory research science"),
            ("People restricted to six hours a night for two weeks performed like someone awake for forty eight hours. They simply did not know it.", "brain scan abstract science"),
            ("Their reaction time stayed impaired for days after normal sleep returned. The recovery lagged far behind the damage.", "person driving night road"),
            ("Weekend recovery brings its own problem. Sleeping in shifts your body clock later, making Sunday night harder and Monday worse.", "alarm clock early morning"),
            ("The only thing that works is consistency. Same bedtime, same wake time, seven days a week. Boring, and the only method that survived a study.", "peaceful bedroom morning light"),
        ],
    },
    "music": {
        "title": "Why You Remember Lyrics From 20 Years Ago",
        "thumb": "20 YEARS LATER", "stock": "vinyl record music",
        "lines": [
            ("You cannot remember what you said last Tuesday. But one bar of a song from twenty years ago brings every word back.", "vinyl record spinning music"),
            ("Music lights up more of the brain than almost anything else. Rhythm, melody, emotion, movement and language all fire at once.", "brain neurons firing abstract"),
            ("Because so many regions are involved, the memory is written in multiple places. It is like saving one file to five hard drives.", "person dancing headphones joy"),
            ("Most of your strongest musical memories come from ages ten to twenty five, when the brain is aggressively forming identity.", "teenager listening headphones"),
            ("Songs from that window get tagged with who you were. The music becomes a timestamp for a version of you that no longer exists.", "crowd concert hands raised"),
            ("When an old song hits and you feel something you cannot explain, that is not nostalgia for the music. It is recognition of yourself.", "person smiling listening music"),
        ],
    },
    "memory": {
        "title": "The Trick That Makes Your Memory Actually Work",
        "thumb": "STOP REREADING", "stock": "person studying books",
        "lines": [
            ("Rereading is the most popular study method on earth and one of the worst. Highlighting feels productive and teaches you almost nothing.", "person studying books"),
            ("Your brain confuses familiarity with knowledge. The page looks known, so you assume you know it. Try writing it from memory and you will find out.", "hand writing notes desk"),
            ("The fix is retrieval. Close the book and force the answer out of your head. The struggle to remember is what builds the pathway.", "thinker thinking window light"),
            ("Spacing beats cramming every time. Reviewing once a day for five days beats five hours in one night, with less total time.", "calendar planner desk"),
            ("Sleep is when the brain decides what to keep. All nighters do not just make you tired. They delete the work you just did.", "person sleeping study night"),
            ("Study less, test yourself more. The method that feels harder is the one that actually works.", "student success graduation light"),
        ],
    },
    "walking": {
        "title": "Walking Is The Most Underrated Thing You Can Do",
        "thumb": "20 MINUTES", "stock": "person walking path nature",
        "lines": [
            ("No equipment, no membership, no cost. And it is consistently one of the most studied interventions in medicine.", "person walking path nature"),
            ("Twenty minutes after a meal measurably lowers blood sugar. The muscles pull glucose from the blood without needing any insulin.", "healthy meal food table"),
            ("Walking also moves lymph fluid, which has no pump of its own and only circulates when your body moves.", "running exercise outdoors"),
            ("Creative output rises sharply during a walk. In one study, people produced sixty percent more ideas after walking than after sitting.", "creative person thinking outdoors"),
            ("It lowers resting heart rate, improves sleep depth, and the effect stacks with every extra thousand steps.", "heart rate health monitor"),
            ("The best exercise is the one you will actually do. For most people, that is the one that requires nothing at all.", "sunset walking silhouette"),
        ],
    },
    "attention": {
        "title": "Your Attention Span Is Being Trained Against You",
        "thumb": "8 SECONDS", "stock": "phone scrolling screen",
        "lines": [
            ("The average person switches tasks every few seconds. That is not a flaw in you. It is a response to an environment built to interrupt.", "phone scrolling screen"),
            ("Every notification is a small prediction error. Your brain drops what it is doing to check, because historically an unexpected sound mattered.", "notification phone alert"),
            ("The cost is not the interruption itself. It is the recovery time. Refocusing can take far longer than the interruption lasted.", "person frustrated computer work"),
            ("Multitasking is mostly rapid switching, and every switch leaves a residue of the previous task in your working memory.", "busy office multiple screens"),
            ("Deep work requires a boring environment. The people who focus best are not disciplined. They removed the choice.", "quiet room focused writing"),
            ("Try twenty five minutes with the phone in another room. Not silent. Another room. Distance beats willpower every time.", "calm desk minimal workspace"),
        ],
    },
    "money": {
        "title": "Why Earning More Rarely Makes You Feel Rich",
        "thumb": "LIFESTYLE CREEP", "stock": "money cash finance",
        "lines": [
            ("Your income doubles and your savings do not. This has a name, and almost everyone falls for it.", "money cash finance"),
            ("Lifestyle creep is the quiet upgrade of your baseline. A better apartment, a newer car, nicer restaurants. Each one feels reasonable alone.", "luxury apartment city"),
            ("Hedonic adaptation does the rest. Any improvement becomes normal within weeks, then starts feeling like the minimum.", "shopping bags retail store"),
            ("Meanwhile fixed costs rise faster than income, so the gap between earning more and keeping more never closes.", "bills paperwork desk"),
            ("The people who build wealth are usually not the highest earners. They are the ones whose lifestyle did not follow their income.", "piggy bank savings"),
            ("You cannot out-earn an unbounded lifestyle. The only lever that works is deciding, in advance, what enough looks like.", "peaceful simple life nature"),
        ],
    },
    "decision": {
        "title": "Your Brain Decides Before You Know It",
        "thumb": "7 SECONDS EARLY", "stock": "person thinking decision",
        "lines": [
            ("Neuroscientists can detect a decision forming seconds before you are aware of having made one. Your conscious self is often the last to know.", "person thinking decision"),
            ("That does not mean free will is fake. It means the work starts earlier than your awareness does.", "brain scan abstract science"),
            ("It also explains moments of doubt. The choice is already running when your mind catches up and questions it.", "conflicted person window light"),
            ("Under fatigue the automatic systems take over, which is why late night decisions tend to repeat old patterns instead of breaking them.", "tired person late night desk"),
            ("The practical fix is to make big decisions in the morning, when the deliberate system still has fuel.", "sunrise morning coffee thought"),
            ("You are not slower than your brain. You are simply notified after the fact.", "calm person looking horizon"),
        ],
    },
    "stress": {
        "title": "Stress Is Not The Problem. This Is.",
        "thumb": "IT'S NOT STRESS", "stock": "stressed person work",
        "lines": [
            ("Stress itself is not harmful. Your body was built for it. The damage comes from stress that never ends.", "stressed person work"),
            ("A short burst of pressure sharpens focus, boosts reaction time, and clears fog. That response saved lives for a hundred thousand years.", "athlete focused intensity"),
            ("Chronic stress keeps the same chemistry switched on, so recovery never happens. Cortisol stays high while the system waits for a resolution that never arrives.", "person overwhelmed paperwork"),
            ("The deciding factor is control. Stress with an endpoint is manageable. Stress with no visible end is what breaks people.", "hourglass endless sand"),
            ("You cannot always remove the pressure, but you can rebuild the ending. Small completed loops tell the brain the threat is over.", "checklist complete success"),
            ("Finish something small today. Not because it matters, but because your nervous system needs to see a finish line.", "sunset calm completion"),
        ],
    },
    "confidence": {
        "title": "Confidence Is A Skill, Not A Personality Trait",
        "thumb": "LEARNABLE", "stock": "confident person standing",
        "lines": [
            ("Confidence is treated like something you are born with. It is actually built the same way every other skill is built.", "confident person standing"),
            ("It does not come from repeating affirmations. It comes from evidence. Your brain believes what it has seen you survive.", "person climbing challenge"),
            ("Avoidance is what kills it. Every time you dodge a hard thing, you teach yourself that you cannot handle it.", "person hesitating door"),
            ("The correction is small deliberate exposure. Not the scariest thing. The next thing.", "person taking first step"),
            ("Tracking matters. Write down what you handled this week, because memory filters out anything that went fine.", "journal writing notebook"),
            ("You do not need to feel ready first. Action produces the evidence, and the evidence produces the feeling.", "sunrise ready action"),
        ],
    },
    "habits": {
        "title": "Why Your New Habit Dies In Three Days",
        "thumb": "DAY 3", "stock": "routine morning habit",
        "lines": [
            ("Most habits collapse in the first week, and the reason is almost never motivation.", "routine morning habit"),
            ("The mistake is starting at your best. You begin with an hour a day, feel great, then life gets busy and the gap turns into guilt.", "intense workout gym"),
            ("Habit research points to the opposite. Shrink the action until it is almost absurd, then hold it there.", "small plant growing"),
            ("Two minutes a day beats an hour you abandon. The goal in week one is repetition, not results.", "calendar mark routine"),
            ("Anchor the new habit to something you already do without thinking. After coffee. After brushing your teeth.", "morning coffee ritual"),
            ("Motivation follows consistency, not the other way around. Do it badly for two weeks and the identity starts to form.", "person steady daily routine"),
        ],
    },
    "night": {
        "title": "What Happens To Your Brain At 3 A.M.",
        "thumb": "3 A.M.", "stock": "dark room night awake",
        "lines": [
            ("Thoughts at three in the morning feel enormous. They are also almost always wrong, and there is a reason for that.", "dark room night awake"),
            ("At night the brain's rational control centre goes quiet while the emotional centre stays active. You are thinking with the volume up and the brakes off.", "brain abstract night glow"),
            ("Cortisol normally reaches its floor around midnight and climbs before dawn. Wake too early and you catch it mid-rise, which feels like anxiety.", "clock night dark bedroom"),
            ("Your perspective narrows too. Without daytime distraction, a single worry becomes the only thing in the frame.", "isolated person dark window"),
            ("The rule is simple. Never solve anything after midnight. Write it down, decide tomorrow at nine.", "writing notebook night lamp"),
            ("Almost nothing you conclude at three in the morning survives the daylight. Sleep is not avoidance. It is better judgement.", "sunrise calm morning"),
        ],
    },
    "lie": {
        "title": "Your Brain Lies To You About This Every Day",
        "thumb": "YOUR BRAIN LIES", "stock": "mirror reflection person",
        "lines": [
            ("You are not seeing the world as it is. You are seeing a prediction that your brain edits in real time.", "mirror reflection person"),
            ("Most of what reaches your consciousness was already filled in before you became aware of it, which is why change blindness is so easy to trigger.", "optical illusion abstract"),
            ("Memory works the same way. Recalling an event does not replay it. It rebuilds it, using whatever you believe now.", "old photographs memory"),
            ("That means every time you remember something, you quietly edit the past to fit the present.", "rewinding time abstract"),
            ("Your brain also predicts how things will feel, and those predictions are usually wrong. People overestimate both how bad failure will hurt and how good success will feel.", "expectation waiting hands"),
            ("Knowing this is useful. When your mind tells you a story about yourself, treat it as a draft, not a fact.", "person calm clear sky"),
        ],
    },
    "cold": {
        "title": "What Cold Water Does To Your Body In 30 Seconds",
        "thumb": "30 SECONDS", "stock": "cold water splash",
        "lines": [
            ("The first reaction is not adaptation. It is panic. Cold water triggers a gasp reflex you cannot consciously override.", "cold water splash"),
            ("That gasp can pull water into your lungs, which is why open water is dangerous even for strong swimmers.", "swimmer open water"),
            ("Within seconds your blood vessels clamp shut and blood pressure jumps sharply. This is why cold exposure is risky for untrained hearts.", "heart rate health monitor"),
            ("Then adrenaline and norepinephrine surge, sometimes several times their baseline, and that is the alertness people report afterwards.", "energetic person morning wake"),
            ("Regular exposure appears to raise baseline norepinephrine and improve mood, though most studies remain small.", "laboratory research science"),
            ("Start with cold water at the end of a normal shower. The controlled dose is where the benefit lives.", "shower water calm"),
        ],
    },
    "focus": {
        "title": "The 90 Minute Rule That Explains Your Work Day",
        "thumb": "90 MINUTES", "stock": "focused work desk",
        "lines": [
            ("Your brain does not work in straight lines. It moves in roughly ninety minute waves, and fighting them is why some days feel impossible.", "focused work desk"),
            ("During each wave focus climbs, holds, then drops. The drop is not laziness. It is a biological boundary.", "wave ocean rhythm"),
            ("Push through it and you get the worst version of your work: slow, error prone, and exhausting.", "frustrated tired work"),
            ("The fix is to plan in blocks that match the wave, then stop before the wall instead of after it.", "planner schedule blocks"),
            ("Rest in that window needs to be real. Scrolling is not recovery, because it keeps the same circuits engaged.", "person walking break outside"),
            ("Work with the wave instead of against it and you will finish more in six hours than you used to in ten.", "calm productive evening desk"),
        ],
    },
    "brain": {
        "title": "Your Brain Deletes Most Of What You Experience",
        "thumb": "99% DELETED", "stock": "brain neurons abstract",
        "lines": [
            ("Every second your senses deliver far more information than you could ever process, so almost all of it is discarded before you notice.", "brain neurons abstract"),
            ("What survives is what your brain decided mattered, and that decision is based on old priorities rather than present ones.", "eye sight vision detail"),
            ("This is why you can walk the same route for years and not remember a single detail of it. Nothing triggered a reason to keep it.", "person walking street routine"),
            ("It also explains why traumatic memories are so sharp and so incomplete. The recording system keeps the emotion and drops the context.", "shadow memory dark silhouette"),
            ("You can bias the system deliberately. Novelty, emotion and attention all mark a moment as worth keeping.", "person experiencing something new"),
            ("A day with nothing new in it will be deleted almost entirely. That is not a memory flaw. That is the design.", "blank calendar empty page"),
        ],
    },
    "phone": {
        "title": "The First 10 Minutes After Waking Decide Your Day",
        "thumb": "10 MINUTES", "stock": "morning waking phone bed",
        "lines": [
            ("Most people reach for the phone before their feet touch the floor, and it quietly shapes everything that follows.", "morning waking phone bed"),
            ("The moment you wake, your brain is moving from sleep into alertness. That transition is unusually open to influence.", "sunrise morning light window"),
            ("Checking messages first hands your attention to other people's agendas before you have formed your own.", "notifications phone screen"),
            ("Cortisol is already rising naturally at this point, which is the body's built in alert system. Sunlight amplifies it correctly.", "morning sunlight window"),
            ("Ten minutes without input changes the tone. Light, water, and a single defined intention are enough.", "glass of water morning"),
            ("You do not need a perfect routine. You need to stop borrowing everyone else's priorities before you have set your own.", "calm morning coffee planning"),
        ],
    },
    "money2": {
        "title": "The Math That Quietly Keeps You Poor",
        "thumb": "THE MATH", "stock": "calculator money bills",
        "lines": [
            ("It is rarely one large mistake. It is a series of small conversions where you trade lasting value for temporary comfort.", "calculator money bills"),
            ("Subscriptions are the clearest example. A few dollars monthly is designed to be too small for your brain to register as a loss.", "subscription phone payment"),
            ("Fees work the same way. Interest compounds forward for the lender and against you, on the exact same schedule.", "bank finance building"),
            ("Then there is the convenience trade. Paying to save ten minutes feels trivial until you add up a year of it.", "delivery convenience city"),
            ("The useful question is not what something costs. It is what it costs per month of your actual life.", "thinking planning desk finances"),
            ("Most people do not need to earn dramatically more. They need to stop paying for things they have stopped noticing.", "simple budget notebook"),
        ],
    },
    "social": {
        "title": "Why Being Around People Changes How You Think",
        "thumb": "YOU ABSORB IT", "stock": "friends group people",
        "lines": [
            ("You do not have an independent personality that other people merely observe. Their habits leak into yours constantly.", "friends group people"),
            ("Studies on obesity, smoking and happiness all show the same pattern. Your risk shifts based on what the people around you do.", "crowd people city life"),
            ("Part of it is practical. You adopt the same standards, so what felt extreme starts to look normal.", "office coworkers behaviour"),
            ("Part of it is deeper. Your brain runs a background comparison whether or not you ask it to.", "person watching others window"),
            ("This cuts both ways. A single disciplined person in a group measurably raises the standard for everyone in it.", "team working together"),
            ("You cannot choose every influence, but you can choose which room you spend most of your time in.", "calm space chosen environment"),
        ],
    },
    "rest": {
        "title": "Rest Is Not The Same As Doing Nothing",
        "thumb": "NOT THE SAME", "stock": "person resting calm nature",
        "lines": [
            ("Lying down with a phone is not rest. Your brain remains in a low grade alert state the entire time.", "person resting couch phone"),
            ("True recovery has a signature. It lowers arousal, and screens generally raise it, even when the content feels relaxing.", "calm nature quiet field"),
            ("This is why scrolling for two hours can leave you more tired than you started, while twenty minutes outside does the opposite.", "person walking park trees"),
            ("Attention also needs different modes. Focused attention and wandering attention use different networks, and both need time.", "person daydreaming sky"),
            ("Boredom itself has a function. It is the state where the brain consolidates and plans without being fed new input.", "empty quiet room stillness"),
            ("Schedule idleness the way you would schedule work. If every gap is filled, nothing ever gets processed.", "peaceful evening calm"),
        ],
    },
    "learning": {
        "title": "You're Learning It Wrong (According To Science)",
        "thumb": "WRONG METHOD", "stock": "student learning books",
        "lines": [
            ("Most study techniques feel effective and fail badly. Fluency while reading is not the same as knowing the material.", "student learning books"),
            ("Highlighting is the classic case. It produces a page that looks reviewed while leaving the knowledge exactly where it was.", "highlighter notes study"),
            ("The reason is that recognition is easy and recall is hard. Your brain confuses the two because they arrive with the same feeling.", "thinking person reading"),
            ("Retrieval practice reverses it. Testing yourself forces the material out of memory, which is what actually strengthens it.", "writing test exam desk"),
            ("Spacing makes it stronger still. Interleaving problem types beats doing blocks of identical questions.", "scattered notes study desk"),
            ("If your method never feels difficult, it is probably not working. Struggle is the signal, not the warning.", "person working through problem"),
        ],
    },
    "food": {
        "title": "Why You're Still Hungry After Eating",
        "thumb": "NOT FULL", "stock": "plate food meal",
        "lines": [
            ("You finished the plate and twenty minutes later you are already looking for something else. That delay is the whole story.", "plate food meal"),
            ("Fullness signals take time to reach your brain. Hormones like CCK and leptin rise gradually, so the message always trails the meal.", "digestion body science abstract"),
            ("Eating quickly means you override the signal before it ever arrives, which is why speed is one of the strongest predictors of overeating.", "fast food eating rushed"),
            ("Protein and fibre trigger those signals far more effectively than refined carbs, which leave the same calorie count feeling hollow.", "protein vegetables healthy food"),
            ("Hydration matters too. Thirst is frequently misread as hunger, especially in the afternoon.", "glass of water thirst"),
            ("Eat slower, eat protein first, and drink water before deciding you are still hungry.", "calm mindful eating table"),
        ],
    },
    "age": {
        "title": "What Actually Changes After 30 (It's Not What You Think)",
        "thumb": "AFTER 30", "stock": "person portrait age",
        "lines": [
            ("The popular story is that everything declines sharply after thirty. Most of that is marketing, not physiology.", "person portrait age"),
            ("Strength and cardiovascular capacity decline only if they are untrained. The measured drop in active people is remarkably small.", "active person exercise gym"),
            ("What does change is recovery. It takes longer between sessions, which people misread as a loss of ability.", "person stretching recovery"),
            ("Metabolic rate stays nearly flat into your sixties. The real change is a gradual drop in spontaneous movement.", "person walking stairs daily"),
            ("Bone density and muscle mass respond to load. Both can be maintained for decades with consistent resistance training.", "resistance training weights"),
            ("The body does not switch off at thirty. It just starts demanding that you be deliberate instead of coasting.", "confident healthy person outdoors"),
        ],
    },
    "lie2": {
        "title": "The Truth About Willpower Nobody Tells You",
        "thumb": "NOT WILLPOWER", "stock": "person disciplined focused",
        "lines": [
            ("Willpower is treated as a character trait. Research treats it as a resource, and resources run out.", "person disciplined focused"),
            ("Across a day, self control measurably declines. The evening version of you is negotiating with less fuel than the morning one.", "evening tired person desk"),
            ("This is why decisions made at night so often contradict decisions made at breakfast.", "night dark window thinking"),
            ("Environment beats effort every time. People who appear disciplined usually have fewer temptations within reach.", "minimal clean workspace"),
            ("That is the entire trick. Make the good option the default and the bad option require steps.", "organized room clear space"),
            ("You are not weak. You are fighting a system that was never designed for constant resistance.", "calm person at peace"),
        ],
    },
    "sound": {
        "title": "Why Certain Sounds Make Your Skin Crawl",
        "thumb": "CHILLS", "stock": "sound waves audio",
        "lines": [
            ("Some sounds hit you physically before you have even identified them. That reaction is older than language.", "sound waves audio"),
            ("The auditory system connects directly to the amygdala, so a threatening sound can trigger a response before the cortex processes what it was.", "ear listening sound"),
            ("Frequencies near a scream are especially potent because the brain is tuned to that specific band.", "alarm warning red abstract"),
            ("The frisson you get from music is a different mechanism. Unexpected chords and sudden dynamic shifts produce a measurable dopamine release.", "music concert sound stage"),
            ("Rhythm does the rest. Synchronized beats increase pain tolerance and produce a sense of shared attention even with strangers.", "drum rhythm percussion"),
            ("You are not being dramatic about the noise. Your hearing system is simply faster than your reasoning.", "person headphones listening"),
        ],
    },
}


def make_script(slug: str, fact: dict) -> dict:
    scenes = [{"stock": stock, "narration": line} for line, stock in fact["lines"]]
    title = fact["title"]
    return {
        "slug": slug,
        "title": title,
        "orientation": "landscape",
        "voice": VOICE,
        "thumb_text": fact["thumb"],
        "thumb_stock": fact["stock"],
        "description": (
            f"{fact['lines'][0][0]}\n\n"
            "Made with AI assistance.\n\n"
            "#facts #science #psychology #education #learn"
        ),
        "tags": ["facts", "science", "psychology", "education", "learn",
                 "documentary", "brain", "interesting facts"],
        "scenes": scenes,
    }


def published_titles() -> set[str]:
    """Titles already on the channel - never queue those topics again."""
    manifest = HERE.parent / "uploaded_manifest.json"
    titles: set[str] = set()
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for entry in data.get("uploaded", {}).values():
                t = (entry.get("title") or "").strip().lower()
                if t:
                    titles.add(t)
        except Exception:  # noqa: BLE001
            pass
    # also treat any rendered-and-queued topic as taken
    for p in CONTENT.glob("*.json"):
        try:
            t = (json.loads(p.read_text(encoding="utf-8")).get("title") or "").strip().lower()
            if t:
                titles.add(t)
        except Exception:  # noqa: BLE001
            pass
    return titles


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    taken = published_titles()
    existing = {p.stem for p in CONTENT.glob("*.json")}
    available = {
        k: v for k, v in FACTS.items()
        if k not in existing and v["title"].strip().lower() not in taken
    }
    if not available:
        print("every topic in the bank is already queued or published")
        return 0

    rng = random.Random(args.seed)
    picks = rng.sample(sorted(available), min(args.count, len(available)))

    for slug in picks:
        dest = CONTENT / f"{slug}.json"
        dest.write_text(json.dumps(make_script(slug, FACTS[slug]), indent=2,
                                   ensure_ascii=False), encoding="utf-8")
        print(f"  queued {slug:24s} | {FACTS[slug]['title'][:50]}")

    print(f"\nadded {len(picks)}; {args.count - len(picks)} requested but "
          f"topic bank exhausted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
