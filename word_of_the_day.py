"""
Word of the day — one German or precise English word, stable for the local date.

Shown on the Home widget. Evening check-in interpolates the same word into
its “use this word” prompt.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import eel

from paths import data_directory

HISTORY_KEEP = 60
STATE_NAME = "word_of_the_day.json"

# Mix of useful German and precise English. ids are stable; do not reuse one
# for a different word.
WORDS: List[Dict[str, str]] = [
    {
        "id": "de-fernweh",
        "word": "Fernweh",
        "language": "de",
        "language_label": "German",
        "article": "das",
        "pos": "noun",
        "meaning": "a longing to be far away; wanderlust with an ache in it",
        "example": "Sunday left her with Fernweh for a train that was not on any timetable.",
    },
    {
        "id": "de-geborgenheit",
        "word": "Geborgenheit",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "the feeling of being safe, held, and at home in a place or with a person",
        "example": "The kitchen at midnight had a Geborgenheit no hotel lobby could copy.",
    },
    {
        "id": "de-sehnsucht",
        "word": "Sehnsucht",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "a deep, lingering yearning — often for something unnamed",
        "example": "There was Sehnsucht in the way he kept the window cracked in winter.",
    },
    {
        "id": "de-vorfreude",
        "word": "Vorfreude",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "the joy of looking forward to something; happiness that arrives early",
        "example": "Packing the bag was already Vorfreude, not just a chore.",
    },
    {
        "id": "de-feierabend",
        "word": "Feierabend",
        "language": "de",
        "language_label": "German",
        "article": "der",
        "pos": "noun",
        "meaning": "the end of the working day; the hour when work is allowed to stop",
        "example": "He protected Feierabend the way other people protect a meeting.",
    },
    {
        "id": "de-zuversicht",
        "word": "Zuversicht",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "quiet confidence that things can still go well",
        "example": "She spoke with Zuversicht, not with slogans.",
    },
    {
        "id": "de-fingerspitzengefuehl",
        "word": "Fingerspitzengefühl",
        "language": "de",
        "language_label": "German",
        "article": "das",
        "pos": "noun",
        "meaning": "intuitive tact; a fingertip sense for the right touch",
        "example": "The edit needed Fingerspitzengefühl, not a red pen.",
    },
    {
        "id": "de-weltschmerz",
        "word": "Weltschmerz",
        "language": "de",
        "language_label": "German",
        "article": "der",
        "pos": "noun",
        "meaning": "world-weariness; sorrow at the gap between the world as it is and as it should be",
        "example": "The news left a thin film of Weltschmerz over an otherwise fine afternoon.",
    },
    {
        "id": "de-augenblick",
        "word": "Augenblick",
        "language": "de",
        "language_label": "German",
        "article": "der",
        "pos": "noun",
        "meaning": "a moment; literally the blink of an eye",
        "example": "In that Augenblick the room went quiet enough to hear the clock.",
    },
    {
        "id": "de-lichtblick",
        "word": "Lichtblick",
        "language": "de",
        "language_label": "German",
        "article": "der",
        "pos": "noun",
        "meaning": "a ray of hope; a bright spot in a dull stretch",
        "example": "The short walk between classes was the Lichtblick of the day.",
    },
    {
        "id": "de-gemuetlichkeit",
        "word": "Gemütlichkeit",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "a cozy, unhurried warmth — of a room, a meal, or a mood",
        "example": "They chased Gemütlichkeit with soup and a too-dim lamp.",
    },
    {
        "id": "de-neugier",
        "word": "Neugier",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "curiosity; the itch to know what is around the corner",
        "example": "Neugier got her through the first dull chapter.",
    },
    {
        "id": "de-ausdauer",
        "word": "Ausdauer",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "stamina; the ability to keep going without drama",
        "example": "The problem asked for Ausdauer more than brilliance.",
    },
    {
        "id": "de-sorgfalt",
        "word": "Sorgfalt",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "care, diligence, attention to the small thing done well",
        "example": "He revised the footnote with unnecessary Sorgfalt, and it showed.",
    },
    {
        "id": "de-klarheit",
        "word": "Klarheit",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "clarity — of thought, of a sentence, of a decision",
        "example": "After the walk she had Klarheit about what to cut.",
    },
    {
        "id": "de-ehrgeiz",
        "word": "Ehrgeiz",
        "language": "de",
        "language_label": "German",
        "article": "der",
        "pos": "noun",
        "meaning": "ambition; the drive to reach further than the current version of yourself",
        "example": "His Ehrgeiz was quiet, which made it harder to dismiss.",
    },
    {
        "id": "de-demut",
        "word": "Demut",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "humility; knowing the work is larger than your last success",
        "example": "She took the correction with Demut and a notebook.",
    },
    {
        "id": "de-entschlossenheit",
        "word": "Entschlossenheit",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "resolve; the state of having decided and meaning it",
        "example": "Monday wanted Entschlossenheit, not another plan.",
    },
    {
        "id": "de-zusammenhalt",
        "word": "Zusammenhalt",
        "language": "de",
        "language_label": "German",
        "article": "der",
        "pos": "noun",
        "meaning": "cohesion; the glue that keeps a group from fraying",
        "example": "The team’s Zusammenhalt survived a sloppy week.",
    },
    {
        "id": "de-gleichgewicht",
        "word": "Gleichgewicht",
        "language": "de",
        "language_label": "German",
        "article": "das",
        "pos": "noun",
        "meaning": "balance; equilibrium between competing pulls",
        "example": "He was hunting Gleichgewicht, not a perfect day.",
    },
    {
        "id": "de-umweg",
        "word": "Umweg",
        "language": "de",
        "language_label": "German",
        "article": "der",
        "pos": "noun",
        "meaning": "a detour; the longer way that still counts as a way",
        "example": "The Umweg through the side street was the better hour.",
    },
    {
        "id": "de-zwischenzeit",
        "word": "Zwischenzeit",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "the in-between time; the stretch that is neither start nor finish",
        "example": "Most of the work lived in the Zwischenzeit, not in the deadline hour.",
    },
    {
        "id": "de-alltaeglichkeit",
        "word": "Alltäglichkeit",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "everyday-ness; the texture of an ordinary day",
        "example": "He tried to write the Alltäglichkeit without making it small.",
    },
    {
        "id": "de-zweisamkeit",
        "word": "Zweisamkeit",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "the togetherness of two; solitude that is shared",
        "example": "They practiced Zweisamkeit by leaving the phones in another room.",
    },
    {
        "id": "de-fortschritt",
        "word": "Fortschritt",
        "language": "de",
        "language_label": "German",
        "article": "der",
        "pos": "noun",
        "meaning": "progress; a measurable step, however unglamorous",
        "example": "Three honest pages was Fortschritt, even if nobody clapped.",
    },
    {
        "id": "de-ruhe",
        "word": "Ruhe",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "calm, quiet, rest — the opposite of a jittery mind",
        "example": "She guarded a half hour of Ruhe before opening the laptop.",
    },
    {
        "id": "de-geduld",
        "word": "Geduld",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "patience; the willingness to let a thing take the time it takes",
        "example": "The proof required Geduld more than a clever trick.",
    },
    {
        "id": "de-hinterfragen",
        "word": "hinterfragen",
        "language": "de",
        "language_label": "German",
        "article": "",
        "pos": "verb",
        "meaning": "to question critically; to look behind an assumption",
        "example": "He hinterfragte the ‘should’ until it became a choice.",
    },
    {
        "id": "de-verweilen",
        "word": "verweilen",
        "language": "de",
        "language_label": "German",
        "article": "",
        "pos": "verb",
        "meaning": "to linger; to stay with something instead of rushing past it",
        "example": "She verweilte on the sentence until it stopped sounding borrowed.",
    },
    {
        "id": "de-nachholen",
        "word": "nachholen",
        "language": "de",
        "language_label": "German",
        "article": "",
        "pos": "verb",
        "meaning": "to catch up on; to do later what was missed",
        "example": "He nachholte the reading on the train, without pretending it was ideal.",
    },
    {
        "id": "de-beharrlich",
        "word": "beharrlich",
        "language": "de",
        "language_label": "German",
        "article": "",
        "pos": "adjective",
        "meaning": "persistent; stubborn in a useful way",
        "example": "A beharrlich hour beat a heroic all-nighter.",
    },
    {
        "id": "de-achtsam",
        "word": "achtsam",
        "language": "de",
        "language_label": "German",
        "article": "",
        "pos": "adjective",
        "meaning": "mindful; careful in attention, not only in manners",
        "example": "An achtsam pause before answering saved the conversation.",
    },
    {
        "id": "de-nachdenklich",
        "word": "nachdenklich",
        "language": "de",
        "language_label": "German",
        "article": "",
        "pos": "adjective",
        "meaning": "pensive; given to thinking something through",
        "example": "He looked nachdenklich at the draft and cut the clever paragraph.",
    },
    {
        "id": "de-zuverlaessig",
        "word": "zuverlässig",
        "language": "de",
        "language_label": "German",
        "article": "",
        "pos": "adjective",
        "meaning": "reliable; someone or something you can count on without checking twice",
        "example": "The zuverlässig note in the morning changed the whole day.",
    },
    {
        "id": "de-torschlusspanik",
        "word": "Torschlusspanik",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "the panic that doors are closing; fear of being too late",
        "example": "He named the Torschlusspanik and then did the next small thing anyway.",
    },
    {
        "id": "de-selbstwirksamkeit",
        "word": "Selbstwirksamkeit",
        "language": "de",
        "language_label": "German",
        "article": "die",
        "pos": "noun",
        "meaning": "self-efficacy; the belief that your actions can still change the outcome",
        "example": "Selbstwirksamkeit returned when she finished one ugly first pass.",
    },
    {
        "id": "en-equanimity",
        "word": "equanimity",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "mental calmness under strain; composure that does not require a blank mind",
        "example": "He answered the critique with equanimity, then asked one precise question.",
    },
    {
        "id": "en-perspicacious",
        "word": "perspicacious",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "having keen insight; seeing through the surface of a situation",
        "example": "A perspicacious reading of the email saved them an argument.",
    },
    {
        "id": "en-liminal",
        "word": "liminal",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "on a threshold; in between one state and the next",
        "example": "Dusk is a liminal hour, which is why it is good for walking and bad for rushing.",
    },
    {
        "id": "en-laconic",
        "word": "laconic",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "using few words; brief in a way that still lands",
        "example": "Her laconic ‘done’ was more useful than a paragraph of hedging.",
    },
    {
        "id": "en-ephemeral",
        "word": "ephemeral",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "lasting only a short time; beautiful partly because it will not stay",
        "example": "The good mood was ephemeral, so he wrote while it lasted.",
    },
    {
        "id": "en-apposite",
        "word": "apposite",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "strikingly appropriate; the right example at the right moment",
        "example": "It was an apposite story, and nobody needed it explained.",
    },
    {
        "id": "en-trenchant",
        "word": "trenchant",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "incisive and vigorous; cutting in a useful way, not a cruel one",
        "example": "The trenchant note in the margin named the real problem.",
    },
    {
        "id": "en-inchoate",
        "word": "inchoate",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "just beginning; not yet fully formed",
        "example": "The idea was still inchoate, which is why it needed a walk, not a meeting.",
    },
    {
        "id": "en-redolent",
        "word": "redolent",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "strongly suggestive of; fragrant with a memory or a place",
        "example": "The hallway was redolent of pencil shavings and old raincoats.",
    },
    {
        "id": "en-pellucid",
        "word": "pellucid",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "transparently clear — of water, of prose, of an explanation",
        "example": "She rewrote the intro until it was pellucid enough to read aloud.",
    },
    {
        "id": "en-sagacious",
        "word": "sagacious",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "wise in a practical, far-seeing way",
        "example": "A sagacious pause kept him from sending the midnight draft.",
    },
    {
        "id": "en-forbearance",
        "word": "forbearance",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "patient restraint; choosing not to snap when you could",
        "example": "The conversation survived on forbearance and one good question.",
    },
    {
        "id": "en-solicitude",
        "word": "solicitude",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "careful concern for someone; attention that is not nosy",
        "example": "His solicitude showed up as tea, not as advice.",
    },
    {
        "id": "en-provenance",
        "word": "provenance",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "the origin and history of a thing; where it came from and how it got here",
        "example": "She asked for the provenance of the claim before repeating it.",
    },
    {
        "id": "en-quiescent",
        "word": "quiescent",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "temporarily quiet or inactive; at rest, not gone",
        "example": "The worry went quiescent after he wrote it down.",
    },
    {
        "id": "en-insouciant",
        "word": "insouciant",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "casually unconcerned; light in a way that can be either charm or avoidance",
        "example": "An insouciant shrug was the wrong tool for a real deadline.",
    },
    {
        "id": "en-perfunctory",
        "word": "perfunctory",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "done as a duty, with little care or interest",
        "example": "He refused a perfunctory reply and wrote the honest one instead.",
    },
    {
        "id": "en-ineluctable",
        "word": "ineluctable",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "unable to be avoided or escaped",
        "example": "Sleep was the ineluctable next item, however unfinished the list.",
    },
    {
        "id": "en-recondite",
        "word": "recondite",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "little known; difficult in a way that hides rather than reveals",
        "example": "He cut the recondite joke; clarity was the kinder flex.",
    },
    {
        "id": "en-salutary",
        "word": "salutary",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "producing a beneficial effect, even if it stings at first",
        "example": "The failed attempt was salutary; it named the real bottleneck.",
    },
    {
        "id": "en-circumspect",
        "word": "circumspect",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "wary and considered; looking around before you step",
        "example": "A circumspect reply left the door open without promising the moon.",
    },
    {
        "id": "en-evanescent",
        "word": "evanescent",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "quickly fading; vanishing almost as soon as it appears",
        "example": "The evanescent smell of rain made him walk the long way home.",
    },
    {
        "id": "en-taciturn",
        "word": "taciturn",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "reserved in speech; not unfriendly, just economical with words",
        "example": "The taciturn yes still counted; he did not need a speech.",
    },
    {
        "id": "en-unstinting",
        "word": "unstinting",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "given freely and generously, without holding back",
        "example": "Her unstinting attention for twenty minutes beat a distracted hour.",
    },
    {
        "id": "en-aplomb",
        "word": "aplomb",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "self-possession under pressure; composure with a little style",
        "example": "He handled the detour with aplomb and a better playlist.",
    },
    {
        "id": "en-candor",
        "word": "candor",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "frankness; the habit of saying the true thing without theater",
        "example": "Candor about being tired was more useful than another coffee.",
    },
    {
        "id": "en-fortitude",
        "word": "fortitude",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "courage in pain or difficulty; staying power of character",
        "example": "The week asked for fortitude, not a new personality.",
    },
    {
        "id": "en-gravitas",
        "word": "gravitas",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "dignity and seriousness of manner; weight that does not shout",
        "example": "The short speech had gravitas because it skipped the filler.",
    },
    {
        "id": "en-heuristic",
        "word": "heuristic",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "a practical rule of thumb for finding a good-enough answer",
        "example": "‘If it takes under two minutes, do it now’ is a blunt heuristic, and it works.",
    },
    {
        "id": "en-judicious",
        "word": "judicious",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "showing sound judgment; careful in a way that is wise, not timid",
        "example": "A judicious cut made the essay shorter and better.",
    },
    {
        "id": "en-nascent",
        "word": "nascent",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "coming into being; just starting to exist",
        "example": "The nascent habit survived because he kept the bar embarrassingly low.",
    },
    {
        "id": "en-pragmatic",
        "word": "pragmatic",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "concerned with what works in practice, not with the prettier theory",
        "example": "A pragmatic twenty minutes beat waiting for the perfect block.",
    },
    {
        "id": "en-quixotic",
        "word": "quixotic",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "exceedingly idealistic; noble in aim and a little unworldly",
        "example": "The plan was quixotic, which is why they also packed a sandwich.",
    },
    {
        "id": "en-reticent",
        "word": "reticent",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "inclined to keep silent; reserved about what you share",
        "example": "He was reticent about the win and precise about the next step.",
    },
    {
        "id": "en-tenacious",
        "word": "tenacious",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "holding fast; not letting a problem or a standard slip",
        "example": "A tenacious reread caught the error nobody else had time for.",
    },
    {
        "id": "en-vicarious",
        "word": "vicarious",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "felt through someone else’s experience rather than your own",
        "example": "Vicarious adventure is fine; the walk still had to be his.",
    },
    {
        "id": "en-wistful",
        "word": "wistful",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "full of a gentle, slightly sad longing",
        "example": "A wistful look at the old notebook, then he opened a blank page.",
    },
    {
        "id": "en-exacting",
        "word": "exacting",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "making severe demands; requiring precision and effort",
        "example": "The teacher was exacting, which is why the sentences got better.",
    },
    {
        "id": "en-galvanize",
        "word": "galvanize",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "verb",
        "meaning": "to shock or stir someone into sudden action",
        "example": "The small public deadline galvanized a week of honest work.",
    },
    {
        "id": "en-harbinger",
        "word": "harbinger",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "noun",
        "meaning": "a sign of what is coming; something that announces a change",
        "example": "The first cool morning was a harbinger, so he got the coat down.",
    },
    {
        "id": "en-lucid",
        "word": "lucid",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "easy to understand; clear in thought and in speech",
        "example": "A lucid outline made the hard chapter feel possible.",
    },
    {
        "id": "en-abiding",
        "word": "abiding",
        "language": "en",
        "language_label": "English",
        "article": "",
        "pos": "adjective",
        "meaning": "lasting; continuing for a long time without fuss",
        "example": "An abiding interest in the problem outlasted the first burst of motivation.",
    },
]

_WORDS_BY_ID = {row["id"]: row for row in WORDS}


def _today() -> str:
    return date.today().isoformat()


def _path() -> Any:
    return data_directory() / STATE_NAME


def _word_index() -> Dict[str, Dict[str, str]]:
    return _WORDS_BY_ID


def display_form(word: Dict[str, Any]) -> str:
    article = str(word.get("article") or "").strip()
    name = str(word.get("word") or "").strip()
    if article:
        return f"{article} {name}"
    return name


def public_word(word: Dict[str, Any], *, on: Optional[str] = None) -> Dict[str, Any]:
    packed = {
        "date": on or _today(),
        "id": word.get("id") or "",
        "word": word.get("word") or "",
        "display": display_form(word),
        "language": word.get("language") or "en",
        "language_label": word.get("language_label") or "English",
        "article": word.get("article") or "",
        "pos": word.get("pos") or "",
        "meaning": word.get("meaning") or "",
        "example": word.get("example") or "",
    }
    packed["prompt"] = (
        f"Use {packed['display']} in a sentence or a short note about today."
    )
    return packed


def fill_text(text: Any, word: Optional[Dict[str, Any]] = None) -> Any:
    if not isinstance(text, str) or "{" not in text:
        return text
    payload = word if word is not None else ensure_today_word()
    mapping = {
        "{word}": payload.get("word") or "",
        "{display}": payload.get("display") or payload.get("word") or "",
        "{meaning}": payload.get("meaning") or "",
        "{language}": payload.get("language_label") or "",
        "{example}": payload.get("example") or "",
        "{article}": payload.get("article") or "",
        "{pos}": payload.get("pos") or "",
    }
    out = text
    for needle, value in mapping.items():
        out = out.replace(needle, value)
    return out


def decorate_flow(flow: Dict[str, Any], word: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fill {word} placeholders in a checklist definition for the live wizard."""
    data = json.loads(json.dumps(flow))
    payload = word if word is not None else ensure_today_word()
    nodes = data.get("nodes")
    if not isinstance(nodes, dict):
        return data
    for node in nodes.values():
        if not isinstance(node, dict):
            continue
        for key in ("question", "placeholder"):
            if key in node:
                node[key] = fill_text(node[key], payload)
    return data


