"""Plain-language wording for the web UI (DECISIONS D30).

Everything here is presentation. It turns numbers the analyses already produced into sentences
a coach, a club player or a recruiter can read without statistics. Nothing is computed beyond
rounding, and the exact values travel next to each sentence in the JSON.

Rules implemented here:
* no statistics vocabulary in the main text (no "CI", "n=", "entropy", "fold", "AUC", ...);
* frequencies as "about 1 time in 14" when both sides of a comparison are under 30%, whole
  percentages otherwise; never a decimal or a signed point difference;
* court areas named the way players name them ("back backhand corner"), never zone codes;
* a player is always named by surname. The dataset does not record how a player wants to be
  referred to, and a wrong pronoun is worse than a repeated name.
"""

from __future__ import annotations

import pandas as pd

from tactics.analyses import AnalysisSettings
from tactics.report import SHOT_PHRASES, _parse, borderline, is_stable, surname, tentative

AREA = {
    "front_fh": "front forehand corner",
    "front_bh": "front backhand corner",
    "mid_fh": "middle of the court, forehand side",
    "mid_bh": "middle of the court, backhand side",
    "rear_fh": "back forehand corner",
    "rear_bh": "back backhand corner",
    "body": "body",
    "out": "out",
    "net_error": "into the net",
}

# "a clear", "a push or rush": the singular noun phrase for an incoming shot
A_SHOT = {
    "push_rush": "a push or rush",
    "smash": "a smash",
    "net": "a net shot",
    "defensive": "a defensive return",
    "drop": "a drop",
    "lob": "a lob",
    "clear": "a clear",
    "drive": "a drive",
    "short_service": "a short serve",
    "long_service": "a long serve",
}

SPLIT_PREFIX = {"game3": "In a deciding game, ", "pressure": "Late in a game, "}
QUICKLY = "loses the point quickly"  # defined once on the page: within the next two shots
ONE_IN_BELOW = 0.30  # "1 in N" wording only when both rates are under this


# ---------------------------------------------------------------------------------------
# Words
# ---------------------------------------------------------------------------------------


def shots(shot: str) -> str:
    """'push_rush' -> 'pushes and rushes'."""
    return SHOT_PHRASES.get(shot, (shot.replace("_", " ") + " shots", "", ""))[0]


def shot_verb(shot: str) -> str:
    """'push_rush' -> 'push or rush' (imperative / plural subject)."""
    return SHOT_PHRASES.get(shot, ("", "play a " + shot.replace("_", " "), ""))[1]


def shot_verb3(shot: str) -> str:
    """'push_rush' -> 'pushes or rushes' (singular subject)."""
    return SHOT_PHRASES.get(shot, ("", "", "plays a " + shot.replace("_", " ")))[2]


def a_shot(shot: str) -> str:
    return A_SHOT.get(shot, "a " + shot.replace("_", " "))


def area(zone: str) -> str:
    return AREA.get(zone, zone.replace("_", " "))


def at_area(zone: str, poss: str) -> str:
    """'to Axelsen's back backhand corner' / 'straight at Axelsen's body'."""
    if zone == "body":
        return f"straight at {poss} body"
    if zone in ("out", "net_error"):
        return area(zone)
    return f"to {poss} {area(zone)}"


def possessive(player: str) -> str:
    me = surname(player)
    return f"{me}'" if me.endswith("s") else f"{me}'s"


def pct_int(p: float) -> int:
    """Whole percent, halves rounded up (34.5 -> 35), the way people round aloud."""
    return int(p * 100 + 0.5)


def one_in(p: float) -> str:
    """0.07 -> 'about 1 time in 14'; 0.45 -> 'about 45% of the time'."""
    if p <= 0:
        return "almost never"
    if p >= 0.995:
        return "almost every time"
    if p < ONE_IN_BELOW:
        return f"about 1 time in {int(round(1 / p))}"
    return f"about {pct_int(p)}% of the time"


def freq_pair(p: float, q: float) -> tuple[str, str]:
    """Two rates in the same form, so the reader can compare them."""
    if p < ONE_IN_BELOW and q < ONE_IN_BELOW:
        return one_in(p), one_in(q)
    return (
        f"about {pct_int(p)}% of the time",
        f"about {pct_int(q)}% of the time",
    )


def whole_pct(p: float) -> str:
    return f"{pct_int(p)}%"


def metres_words(m: float) -> str:
    """Half-metre rounding without a decimal point: 2.21 -> '2 m', 1.67 -> '1½ m'."""
    half = int(round(m * 2))
    whole, rem = divmod(half, 2)
    if whole == 0:
        return "½ m" if rem else "0 m"
    return f"{whole}½ m" if rem else f"{whole} m"


def cm(m: float) -> str:
    return f"{int(round(abs(m) * 100))} cm"


def _cap(text: str) -> str:
    return text[0].upper() + text[1:] if text else text


