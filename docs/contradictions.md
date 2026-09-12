# Intentional Contradictions

These are deliberate conflicts in the **synthetic evaluation corpus**. They are not claims
that the official RGPV ordinances contain these contradictions.

## C001 — Medical attendance threshold

- `corpus/academic_regulations.md`, Section 4.8: approved medical exemption requires at least **60%** attendance.
- `corpus/attendance_policy.md`, Section 4.4: approved medical exemption requires at least **65%** attendance.
- Expected state for a question asking which threshold applies to the same medical-exemption scenario: `CONTRADICTION`.

## C002 — Improvement attempts

- `corpus/academic_regulations.md`, Section 7.7: improvement is allowed in a maximum of **three** subjects.
- `corpus/examination_policy.md`, Section 5.2: improvement is allowed in a maximum of **two** subjects.
- Expected state for a question asking for the applicable maximum under the same conditions: `CONTRADICTION`.

## C003 — Semester tuition deadline

- `corpus/fee_deadlines.md`, fee table / Section 2.1: normal semester tuition deadline is **15 July**.
- `corpus/fee_deadlines.md`, Section 3.1: semester tuition is stated to be due by **31 July**.
- Expected state for a question asking for the final normal deadline when both provisions are in scope: `CONTRADICTION`.

## Important scope note

The two official RGPV PDFs in this repository are historical regulations for different
admission periods. Differences between them are not automatically counted as planted
contradictions. The evaluation should distinguish version/cohort applicability from a
true simultaneous conflict.