def _load_state() -> Dict[str, Any]:
    path = _path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write_state(state: Dict[str, Any]) -> None:
    path = _path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _history_ids(state: Dict[str, Any], skip_date: str) -> List[str]:
    rows = state.get("history")
    if not isinstance(rows, list):
        return []
    ids: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("date") or "") == skip_date:
            continue
        wid = str(row.get("id") or "").strip()
        if wid:
            ids.append(wid)
    return ids[-HISTORY_KEEP:]


def pick_word(day: str, used_ids: List[str], catalog: Optional[List[Dict[str, str]]] = None) -> Dict[str, str]:
    pool = list(catalog or WORDS)
    if not pool:
        raise ValueError("Word list is empty")
    used = set(used_ids)
    available = [row for row in pool if row.get("id") not in used]
    if not available:
        available = pool
    digest = hashlib.sha256(f"kosistenz-wotd:{day}".encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(available)
    return available[index]


def _current_from_state(state: Dict[str, Any], day: str) -> Optional[Dict[str, Any]]:
    current = state.get("current")
    if not isinstance(current, dict):
        return None
    if str(current.get("date") or "") != day:
        return None
    stored_id = str(current.get("id") or "")
    catalog = _word_index()
    if stored_id in catalog:
        return public_word(catalog[stored_id], on=day)
    if current.get("word") and current.get("meaning"):
        return public_word(current, on=day)
    return None


def ensure_today_word(day: Optional[str] = None) -> Dict[str, Any]:
    on = day or _today()
    state = _load_state()
    existing = _current_from_state(state, on)
    if existing:
        return existing
    chosen = pick_word(on, _history_ids(state, on))
    packed = public_word(chosen, on=on)
    history = [row for row in (state.get("history") or []) if isinstance(row, dict)]
    history = [row for row in history if str(row.get("date") or "") != on]
    history.append({"date": on, "id": packed["id"]})
    _write_state({"current": packed, "history": history[-HISTORY_KEEP:]})
    return packed


def _usage_from_today(day: str) -> Optional[str]:
    try:
        import daily_checklist
    except Exception:
        return None
    try:
        rows = daily_checklist.fetch_submissions(local_date=day, decorate=False)
    except Exception:
        return None
    for row in rows:
        answers = row.get("answers") or {}
        text = answers.get("word_use")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


@eel.expose
def get_word_of_the_day() -> Dict[str, Any]:
    packed = dict(ensure_today_word())
    packed["used_tonight"] = _usage_from_today(packed["date"])
    packed["generated_at"] = datetime.now().isoformat(timespec="seconds")
    return packed
