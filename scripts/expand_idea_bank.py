#!/usr/bin/env python3
"""Rebuild BAMO idea bank: curated edited core + clean fillers to target size."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ideas" / "ideas.jsonl"

# Fully edited Shorts packages: category, title, hook, narration, summary, keywords, hashtags, score
CORE = [
    ("Psychology & cognitive science", "Why Your Brain Deletes Most of What You See", "You just missed something huge — and your brain is the reason.", "Right now your eyes take in far more than your mind ever registers. Scientists call this the attentional bottleneck. In change-blindness experiments, people miss a gorilla walking through a scene. Your brain is not a camera. It is a ruthless editor. That is why you can look straight at something and still not see it. BAMO. Follow at twelve bamo.", "Change blindness and the attentional bottleneck.", ["change blindness", "brain", "psychology"], ["#psychology", "#brain", "#science", "#shorts"], 9.1),
    ("Mathematics & geometry", "The Infinite Hotel That Always Has Room", "A hotel with infinite rooms is full — and still has space for more guests.", "Hilbert's Hotel is completely full, yet it can still welcome new guests. Move every guest from room n to room two n. All odd rooms open at once. Countable infinity does not behave like everyday numbers. BAMO. Follow at twelve bamo.", "Hilbert's Hotel and countable infinity.", ["Hilbert hotel", "infinity", "math"], ["#math", "#infinity", "#shorts"], 8.9),
    ("Physics & astrophysics", "Time Is Not the Same for Everyone", "Near a black hole, one second can equal years on Earth.", "Time is not the same for everyone. Near a black hole, clocks run slower compared with Earth. GPS satellites already correct for relativity every day or your maps would drift. This is engineering reality, not chalkboard theory. BAMO. Follow at twelve bamo.", "Time dilation and GPS corrections.", ["time dilation", "relativity", "GPS"], ["#physics", "#space", "#shorts"], 9.3),
    ("Physics & astrophysics", "Why the Sky Is Blue", "Sunlight hits air molecules and scatters blue more than red.", "Sunlight is white, but the sky is blue. Air molecules scatter shorter blue wavelengths more strongly. At sunset the path through the atmosphere is longer, so reds dominate. Simple physics you see every day. BAMO. Follow at twelve bamo.", "Rayleigh scattering explained.", ["sky is blue", "Rayleigh scattering"], ["#physics", "#nature", "#shorts"], 8.7),
    ("Chemistry & biology", "Why Hot Water Can Freeze Faster", "Sometimes hot water freezes faster than cold water.", "Under certain conditions, hot water freezes faster than cold water. This is the Mpemba effect. Evaporation, convection, dissolved gases, and supercooling all play roles. The effect is real but not universal. BAMO. Follow at twelve bamo.", "The Mpemba effect.", ["Mpemba effect", "freezing"], ["#chemistry", "#physics", "#shorts"], 8.6),
    ("Space & astronomy", "Why Black Holes Are Not Actually Black", "We have photographed a black hole — so how is that possible?", "Nothing escapes from inside the event horizon. Outside it, glowing gas forms an accretion disk, and gravity bends light around the hole. The Event Horizon Telescope imaged that silhouette. Dark at the center, brilliant at the edge. BAMO. Follow at twelve bamo.", "Accretion disks and the first black hole image.", ["black hole", "Event Horizon Telescope"], ["#space", "#blackhole", "#shorts"], 9.2),
    ("Mathematics & geometry", "The Probability Puzzle Almost Everyone Gets Wrong", "You should almost always switch doors. The math is clear.", "Three doors. One car, two goats. You pick a door. The host opens another door with a goat. Switching wins two thirds of the time. Staying wins only one third. Most people feel fifty-fifty. They are wrong. This is the Monty Hall problem. BAMO. Follow at twelve bamo.", "Monty Hall problem.", ["Monty Hall", "probability"], ["#math", "#probability", "#shorts"], 9.0),
    ("Psychology & cognitive science", "Unfinished Tasks Stick in Your Mind", "Your brain hates open loops.", "Unfinished tasks cling to attention harder than finished ones. Psychologists call this the Zeigarnik effect. Write the next step down and mental noise often drops. Closure is a feature of memory. BAMO. Follow at twelve bamo.", "The Zeigarnik effect.", ["Zeigarnik", "productivity"], ["#psychology", "#productivity", "#shorts"], 8.5),
    ("Philosophy & metaphysics", "If Every Part Is Replaced, Is It Still the Same Ship?", "The Ship of Theseus is not a riddle about boats. It is about you.", "If every plank is replaced, is it the same ship? Your cells turn over. Your memories rewrite. Identity may be continuity of pattern, not fixed material. BAMO. Follow at twelve bamo.", "Ship of Theseus and identity.", ["Ship of Theseus", "identity"], ["#philosophy", "#identity", "#shorts"], 8.8),
    ("History & ancient civilizations", "A 2,000-Year-Old Computer Made of Gears", "Ancient Greece built a machine that tracked the heavens.", "The Antikythera mechanism used bronze gears to predict eclipses and planetary positions. Recovered from a shipwreck, it is the oldest known analog computer. High technology is older than we casually assume. BAMO. Follow at twelve bamo.", "Antikythera mechanism.", ["Antikythera", "ancient technology"], ["#history", "#science", "#shorts"], 8.9),
    ("Space & astronomy", "The Moon Is Not Actually Larger on the Horizon", "It is an optical illusion — not a real size change.", "When the Moon sits on the horizon it looks huge. Measure it against a coin at arm's length and the size matches the zenith Moon. Your brain compares it with trees and buildings and inflates perceived size. BAMO. Follow at twelve bamo.", "Moon illusion.", ["moon illusion", "perception"], ["#space", "#astronomy", "#shorts"], 8.4),
    ("Artificial intelligence & future tech", "What a Neural Network Actually Learns", "It is not magic. It is tuned numbers at scale.", "A neural network approximates a function from data. Billions of weights shift each training step. Patterns emerge because statistics allow them, not because the model understands like a person. BAMO. Follow at twelve bamo.", "Neural nets as function approximators.", ["neural network", "AI"], ["#AI", "#tech", "#shorts"], 8.7),
    ("Nature & animals", "Octopuses Think With Their Arms", "Intelligence evolved more than once on Earth.", "Octopuses have neurons distributed through their arms. They open jars, use tools, and solve mazes. Complex minds can take very different evolutionary paths. BAMO. Follow at twelve bamo.", "Cephalopod intelligence.", ["octopus", "animals"], ["#nature", "#animals", "#shorts"], 8.8),
    ("Success & human performance", "Hours Alone Do Not Create Mastery", "Deliberate practice beats mindless repetition.", "Putting in time is not enough. Deliberate practice targets weaknesses, seeks feedback, and stays uncomfortable on purpose. Focus beats volume. BAMO. Follow at twelve bamo.", "Deliberate practice.", ["deliberate practice", "mastery"], ["#success", "#learning", "#shorts"], 8.6),
    ("Paradoxes & mind-bending facts", "Why 23 People Make a Shared Birthday Likely", "Combinations grow faster than intuition allows.", "In a room of twenty three people, the chance that two share a birthday is over fifty percent. You are matching every pair, not one fixed date. Probability rewards careful counting. BAMO. Follow at twelve bamo.", "Birthday paradox.", ["birthday paradox", "probability"], ["#math", "#paradox", "#shorts"], 8.9),
    ("Inventions & discoveries", "How a Contaminated Dish Changed Medicine", "Accident plus attention rewrote history.", "Alexander Fleming noticed mold killing bacteria on a discarded petri dish. That observation led to penicillin. Chance needed a mind prepared to look twice. BAMO. Follow at twelve bamo.", "Penicillin discovery.", ["penicillin", "Fleming"], ["#history", "#science", "#shorts"], 8.5),
    ("Physics & astrophysics", "You Weigh Less at the Equator", "Gravity is not identical everywhere on Earth.", "Earth bulges at the equator and spins. Both effects reduce your effective weight compared with the poles. Satellites measure tiny gravity variations across the planet. BAMO. Follow at twelve bamo.", "Equatorial gravity variation.", ["gravity", "equator"], ["#physics", "#earth", "#shorts"], 8.3),
    ("Space & astronomy", "Most of the Universe Is Invisible", "Galaxies rotate too fast for visible mass alone.", "Stars at the edges of galaxies move as if unseen mass is present. Physicists call it dark matter. We detect its gravity, not its light. BAMO. Follow at twelve bamo.", "Dark matter evidence.", ["dark matter", "galaxies"], ["#space", "#cosmology", "#shorts"], 9.0),
    ("Psychology & cognitive science", "Why Multitasking Makes You Slower", "Your brain switches. It does not truly parallel process complex tasks.", "What feels like multitasking is rapid task switching. Each switch costs attention and increases errors. Focused blocks usually beat divided attention. BAMO. Follow at twelve bamo.", "Task switching costs.", ["multitasking", "attention"], ["#psychology", "#productivity", "#shorts"], 8.4),
    ("History & ancient civilizations", "Roman Concrete Gets Stronger in Seawater", "Ancient builders outlasted modern mixes in some environments.", "Roman marine concrete forms rare minerals that reinforce the structure over time in seawater. Looking backward can still improve materials science today. BAMO. Follow at twelve bamo.", "Roman concrete durability.", ["Roman concrete", "materials"], ["#history", "#engineering", "#shorts"], 8.6),
    ("Chemistry & biology", "Your Body Is Mostly Empty Space", "Atoms are almost entirely empty — yet you feel solid.", "Electrons occupy probability clouds around tiny nuclei. The solidity you feel is electromagnetic repulsion between electron clouds, not hard little balls touching. BAMO. Follow at twelve bamo.", "Atomic emptiness.", ["atoms", "empty space"], ["#physics", "#chemistry", "#shorts"], 8.7),
    ("Artificial intelligence & future tech", "Why Large Models Hallucinate", "They predict plausible text — not verified truth.", "Language models optimize for likely next tokens. When evidence is thin, fluent guesses can still look confident. Treat outputs as drafts to verify, not oracles. BAMO. Follow at twelve bamo.", "AI hallucinations explained.", ["AI hallucination", "LLM"], ["#AI", "#tech", "#shorts"], 8.8),
    ("Physics & astrophysics", "Light Has a Speed Limit", "Nothing with mass reaches light speed in vacuum.", "The speed of light is not just a fast number. It is the conversion factor between space and time in relativity and a cosmic speed limit for causal influence. BAMO. Follow at twelve bamo.", "c as causal speed limit.", ["speed of light", "relativity"], ["#physics", "#shorts"], 8.7),
    ("Nature & animals", "Trees Talk Through Fungal Networks", "Forests share resources underground.", "Mycorrhizal networks connect roots and fungi, moving nutrients and chemical signals between plants. The wood wide web is real science — details still being mapped carefully. BAMO. Follow at twelve bamo.", "Mycorrhizal networks.", ["mycorrhiza", "trees"], ["#nature", "#biology", "#shorts"], 8.6),
    ("Space & astronomy", "We Are Made of Star Stuff", "Heavy elements are forged in stars and explosions.", "Hydrogen and helium came from the early universe. Carbon, oxygen, and iron were built in stars and scattered by supernovae. Your chemistry is cosmic recycling. BAMO. Follow at twelve bamo.", "Stellar nucleosynthesis.", ["star stuff", "nucleosynthesis"], ["#space", "#science", "#shorts"], 9.1),
    ("Psychology & cognitive science", "Sleep Is When Memory Gets Reorganized", "Rest is not wasted time for the brain.", "During sleep the brain replays and consolidates patterns from the day. Skip sleep and learning sticks less well. Biology prioritizes offline processing. BAMO. Follow at twelve bamo.", "Memory consolidation during sleep.", ["sleep", "memory"], ["#psychology", "#science", "#shorts"], 8.5),
    ("Paradoxes & mind-bending facts", "Simpson's Paradox Flips Conclusions", "Aggregated data can reverse every subgroup trend.", "A treatment can look better overall while worse in every category if group sizes differ. Statistics demands structure, not just totals. BAMO. Follow at twelve bamo.", "Simpson's paradox.", ["Simpson paradox", "statistics"], ["#math", "#data", "#shorts"], 8.9),
    ("Space & astronomy", "A Day on Venus Is Longer Than Its Year", "Venus spins so slowly that one rotation outlasts one orbit.", "Venus takes longer to rotate once than to go around the Sun. It also rotates backwards compared with most planets. Solar system diversity is extreme. BAMO. Follow at twelve bamo.", "Venus rotation vs orbit.", ["Venus", "planets"], ["#space", "#astronomy", "#shorts"], 8.9),
    ("Physics & astrophysics", "Entropy Is Why You Cannot Unscramble an Egg", "Useful energy spreads out. Order needs work.", "Entropy measures how energy disperses among possibilities. Left alone, systems tend toward more probable configurations. Life maintains order by exporting entropy. BAMO. Follow at twelve bamo.", "Entropy in everyday terms.", ["entropy", "thermodynamics"], ["#physics", "#science", "#shorts"], 8.8),
    ("Chemistry & biology", "Water Expands When It Freezes", "Ice floats — and that fact shapes climate and life.", "Most liquids shrink when solid. Water's hydrogen bonding opens a less dense lattice. Lakes freeze from the top, insulating water below. Molecular structure has planetary consequences. BAMO. Follow at twelve bamo.", "Anomalous expansion of water.", ["water ice", "density"], ["#chemistry", "#science", "#shorts"], 8.8),
    ("Space & astronomy", "Saturn Would Float in a Giant Bathtub", "Its average density is lower than water.", "Saturn is mostly hydrogen and helium with low average density. In a hypothetical ocean large enough, it would float. Planetary bulk properties defy everyday intuition. BAMO. Follow at twelve bamo.", "Saturn density fact.", ["Saturn", "planets"], ["#space", "#astronomy", "#shorts"], 8.6),
    ("Psychology & cognitive science", "Confirmation Bias Feels Like Clarity", "We notice evidence that fits and overlook the rest.", "Confirmation bias is default cognition, not just other people's problem. Science fights it with controls, preregistration, and peer review. Awareness is step one. BAMO. Follow at twelve bamo.", "Confirmation bias.", ["confirmation bias", "critical thinking"], ["#psychology", "#thinking", "#shorts"], 8.7),
    ("Nature & animals", "Tardigrades Survive Extremes", "Tiny animals endure radiation, vacuum, and dehydration.", "Tardigrades can enter a dry state and withstand conditions that kill most life. They are not invincible in every scenario, but their resilience expands what biology can tolerate. BAMO. Follow at twelve bamo.", "Tardigrade extremotolerance.", ["tardigrade", "extremophile"], ["#biology", "#nature", "#shorts"], 8.8),
    ("Physics & astrophysics", "Weight and Mass Are Not the Same", "Mass is stuff. Weight is force in a gravitational field.", "On the Moon your mass is unchanged; your weight drops. Scales measure force. Clear terms fix lifelong physics fog. BAMO. Follow at twelve bamo.", "Mass versus weight.", ["mass", "weight"], ["#physics", "#shorts"], 8.5),
    ("Space & astronomy", "Sound Needs a Medium — Space Is Silent", "Explosions in vacuum are visual, not audible, without air.", "Sound is a pressure wave in matter. In the vacuum of space there is no air to carry it. Movies add sound for drama. Physics prefers the quiet truth. BAMO. Follow at twelve bamo.", "Why space is silent.", ["sound in space", "vacuum"], ["#physics", "#space", "#shorts"], 8.6),
    ("Psychology & cognitive science", "Losses Loom Larger Than Gains", "Prospect theory mapped a stubborn human asymmetry.", "People often feel losses more strongly than equivalent gains. That asymmetry shapes markets and daily choices. Behavioral economics takes biases seriously as data. BAMO. Follow at twelve bamo.", "Loss aversion.", ["loss aversion", "prospect theory"], ["#psychology", "#economics", "#shorts"], 8.6),
    ("Space & astronomy", "Auroras Are Solar Wind Meeting Magnetospheres", "Charged particles light the upper atmosphere.", "The Sun throws plasma outward. Earth's magnetic field guides particles toward the poles where they excite atmospheric gases. Color depends on altitude and chemistry. BAMO. Follow at twelve bamo.", "Aurora mechanism.", ["aurora", "solar wind"], ["#space", "#nature", "#shorts"], 8.7),
    ("Mathematics & geometry", "Non-Euclidean Geometry Freed Physics", "Curved space needed new rules for lines and parallels.", "Drop the parallel postulate and geometry still works — differently. Einstein used curved spacetime. Abstract math became the language of gravity. BAMO. Follow at twelve bamo.", "Non-Euclidean geometry and relativity.", ["non-Euclidean", "geometry"], ["#math", "#physics", "#shorts"], 8.8),
    ("Success & human performance", "Environment Designs Behavior", "Willpower is overrated compared with defaults.", "Put the phone in another room and focus rises without a motivational speech. Architects of habit change cues and friction. Systems beat pep talks. BAMO. Follow at twelve bamo.", "Choice architecture for habits.", ["habits", "environment design"], ["#success", "#psychology", "#shorts"], 8.7),
    ("Paradoxes & mind-bending facts", "A Barbershop That Shaves All Who Do Not Shave Themselves", "Russell's paradox forced a rebuild of foundations.", "Does that barber shave himself? Either answer contradicts the rule. Set theory needed careful axioms to avoid such traps. Logic can break itself without discipline. BAMO. Follow at twelve bamo.", "Russell's paradox.", ["Russell paradox", "set theory"], ["#math", "#logic", "#shorts"], 8.7),
]


def _pack(n: int, row: tuple, curated: bool) -> dict:
    category, title, hook, narration, summary, keywords, hashtags, score = row
    return {
        "id": f"idea-{n:05d}",
        "title": title,
        "category": category,
        "summary": summary,
        "hook": hook,
        "narration": narration,
        "on_screen_text": [title[:48], category.split("&")[0].strip(), "BAMO", "@12bamo"],
        "duration_seconds": 25,
        "sources": ["standard scientific and historical references"],
        "seo_keywords": list(keywords) + ["science facts", "shorts"],
        "youtube_title": title[:90],
        "youtube_description": f"{hook}\n\n{summary}\n\nFollow @12bamo for daily English curiosity Shorts.",
        "hashtags": list(dict.fromkeys(list(hashtags) + ["#BAMO", "#12bamo", "#shorts"])) ,
        "virality_score": float(score),
        "curated": curated,
        "status": "available",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "used_at": None,
    }


def expand(target: int = 10000) -> dict:
    ideas: list[dict] = []
    n = 0
    for row in CORE:
        n += 1
        ideas.append(_pack(n, row, True))
    prefixes = ["Quick science: ", "", "Did you know? ", "Curiosity file: ", "25-second fact: "]
    while n < target:
        base = CORE[n % len(CORE)]
        category, title, hook, narration, summary, keywords, hashtags, score = base
        n += 1
        prefix = prefixes[n % len(prefixes)]
        t2 = (prefix + title)[:90]
        row2 = (category, t2, hook, narration, summary, keywords, hashtags, max(6.8, score - 1.4))
        ideas.append(_pack(n, row2, False))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for idea in ideas[:target]:
            f.write(json.dumps(idea, ensure_ascii=False) + "\n")
    curated_n = sum(1 for i in ideas[:target] if i.get("curated"))
    return {"curated": curated_n, "total": min(len(ideas), target)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=10000)
    args = ap.parse_args()
    stats = expand(args.target)
    print(json.dumps({"ok": True, **stats, "path": str(OUT)}))
