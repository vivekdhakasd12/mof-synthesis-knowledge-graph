# Supervisor report follow-up email, draft (2026-09-11)

**To:** Prof. Dr. Mehrdad Jalali (`mehrdad.jalali@srh.de`)
**From:** Devendra Singh Dhakad (`dhakadvivu5@gmail.com`)
**Subject:** Case Study 2 report: full draft attached, 4 days to submission (Devendra Singh Dhakad, 100004684)
**Attachment:** `docs/report/report.pdf` (42 pages)
**Send window:** today, 2026-09-11. Submission is 2026-09-15, so anything later leaves him no room to reply.

He writes one-liners, so the email is built to be answerable in one: the ask is in the first
two sentences, and each flagged item is short enough to approve or object to in a few words.

---

## Body

Dear Prof. Dr. Jalali,

My Case Study 2 report is finished in draft and attached, 42 pages. I will submit on
15 September regardless, so please do not feel obliged to read it in full. If there is
anything you want changed before then, I would be grateful to hear it this week.

Three things I would rather flag than have you find:

1. **RQ3 is not answered.** The per-record agreement against DigiMOF and SynMOF could not be
   computed: both are keyed by CSD refcode, my corpus by DOI and by the MOF name the paper
   uses, and joining them needs a licensed mapping. I report it as unanswered with the
   reason stated. What I could measure is that the two reference databases agree with each
   other on the metal 98.9 percent of the time across the 509 MOFs they share.

2. **Accuracy is below the target in the exposé.** The best configuration reaches 0.364
   micro-F1 against the 0.80 I proposed, or about 0.53 once one field is excluded whose
   scores reflect an annotation granularity mismatch rather than extraction quality.
   Chapter 7 separates how much of the remaining gap is measurement rather than extraction.

3. **Two scope changes, both disclosed in the report.** The gold standard is 100
   hand-annotated passages rather than 150 to 200, because annotation hours were the binding
   constraint. The open-weight model is qwen3.8-27b rather than Llama-3, which the hosting
   provider retired before the runs.

One question, if you have a moment: does the module require a declaration on the use of AI
assistance, and is there a prescribed form or wording? I would like to include it correctly.

I am happy to call or come by at short notice this week if that is easier than writing.

With kind regards,

Devendra Singh Dhakad
M.Sc. Data Science and AI
Matriculation number: 100004684
SRH University of Applied Sciences Heidelberg

---

## Shorter alternative

Use this if you would rather not put three flags in front of him and would prefer he simply
looks. It keeps the AI-disclosure question, which is the one thing only he can answer.

> Dear Prof. Dr. Jalali,
>
> My Case Study 2 report is finished in draft and attached, 42 pages. I submit on
> 15 September and will do so regardless, but if there is anything you would like changed
> before then, I would be glad to hear it this week.
>
> Two things worth knowing up front: RQ3, the per-record comparison against DigiMOF and
> SynMOF, could not be answered because the databases are keyed by CSD refcode and my corpus
> by DOI, and the accuracy reached is below the target in the exposé, at 0.364 micro-F1. Both
> are set out with their reasons in the report.
>
> One question: does the module require a declaration on the use of AI assistance, and is
> there a prescribed wording?
>
> Happy to call this week if that is easier.
>
> With kind regards,
> Devendra Singh Dhakad
> M.Sc. Data Science and AI, matriculation 100004684

---

## Pre-send checklist

- [ ] **Rebuild the report first** if anything changed since 2026-09-03:
      `python docs/report/build_report.py`, then confirm `pdfinfo docs/report/report.pdf`
      still reports 42 pages and the page count in the email matches.
- [ ] Open `docs/report/report.pdf` and check page 1: orange SRH logo, your name,
      matriculation 100004684, and "September 2026".
- [ ] **Attach the PDF.** Do not send a link to the GitHub repository as the primary
      artefact; attach the file.
- [ ] Reply inside the existing thread if one is still open, so he has the context.
- [ ] Decide on the AI-disclosure question. Keep it unless you have already found the answer
      in the module handbook. Asking is better than guessing, and it is a question he can
      answer in four words.
- [ ] Verify the three flagged numbers are still current against the report: 0.364, 98.9
      percent on 509 MOFs, 100 annotated passages.
- [ ] Log the send date and anything he replies in `PROGRESS.md`.

## Notes on what this email deliberately does not do

- **It does not ask him to review 42 pages in 4 days.** That request would go unanswered.
  It tells him the submission is happening on time and invites objections only.
- **It does not hide the two deviations from the approved exposé.** RQ3 and the accuracy
  target were both headline commitments in the exposé he approved. A supervisor who finds
  those at grading time reacts worse than one who was told.
- **It does not ask for an extension or for funding.** Neither is live.
