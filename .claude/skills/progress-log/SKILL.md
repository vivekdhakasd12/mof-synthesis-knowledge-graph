---
name: progress-log
description: Append a properly formatted end-of-session entry to PROGRESS.md, the project's rolling work log. Use this whenever the user says to update the progress log, log this session, wrap up, end the session, or record what was done — and proactively at the end of any working session in this repo, because the project's working agreement requires a PROGRESS.md entry every session. Also use it when the user asks to record a decision, status change, or supervisor interaction.
---

# progress-log

PROGRESS.md is the project's institutional memory: future sessions (and the final report's "process" section) reconstruct what happened from it. An entry that records intentions instead of events, or relative dates instead of absolute ones, is worthless three weeks later — that's the failure mode this skill exists to prevent.

## Procedure

1. Read the top entry of `PROGRESS.md` (after the 3-line intro) to get the previous session number and see the established voice.
2. Get today's date: `date +%Y-%m-%d`.
3. Insert the new entry **above** the previous top entry (newest first), directly after the intro lines.
4. Keep it 25–40 lines. If a session was tiny, a 6-line entry is fine — never pad.

## Entry template

```markdown
## YYYY-MM-DD (session N) — <short headline of what changed>

**Status:** <one paragraph: project state AFTER this session, leading with what changed since the last entry>

Done in this session:
- <concrete artifact or decision, with file paths>
- ...

Next (deadline order):
1. **<absolute date or date range>:** <action>
2. ...

Open items / risks:
- <new risks first, then carry forward any still-unresolved risks from the previous entry>
```

## Rules

- **Record what actually happened, not what was planned.** If an email was drafted but not sent, write "drafted, not sent". If a deadline was missed, say so plainly.
- **Absolute dates only** ("2026-06-21", never "next Friday" or "in two weeks").
- **Carry risks forward.** Copy unresolved risks from the previous entry (mark them "carried:"). A risk silently disappearing from the log is how risks get forgotten.
- **Next steps are deadline-ordered**, each tied to a date.
- Quote supervisor communications verbatim when they affect decisions (e.g., his "The topic is confirmed. Move forward.").
- Decisions get a one-line rationale so future readers don't relitigate them.
- Session number = previous entry's number + 1. If the same day gets two entries, they are still separate sessions.