def _prefixed(prefix: str, head: str) -> str:
    return prefix + head[0].lower() + head[1:] if prefix else head


# ---------------------------------------------------------------------------------------
# Insights (danger rows)
# ---------------------------------------------------------------------------------------


def headline(row: pd.Series, player: str, s: AnalysisSettings) -> str:
    """The coaching takeaway, in the voice of a coach preparing an opponent."""
    me, poss = surname(player), possessive(player)
    p = _parse(row, s)
    shot, zone, faced, worse = p["shot"], p["zone"], p["faced"], float(row.delta) > 0
    prefix = SPLIT_PREFIX.get(p["split"], "")
    if faced:
        if worse:
            if shot and zone:
                head = f"{_cap(shot_verb(shot))} {at_area(zone, poss)}."
            elif shot:
                head = f"{_cap(shot_verb(shot))} more against {me}."
            elif zone == "body":
                head = f"Hit straight at {poss} body."
            else:
                head = f"Attack {poss} {area(zone)}."
        else:
            if shot and zone:
                head = f"Don't rely on {shots(shot)} {at_area(zone, poss)}."
            elif shot:
                head = f"Don't rely on {shots(shot)} against {me}."
            else:
                head = f"Don't attack {poss} {area(zone)}."
    else:
        if shot and zone:
            what = f"{poss} {shots(shot)} {at_area(zone, 'your')}"
        elif shot:
            what = f"{poss} {shots(shot)}"
        else:
            what = f"anything {me} plays {at_area(zone, 'your')}"
        head = f"Punish {what}." if worse else f"Be ready for {what}."
    return _prefixed(prefix, head)


def situation(row: pd.Series, player: str, s: AnalysisSettings) -> str:
    """'when opponents push or rush to Axelsen's back backhand corner' (no capital)."""
    me, poss = surname(player), possessive(player)
    p = _parse(row, s)
    shot, zone = p["shot"], p["zone"]
    if p["faced"]:
        if shot and zone:
            return f"when opponents {shot_verb(shot)} {at_area(zone, poss)}"
        if shot:
            return f"when opponents {shot_verb(shot)}, wherever it lands"
        if zone == "body":
            return f"when opponents hit straight at {poss} body"
        return f"when opponents play {at_area(zone, poss)}"
    if shot and zone:
        return f"after {poss} {shots(shot)} {at_area(zone, 'the opponent' + chr(39) + 's')}"
    if shot:
        return f"after {poss} {shots(shot)}"
    return f"after anything {me} plays {at_area(zone, 'the opponent' + chr(39) + 's')}"


def evidence(row: pd.Series, player: str, s: AnalysisSettings) -> str:
    """One plain sentence of evidence, two when there is a comparison."""
    me = surname(player)
    p = _parse(row, s)
    prefix = SPLIT_PREFIX.get(p["split"], "")
    sit = situation(row, player, s)
    if row.get("ref_n", 0):
        f1, f2 = freq_pair(float(row.rate), float(row.ref_rate))
        text = f"{sit}, {me} {QUICKLY} {f1}. Most pros lose it {f2}."
    else:
        text = f"{sit}, {me} {QUICKLY} {one_in(float(row.rate))}."
    return _cap(prefix + text) if prefix else _cap(text)


def held_up(row: pd.Series, player: str) -> str | None:
    """'It held up in 15 of 20 re-checks, each one leaving out a different match.'"""
    folds = int(row.get("folds", 0) or 0)
    if not folds:
        return None
    sel = int(row.get("selected_folds", 0) or 0)
    return (
        f"It held up in {sel} of {folds} re-checks, each one leaving out a different match of "
        f"{possessive(player)}."
    )


def flags(row: pd.Series) -> list[str]:
    """The warnings a reader must not miss, in plain words. Order: weakest claim first."""
    out = []
    if bool(row.get("candidate", True)) and borderline(row):
        out.append("Too close to call: possible, not confident.")
    if bool(row.get("tentative", tentative(row))):
        out.append("Early sign: not enough rallies to be sure.")
    if int(row.get("folds", 0) or 0) and not is_stable(row):
        out.append("Came and went between re-checks: a lead, not a finding.")
    return out


# ---------------------------------------------------------------------------------------
# Habits, predictability, openings
# ---------------------------------------------------------------------------------------


def situation_words(sit: str, poss: str) -> str:
    """'clear -> rear_bh' -> 'a clear to Axelsen's back backhand corner'; '-> any' -> 'a clear,
    wherever it lands'."""
    shot, _, zone = sit.partition(" -> ")
    if zone == "any":
        return f"{a_shot(shot)}, wherever it lands"
    return f"{a_shot(shot)} {at_area(zone, poss)}"


def reply_verb(reply: str) -> str:
    """'smash -> mid_fh' -> 'smashes to the opponent's middle of the court, forehand side'."""
    shot, _, zone = reply.partition(" -> ")
    verb = shot_verb3(shot)
    return f"{verb} {at_area(zone, 'the opponent' + chr(39) + 's')}" if zone else verb


