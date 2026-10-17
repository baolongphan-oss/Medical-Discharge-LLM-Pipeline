# Stage 2 (v3): code-generated medication table
# Doses never pass through the LLM: this table is built in Python from the extraction.
import re

ASK = "Ask your doctor"

# (pattern, replacement) pairs; periods are optional and matching ignores case.
# Order matters: q.i.d. and q.h.s. must be checked before q.d.
FREQ_LOOKUP = [
    (r"\bb\.?i\.?d\b\.?", "2 times a day"),
    (r"\bt\.?i\.?d\b\.?", "3 times a day"),
    (r"\bq\.?i\.?d\b\.?", "4 times a day"),
    (r"\bq\.?h\.?s\b\.?", "at bedtime"),
    (r"\bq\.?d\b\.?", "1 time a day"),
    (r"\bp\.?r\.?n\b\.?", "only when you need it"),
    (r"\bp\.?o\b\.?", "by mouth"),
    (r"\bq\.?\s?(\d+)\s?(?:h|hr|hrs|hours?)\b\.?", r"every \1 hours"),  # q4h, q.4h, q.4 hours
    (r"\bou\b\.?", "both eyes"),
]

# group title -> statuses that belong in it, in display order
GROUPS = [
    ("New medicines", ["new"]),
    ("Changed medicines", ["changed"]),
    ("Keep taking", ["continued", "unknown"]),
    ("STOP taking", ["stopped"]),
]


def plain_frequency(freq):
    """Replace known abbreviations with plain words; anything unmatched stays as written."""
    for pattern, plain in FREQ_LOOKUP:
        freq = re.sub(pattern, plain, freq, flags=re.IGNORECASE)
    return freq


def render_med_table(medications):
    """Return a Markdown table of medications, grouped by status."""
    if not medications:
        return "Ask your care team which medicines to take at home."

    sections = []
    for title, statuses in GROUPS:
        meds = [m for m in medications if m.status in statuses]
        if not meds:
            continue

        if title == "STOP taking":
            # stopped medicines only need the name
            rows = ["| Medicine |", "|---|"]
            rows += [f"| {m.name} |" for m in meds]
        else:
            rows = ["| Medicine | How much | How often | How long |", "|---|---|---|---|"]
            for m in meds:
                dose = m.dose or ASK
                freq = plain_frequency(m.frequency) if m.frequency else ASK
                if m.duration:
                    duration = m.duration
                elif title == "New medicines":
                    duration = "Ask your doctor how long"
                else:
                    duration = ""
                rows.append(f"| {m.name} | {dose} | {freq} | {duration} |")

        sections.append(f"### {title}\n\n" + "\n".join(rows))

    return "\n\n".join(sections)
