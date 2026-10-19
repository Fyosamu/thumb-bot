# -*- coding: utf-8 -*-
"""Generate the multichan registry: 100 personal-development channels.

25 categories x 4 channels each. Every entry carries its own English
name, Persian aparat search queries (the robot discovers sources per
category), description, palette, edge-tts voice and state paths suffix.
Deterministic - rerunning produces byte-identical output.

    python gen_channels.py
"""
from __future__ import annotations

import colorsys
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "channels.json"

# (category slug, EN category, tagline, 3 Persian queries, 4 channel names)
CATS: list[tuple[str, str, str, list[str], list[str]]] = [
    ("habits", "Habits & Discipline", "Small habits, massive change",
     ["عادت‌های موفقیت", "انضباط شخصی", "تغییر عادت"],
     ["Keystone Habits", "Habit Forge", "Daily Discipline", "Routine Lab"]),
    ("goals", "Goals & Vision", "Aim with intent, arrive with proof",
     ["هدفگذاری", "برنامه ریزی برای موفقیت", "رسیدن به هدف"],
     ["North Star Goals", "Goal Craft", "Aim Higher", "Vision Daily"]),
    ("psychology", "Psychology Insights", "Why we do what we do",
     ["روانشناسی شخصیت", "روانشناسی رفتار", "تله‌های فکری"],
     ["Mind Decode", "Psychology Daily", "Why We Do That", "Cognitive Corner"]),
    ("mindfulness", "Mindfulness & Meditation", "One breath at a time",
     ["مدیتیشن ذهن آگاهی", "آرامش ذن", "مراقبه روزانه"],
     ["Still Mind", "Mindful Minutes", "Present Moment", "Breath & Focus"]),
    ("productivity", "Productivity Systems", "Do less, finish more",
     ["بهره وری", "مدیریت زمان", "برنامه ریزانه موفق"],
     ["Deep Output", "Productivity Engine", "Time Craft", "Focus Sprint"]),
    ("confidence", "Confidence & Self-Esteem", "Stand taller every day",
     ["اعتماد به نفس", "عزت نفس", "غرور سالم"],
     ["Bold Within", "Confidence Code", "Own Your Worth", "Stand Tall"]),
    ("communication", "Communication Skills", "Words that land",
     ["مهارت ارتباطی", "فن بیان", "ارتباط موثر"],
     ["Speak Easy", "Charisma Lab", "Words That Land", "Social Voice"]),
    ("leadership", "Leadership & Influence", "Lead without noise",
     ["رهبری", "مدیریت رفتار", "الگوی رهبری"],
     ["Lead Right", "Influence Lab", "The Quiet Leader", "Command Presence"]),
    ("money", "Wealth Mindset", "Think rich, act clear",
     ["ذهنیت پول", "موفقیت مالی", "سرمایه گذاری ذهنیت"],
     ["Money Mind", "Wealth Signal", "Abundance Logic", "Financial Grit"]),
    ("health", "Health Habits", "Feel good, live long",
     ["سلامت", "تغذیه سالم", "عادت‌های سلامت"],
     ["Body Signal", "Health Habits", "Vital Daily", "Feel Good Daily"]),
    ("fitness", "Fitness Motivation", "Stronger every single day",
     ["تناسب اندام", "ورزش انگیزشی", "تمرین بدنسازی"],
     ["Iron Will Fitness", "Move Daily", "Gym Mind", "Stronger Every Day"]),
    ("learning", "Learning & Memory", "Learn faster, remember more",
     ["یادگیری سریع", "تقویت حافظه", "روش مطالعه"],
     ["Learn Faster", "Memory Lab", "Study Spark", "Curious Mind"]),
    ("discovery", "Self-Discovery", "Meet the person underneath",
     ["خودشناسی", "توسعه فردی", "شناخت خود"],
     ["Know Thyself", "Inner Compass", "Self Map", "Deep Within"]),
    ("stoicism", "Stoicism & Resilience", "Unshaken, on purpose",
     ["فلسفه زندگی", "صبر و استقامت", "آرامش در سختی"],
     ["Modern Stoic", "Philosopher's Daily", "Resilient Mind", "Amor Fati"]),
    ("focus", "Focus & Deep Work", "One task, full power",
     ["تمرکز", "حواس پرتی", "کار عمیق"],
     ["Deep Work Daily", "Single Task", "Attention Lab", "Flow State"]),
    ("time", "Time Management", "Own your hours",
     ["مدیریت زمان", "برنامه روزانه", "نظم روزانه"],
     ["Hour Glass", "Time Blocks", "Day Architect", "Schedule Sense"]),
    ("motivation", "Motivation & Inspiration", "Rise, then keep rising",
     ["انگیزشی", "موفقیت", "انگیزه زندگی"],
     ["Rise Daily", "Fuel The Fire", "Momentum Mind", "Unstoppable"]),
    ("thinking", "Critical Thinking", "Think before you believe",
     ["تفکر انتقادی", "حل مسئله", "منطق بازی"],
     ["Think Clear", "Logic Lens", "Skeptic's Guide", "Reason Daily"]),
    ("creativity", "Creativity & Ideas", "Spark, then build",
     ["خلاقیت", "ایده پردازی", "نوآوری"],
     ["Idea Forge", "Creative Pulse", "Spark Studio", "Original Mind"]),
    ("calm", "Calm & Sleep", "Slow down to go further",
     ["آرامش ذهن", "خواب راحت", "کاهش استرس"],
     ["Calm Current", "Sleep Well Daily", "Unwind Mind", "Serene Hours"]),
    ("emotions", "Emotional Mastery", "Feel it, don't be ruled by it",
     ["کنترل هیجان", "مدیریت هیجان", "خودداری از عصبانیت"],
     ["Emotional Grit", "Feelings First", "Mood Mastery", "React Less"]),
    ("social", "Social Skills & Charisma", "People are a skill",
     ["مهارت اجتماعی", "جذابیت اجتماعی", "دوستیابی"],
     ["Social Ease", "People Skills", "First Impression", "Belonging Lab"]),
    ("career", "Career Growth", "Climb with strategy",
     ["موفقیت شغلی", "پیشرفت شغلی", "کارآفرینی"],
     ["Career Climb", "Work Craft", "Pro Move", "Ambition Path"]),
    ("reading", "Reading & Books", "A book a week, a mind for life",
     ["کتاب خوانی", "معرفی کتاب", "خلاصه کتاب"],
     ["Page Turner", "Read More", "Book Bites", "Library Mind"]),
    ("winners", "Success Stories", "How winners actually win",
     ["داستان موفقیت", "زندگینامه موفقیت", "الگوی موفقیت"],
     ["Winner's Mind", "Success Files", "Peak Story", "Rise & Build"]),
]