def reply_noun(reply: str) -> str:
    """'smash -> mid_fh' -> 'a smash to the opponent's middle of the court, forehand side'."""
    shot, _, zone = reply.partition(" -> ")
    return (
        f"{a_shot(shot)} {at_area(zone, 'the opponent' + chr(39) + 's')}" if zone else a_shot(shot)
    )


def habit_sentence(row: pd.Series, player: str) -> str:
    me, poss = surname(player), possessive(player)
    f1, f2 = freq_pair(float(row.rate), float(row.ref_rate))
    return (
        f"After {situation_words(row.situation, poss)}, {me} {reply_verb(row.reply)} {f1}. "
        f"Most pros do it {f2}."
    )


def effective(entropy_bits: float) -> int:
    """2^entropy rounded: 'about this many different shots'."""
    return int(round(2 ** float(entropy_bits)))


def predictability_sentence(row: pd.Series, player: str) -> str:
    me, poss = surname(player), possessive(player)
    mine, ref = effective(row.entropy_bits), effective(row.ref_entropy_bits)
    lead = (
        "Easy to read: "
        if bool(row.more_predictable)
        else "Hard to read: "
        if bool(row.less_predictable)
        else ""
    )
    return (
        f"{lead}after {situation_words(row.situation, poss)}, {me} usually plays one of about "
        f"{mine} shots. Most pros mix between about {ref}. Most often: "
        f"{reply_noun(row.top_reply)} ({whole_pct(float(row.top_share))})."
    )


def sequence_words(seq: str, player: str) -> str:
    """'P:short_service > O:net > P:lob' -> 'Axelsen serves short, the opponent plays a net
    shot, Axelsen lobs'."""
    me = surname(player)
    parts = []
    for tok in seq.split(" > "):
        who, _, shot = tok.partition(":")
        parts.append(f"{me if who == 'P' else 'the opponent'} {shot_verb3(shot)}")
    return ", ".join(parts)


def set_play_sentence(row: pd.Series, player: str, serving: bool) -> str:
    me = surname(player)
    role = "serves" if serving else "receives"
    f1, f2 = freq_pair(float(row.rate), float(row.ref_rate))
    text = (
        f"When {me} {role}, {f1} the rally starts like this: {sequence_words(row.sequence, player)}. "
        f"Most pros start that way {f2}."
    )
    if row.get("ref_win_rate") is not None and not pd.isna(row.get("ref_win_rate")):
        text += (
            f" {me} wins {whole_pct(float(row.win_rate))} of those rallies; "
            f"most pros win {whole_pct(float(row.ref_win_rate))}."
        )
    return text


# ---------------------------------------------------------------------------------------
# Movement and finishing
# ---------------------------------------------------------------------------------------


def base_sentence(player: str, depth: float, lat_fh: float, ref_min: float, ref_max: float) -> str:
    """lat_fh: metres toward the player's forehand side (already hand-corrected)."""
    me = surname(player)
    if abs(lat_fh) < 0.15:
        side = "right in the middle"
    else:
        hand = "forehand" if lat_fh > 0 else "backhand"
        side = f"{'a little' if abs(lat_fh) < 0.4 else 'well'} toward the {hand} side"
    return (
        f"{me} usually waits about {metres_words(depth)} from the net, {side}. "
        f"Most pros wait between {metres_words(ref_min)} and {metres_words(ref_max)} from the net."
    )


def mean_sentence(row: pd.Series, player: str, kind: str) -> str:
    """kind: 'pull' (label = incoming shot), 'distance' (per rally), 'per_hit' (per own stroke)."""
    me = surname(player)
    mean, delta = float(row["mean"]), float(row.delta)
    if kind == "pull":
        head = f"{_cap(a_shot(str(row.label)))} pulls {me} about {metres_words(mean)} from base"
    elif kind == "distance":
        head = f"In {row.label}, {me} covers about {metres_words(mean)} per rally"
    else:
        head = f"In {row.label}, {me} moves about {metres_words(mean)} per shot"
    if bool(row.get("signal")) and abs(delta) >= 0.005:
        more = "more" if delta > 0 else "less"
        return f"{head}, {cm(delta)} {more} than most pros."
    return f"{head}, about the same as most pros."


def finishing_sentence(row: pd.Series, player: str) -> str:
    poss = possessive(player)
    what = f"{poss} {shots(str(row.label))}"
    if bool(row.get("signal")) and row.delta is not None and not pd.isna(row.delta):
        how = "more often" if float(row.delta) > 0 else "less often"
        return f"When {what} end the rally, they are winners rather than mistakes {how} than most pros'."
    return f"When {what} end the rally, they are winners rather than mistakes about as often as most pros'."


def coin_flip_note() -> str:
    return (
        "We also tried to predict who wins a rally from the shots and positions while it is "
        "still going. It did not work: the model did no better than a coin flip. We say so "
        "instead of hiding it."
    )
