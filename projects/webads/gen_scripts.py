# -*- coding: utf-8 -*-
"""Generate the 10,000-script ad bank for the web-design project.

    python gen_scripts.py            # writes bank.jsonl (10000 lines)
    python gen_scripts.py 5000       # smaller bank

One line = one complete <1 minute reel script, same schema as the short
scripts of the other channels (scenes: 7, portrait, ~70 words = ~30 s).
Templates are assembled combinatorially from the pools below - hooks,
pains, services, proofs, offers and CTAs - so every episode reads
different while every claim stays on-message: teams of specialists,
e-commerce and any site, highest quality, strong SEO, from $1,000.
Deterministic: same seed -> same bank, so re-runs never fork the order.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE / "bank.jsonl"
COUNT = 10_000
SEED = 67

VOICE = "en-US-AvaMultilingualNeural"

HOOKS = [
    "Your website is losing you customers every single hour.",
    "This website paid for itself in eleven days.",
    "If your site takes three seconds to load, half your buyers are gone.",
    "Your competitor's site just sold to YOUR customer.",
    "Google did not show your site today. Here is why.",
    "Pretty websites do not sell. Websites like this one sell.",
    "Seventy-five percent of people judge your business by one thing: your website.",
    "Stop losing sales to a slow website.",
    "Your website should be your best salesperson. Yours is on vacation.",
    "We rebuilt this online store in nine days. Sales went up two-point-four times.",
    "If you cannot find your own site on Google, neither can your customers.",
    "A website is not decoration. It is infrastructure.",
    "Your homepage has five seconds to earn trust. Most fail in two.",
    "Eighty percent cart abandonment? The checkout is the problem, not the product.",
    "Nobody buys from a site that looks like it was built in two thousand nine.",
    "Every minute without a proper site, a rival takes your customer.",
    "One line of code is costing you sales tonight.",
    "Your customers are searching at midnight. Is anyone answering?",
    "That broken contact form is a broken revenue stream.",
    "A mobile visitor just gave up on your site. Watch.",
    "Your logo is fine. Your website is what is failing you.",
    "Your customers decided about you in five seconds. Guess what they saw.",
    "You are paying rent for a shop nobody can find. The internet is free.",
    "Your site looks okay. That is exactly the problem.",
    "This client stopped chasing customers the day his site went live.",
    "Half of your traffic is mobile. Half your site ignores that.",
    "Your website is your hardest-working employee. Yours never shows up.",
    "That stock photo header just told everyone you do not care.",
    "People scrolled past you today. Here is the fix.",
    "Your business is good. Your website is hiding it.",
    "The fastest way to lose a sale: make them wait for your page.",
    "Your contact page is where your next client went to disappear.",
    "You built the business. The website should be closing for you.",
    "Ten seconds is an eternity online. Your site takes eight to load.",
    "Your customers compare you side by side, right now.",
    "A redesign is not vanity. It is revenue.",
    "Someone searched for your service tonight. They found someone else.",
    "Your bounce rate is a confession.",
    "The sale did not fail. The page load did.",
    "If your site is not selling, you do not have a website. You have a brochure.",
    "That landing page has one job. It is not doing it.",
    "Your site loads slow, looks dated, and ranks nowhere. Three problems, one fix.",
    "Every ad you run points to a page that leaks customers.",
    "Your website is open twenty-four seven. Make it work for it.",
    "Your next thousand customers are searching right now.",
    "You would not open a store with a broken front door. Your site has one.",
    "Your traffic is fine. Your conversion is the crime scene.",
    "This client's new site covers its own cost every month.",
    "Your homepage says everything wrong in five seconds flat.",
    "Google ranks speed first. Your site is parked in the slow lane.",
]

PAINS = [
    "Slow pages bleed money: every extra second cuts sales by seven percent.",
    "A site that is not mobile-friendly loses six in ten buyers halfway.",
    "Weak SEO means free traffic you never receive.",
    "An outdated design kills trust before you say one word.",
    "Broken checkout, hidden shipping costs, confusing menus: the three biggest cart killers.",
    "No analytics means decisions made on feelings instead of data.",
    "A browser security warning is an instant exit for every visitor.",
    "Nobody fills a form that asks too much and promises nothing.",
    "A dead contact page turns warm leads into silence.",
    "If your site looks generic, your prices get compared to the cheapest option.",
    "Boring copy makes good products look bad.",
    "Visitors scan. Walls of text get skipped, not read.",
    "A hard-to-find phone number is a lost call, lost today.",
    "Your competitors update weekly. Your site has not changed in years.",
    "Desktop-only layouts break the moment a customer opens you on a phone.",
    "Every broken link is a door that leads nowhere.",
    "A slow checkout doubles the chance the cart gets abandoned.",
    "No clear call to action means no action at all.",
    "Blurry photos and unstyled pages whisper: amateur hour.",
    "Search engines cannot rank pages they cannot understand.",
    "No mobile payment? Half the traffic cannot buy anyway.",
    "An unstructured site buries your best pages under junk.",
    "Pop-ups and clutter push buyers out the door.",
    "Old content and dead blog posts drag your whole ranking down.",
    "A site without SSL gets flagged. Visitors run.",
    "Unclear pricing makes buyers assume the worst: overpriced.",
    "If loading spins past three seconds, the back button wins.",
    "No reviews, no proof, no trust: strangers do not gamble.",
    "A website that ignores accessibility excludes paying customers.",
    "Inconsistent branding across pages looks like a scam, not a store.",
    "A confusing menu hides the one page that makes you money.",
    "Your homepage buries the offer below the fold. Nobody digs.",
    "No follow-up capture means ninety-eight percent of visitors leave forever.",
    "Generic templates make you invisible in a crowded market.",
    "Hidden costs at the last step are the number-one cart killer.",
    "A site that cannot grow with you costs you double later.",
    "No social proof means every visitor takes a blind leap.",
    "Bad typography strains eyes. Strained readers leave.",
    "Your site looks the same on every device, and wrong on most of them.",
    "Search engines skip sites with no structure and no sitemap.",
    "Customers bounce when the menu makes them think.",
    "A website without a funnel is a car without a steering wheel.",
    "Every day with a weak site, your competitor's strong one eats your share.",
    "Nothing on the page tells the visitor what to do next.",
]

AGITATES = [
    "And it gets worse: they never come back.",
    "That is a customer you paid to attract, then lost for free.",
    "Multiply that by every hour your site stays slow.",
    "And every one of them tells nobody. They just leave.",
    "The worst part: you will never see the sale you missed.",
    "Meanwhile your competitor's phone is ringing.",
    "That lost visitor was ready to pay today.",
    "And tomorrow the same thing happens again.",
    "You already paid for the traffic. Now it walks out.",
    "You feel it in the numbers at the end of the month.",
    "And on mobile, where most of your buyers actually are, it is worse.",
    "Every week you wait, the repair bill gets bigger.",
    "Meanwhile your ad budget keeps buying clicks that vanish.",
    "Your best product is invisible behind your worst page.",
    "You are not losing to better products. You are losing to better pages.",
    "Google already sent you the visitor. Your site failed the handshake.",
    "And the next customer they find is one click away.",
    "You are invisible where it matters: the search results page.",
    "That friction compounds, day after day, sale after sale.",
    "The buyer felt the doubt. Doubt kills carts.",
    "And the worst reviews come from that exact confusion.",
    "You never hear the complaint. You only see the missing revenue.",
    "Your support inbox fills with questions your site should have answered.",
    "Every redesign delay is a quiet monthly loss.",
    "The traffic is there. The site is bleeding it out.",
    "And once a visitor leaves, the ad spend leaves with them.",
    "That is money on the floor, every single day.",
    "Your rivals are A/B testing while you are apologizing for your site.",
    "The market does not wait for your launch date.",
    "And your best clients judge you by your worst page.",
]

SERVICES = [
    "We design, build and SEO-tune online stores that actually convert.",
    "Business sites with clean architecture and real SEO foundations.",
    "Booking systems for clinics, salons and restaurants.",
    "Landing pages engineered for one action: the sale.",
    "Portfolios, blogs, membership sites, dashboards.",
    "Speed work: green Core Web Vitals, loads under two seconds.",
    "Full rebuilds and migrations from any platform.",
    "Rescues of half-finished projects, done right.",
    "A dedicated team: designer, developer, SEO specialist, one project.",
    "Mobile-first layouts tested across real devices.",
    "Payment gateways wired in and tested end to end.",
    "Product catalogs structured so search engines actually understand them.",
    "Conversion-first copy written into the layout, not bolted on.",
    "Analytics and Search Console connected from day one.",
    "Security hardening, backups and SSL as standard.",
    "Custom admin panels so you update content without calling anyone.",
    "Schema markup and sitemaps from the first commit.",
    "Speed optimization that shaves seconds, not milliseconds.",
    "Multi-language sites ready for international buyers.",
    "Email capture and follow-up funnels built into every page.",
    "Design systems that keep every new page on brand.",
    "Ecommerce SEO: categories, filters and product pages that rank.",
    "Core Web Vitals tuning, image compression, lazy loading, caching.",
    "Accessibility passes so nobody is excluded from buying.",
    "Integrations: CRM, WhatsApp, invoices, shipping, inventory.",
    "Landing pages for ads that finally match the click they buy.",
    "Content structure: headings, internal links, clean URLs.",
    "Hosting setup and handover, with training for your team.",
    "Maintenance plans so the site never rots again.",
    "A/B testing of headlines and layouts until the numbers move.",
    "Store launches with payment, shipping and tracking already wired.",
    "Site audits today, fixes this week, results this month.",
    "One team, one project, zero finger-pointing between agencies.",
    "A site that loads fast on a bad connection, not just on wifi.",
    "Everything scoped, priced and delivered: no surprises.",
]

PROOFS = [
    "Handover includes training, documentation and thirty days of support.",
    "Tested on forty devices and three connection speeds before launch.",
    "SEO from the first commit, not bolted on later.",
    "No template soup. No plugin graveyard. Clean code that lasts.",
    "Every page is measured: load time, conversions, search visibility.",
    "We fix the three killers first: speed, mobile, checkout.",
    "Our stores load under two seconds, even on mobile data.",
    "We do not disappear after launch. Thirty days of support, included.",
    "You own everything: the code, the domain, the accounts.",
    "The site is yours forever. No rent, no lock-in.",
    "Analytics wired in, so every decision is backed by numbers.",
    "Every checkout is tested with real payments before going live.",
    "We document everything, so your team is never stuck.",
    "One point of contact. No agency telephone game.",
    "We ship on the date we promised, or we explain why, early.",
    "Real devices, not just screenshots: iPhone, Android, tablet, laptop.",
    "Structure search engines love: headings, schema, sitemaps.",
    "We speak plainly. No jargon, no smoke, no invoices you cannot read.",
    "Speed is a feature: we measure every second and cut the waste.",
    "The redesign pays for itself: most clients see it within months.",
    "Every project gets a performance budget we actually respect.",
    "Your admins get training videos, not a two-page PDF.",
    "Security scans and backups are wired in from day one.",
    "We build funnels, not just pages: every screen leads somewhere.",
    "Mobile-first, because that is where your buyers are.",
    "We remove the friction: fewer fields, clearer buttons, faster carts.",
    "Proof is in the metrics: traffic, conversions, revenue, in one dashboard.",
    "Clean handover: your next developer will thank us.",
    "Nothing hidden: fixed scope, fixed price, fixed date.",
    "The site keeps selling while you sleep. That is the whole point.",
    "We obsess over the last ten percent most agencies skip.",
    "Every page answers one question: what should the visitor do now?",
    "Quality you can inspect: source code included at handover.",
    "We benchmark your competitors and beat their load times.",
    "Three rounds of revisions are included, not extra.",
    "Your store, your brand, your data, under your control.",
    "We build for the next five years, not just this launch.",
    "From first call to launch: clear steps, clear dates, clear price.",
    "Support that answers in hours, not business days.",
    "The boring parts done right: redirects, metadata, canonicals.",
]

OFFERS = [
    "Projects start from one thousand dollars. Fixed scope, fixed price.",
    "From one thousand dollars: design, build, SEO setup, launch, training.",
    "Store packages from one thousand dollars, payment gateway included.",
    "One payment. One team. One website that works while you sleep.",
    "Cheaper than a month of rent, and it sells for years.",
    "Start at one thousand dollars. Scale whenever you are ready.",
    "A complete business site from one thousand dollars. No hidden fees.",
    "Your first month of support comes free with every build.",
    "Get a free audit before you pay a single dollar.",
    "Fifteen-minute call today, fixed quote tomorrow.",
    "We scope it, price it, build it: from one thousand dollars.",
    "Launch-ready from one thousand dollars, including training.",
    "One thousand dollars gets you online properly. Not almost. Properly.",
    "Compare that to one lost client per month: it pays back instantly.",
    "Split it into two payments if that is easier. Ask.",
    "Every package includes SEO, speed and mobile optimization.",
    "The quote you get is the invoice you pay.",
    "Small budget? We phase it: launch the money pages first.",
    "Free strategy call, then a fixed price. No hourly surprises.",
    "From one thousand dollars, your store takes orders while you sleep.",
    "A serious website should not cost a fortune. Ours start at one thousand.",
    "One thousand dollars. One team. Ninety days to live.",
    "No retainers required. Build it, own it, run it.",
    "We quote the whole project up front, from one thousand dollars.",
    "Your rebuild costs less than one month of missed sales.",
    "Fast-track option: live in fourteen days, from one thousand dollars.",
    "First draft in forty-eight hours. You approve before we build.",
    "Free mockup with every serious inquiry. See it before you spend.",
    "Price locked at the quote. Scope creep is our problem, not yours.",
    "Try us with a landing page first, from one thousand dollars.",
]

CTAS = [
    "DM the word SITE and we audit yours for free.",
    "Link in bio: claim your one-thousand-dollar project plan today.",
    "Comment STORE and we send three references in your niche.",
    "Send us your URL. We reply with the three things costing you customers.",
    "Book a fifteen-minute call. No pressure, no jargon.",
    "Follow for daily site fixes, then DM us your link.",
    "Message us before midnight: free audit for the first ten replies.",
    "Tap the link and get your fixed quote in twenty-four hours.",
    "Save this reel, then send it to the person who runs your site.",
    "Comment YES and we will DM the full checklist.",
    "Your free audit is one message away. Use it.",
    "We answer every DM. Try us: send your URL.",
    "Ready this month? Say READY and we start the scope today.",
    "Click bio, pick a slot, get your plan. That simple.",
    "Tell us your industry and we send a mockup idea. Free.",
    "Last step: one message. SITE. That is the whole form.",
    "Your competitor already messaged us. Do not let them be the only one.",
    "The audit is free. The embarrassment of your bounce rate is optional.",
    "Share this with your business partner. Then decide together.",
    "DM SITE tonight, wake up to your audit.",
    "One keyword: SITE. One free report. Zero obligation.",
    "We build from one thousand dollars. Your first move is one message.",
    "Stop scrolling. Start selling. Link in bio.",
    "Ten free audits left this month. Claim yours now.",
    "Message the word LAUNCH and get your delivery date today.",
    "Comment your industry: restaurant, clinic, store. We reply with ideas.",
    "Your site can be live in two weeks. Say GO and we begin.",
    "Watch the reel, send the URL, get the fixes. Free.",
    "Follow, then DM: we will audit your homepage live on a call.",
    "The link in bio is the shortest distance to a site that sells.",
]

NICHES = [
    ("online stores", "online store shopping cart"),
    ("restaurants", "restaurant food plating"),
    ("cafes", "coffee shop barista"),
    ("clinics", "medical clinic reception"),
    ("dental clinics", "dentist chair tools"),
    ("gyms", "gym workout training"),
    ("salons", "hair salon styling"),
    ("real estate", "real estate house keys"),
    ("car dealers", "car dealership showroom"),
    ("law firms", "law office desk books"),
    ("agencies", "creative agency team"),
    ("photographers", "photographer camera studio"),
    ("coaches", "speaker stage coaching"),
    ("schools", "classroom students learning"),
    ("online courses", "laptop online course"),
    ("travel agencies", "airport traveler suitcase"),
    ("hotels", "hotel lobby interior"),
    ("construction", "construction site crane"),
    ("architecture", "architect blueprint drawing"),
    ("interior design", "interior design living room"),
    ("jewelry shops", "jewelry rings display"),
    ("fashion boutiques", "clothing rack boutique"),
    ("electronics shops", "electronics store gadgets"),
    ("pet stores", "pet shop puppy"),
    ("bakeries", "bakery fresh bread"),
    ("pizzerias", "pizza oven fresh"),
    ("barbershops", "barber haircut shop"),
    ("spas", "spa candles massage"),
    ("yoga studios", "yoga class sunrise"),
    ("music schools", "piano lesson music"),
    ("auto repair", "mechanic car repair"),
    ("logistics", "cargo truck delivery"),
    ("shipping stores", "parcel boxes warehouse"),
    ("insurance agents", "insurance desk handshake"),
    ("accountants", "accountant calculator desk"),
    ("financial advisors", "financial chart growth"),
    ("startups", "startup team meeting"),
    ("saas products", "dashboard software screen"),
    ("mobile apps", "mobile app phone hand"),
    ("nonprofits", "volunteers charity team"),
    ("churches", "community hall gathering"),
    ("wedding planners", "wedding table decoration"),
    ("event venues", "event hall lights"),
    ("farmers markets", "fresh market vegetables"),
]

TEMPLATES = ["mockup", "question", "beforeafter", "price", "stat", "checklist"]


def pick(rng: random.Random, pool):
    return rng.choice(pool)


def build(rng: random.Random, n: int, total: int) -> dict:
    hook = pick(rng, HOOKS)
    pain = pick(rng, PAINS)
    agitate = pick(rng, AGITATES)
    svc_i = pick(rng, range(len(SERVICES)))
    service = SERVICES[svc_i]
    proof = pick(rng, PROOFS)
    offer = pick(rng, OFFERS)
    cta = pick(rng, CTAS)
    niche, stock = NICHES[rng.randrange(len(NICHES))]

    slug = f"webad_ep{n:05d}_{rng.randrange(16):x}"
    scene_texts = [hook, pain, agitate, service, proof, offer, cta]
    scenes = []
    for i, text in enumerate(scene_texts):
        s_stock = stock if i in (0, 3) else rng.choice([
            "laptop code screen", "web design mockup", "designer desk workspace",
            "analytics graph growth", "team working office", "smartphone mobile app",
            "online shopping laptop", "typing keyboard closeup", "office city window",
            "startup whiteboard planning",
        ])
        scenes.append({"stock": s_stock, "narration": text})

    title = f"{hook.rstrip('.')} #Shorts"
    if len(title) > 95:
        title = title[:92].rstrip() + "… #Shorts"

    desc = (f"{hook} {pain}\n\n"
            f"We build {niche} websites and every kind of site: highest quality, "
            f"strong SEO, projects from $1,000.\n\n{cta}\n\n"
            "#webdesign #website #seo #ecommerce #SmallBusiness #OnlineStore #Shorts")

    return {
        "slug": slug,
        "topic": f"Web Design Ad {n}",
        "title": title,
        "orientation": "portrait",
        "voice": VOICE,
        "template": TEMPLATES[n % len(TEMPLATES)],
        "thumb_text": (hook[:22].rsplit(" ", 1)[0] + "!").upper(),
        "thumb_stock": stock,
        "description": desc,
        "tags": ["web design", "website", "seo", "ecommerce", "small business",
                 "online store", "web development", "#Shorts"],
        "scenes": scenes,
        "_words": sum(len(s["narration"].split()) for s in scenes),
    }


def main(argv) -> int:
    total = int(argv[1]) if len(argv) > 1 else COUNT
    rng = random.Random(SEED)
    seen = set()
    lines = []
    n = 0
    while len(lines) < total:
        n += 1
        s = build(rng, n, total)
        key = tuple(sc["narration"][:40] for sc in s["scenes"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(json.dumps(s, ensure_ascii=False))
    with open(BANK, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"bank: {len(lines)} scripts -> {BANK.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