VOICES = ["en-US-ChristopherNeural",
          "en-US-AvaMultilingualNeural",
          "en-US-AndrewMultilingualNeural",
          "en-US-EmmaMultilingualNeural"]


def palette(i: int) -> list[list[int]]:
    """Deep near-black tint of the category hue + a vivid accent."""
    hue = (i * 0.37) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.72, 0.95)
    accent = [int(r * 255), int(g * 255), int(b * 255)]
    bg = [max(8, int(accent[0] * 0.13) + 6),
          max(8, int(accent[1] * 0.13) + 8),
          max(14, int(accent[2] * 0.13) + 16)]
    band = [min(255, accent[0] // 4 + 10),
            min(255, accent[1] // 4 + 10),
            min(255, accent[2] // 4 + 18)]
    return [bg, accent, band]


def main() -> int:
    channels = []
    cid = 5                                   # 1-4 belong to the originals
    for i, (slug, cat, tagline, queries, names) in enumerate(CATS):
        pal = palette(i)
        for v, name in enumerate(names):
            desc = (f"{tagline}. {cat} in clear, practical daily "
                    f"episodes - ideas you can apply the same day. "
                    f"New video every day. English narration, "
                    f"copyright-free visuals. Part of the MindSeries "
                    f"network ({slug}).")
            channels.append({
                "id": cid,
                "slug": f"{slug}{v + 1}",
                "name": name,
                "category": slug,
                "category_en": cat,
                "tagline": tagline,
                "queries": queries,
                "description": desc,
                "voice": VOICES[v % len(VOICES)],
                "palette": pal,
                "yt_category": "27",           # Education
                "cron": "0 13 * * *",
            })
            cid += 1
    OUT.write_text(json.dumps({"channels": channels},
                              ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"{len(channels)} channels -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
