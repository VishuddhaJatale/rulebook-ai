# Evaluation Set

This is the ground-truth evaluation set for the Rulebook AI project.

## States

- `ANSWERABLE`: the corpus contains sufficient evidence to answer the question.
- `NOT_COVERED`: the corpus does not establish the requested fact.
- `CONTRADICTION`: two applicable provisions give incompatible answers.

## Current test set

- 20 answerable
- 25 not covered
- 6 contradiction
- 51 total

The 25 `NOT_COVERED` questions are deliberately plausible and adjacent to material
actually present in the corpus. They are intended to test whether the system refuses
unsupported claims rather than merely answering absurd questions.

The final evaluation runner will compare the model's machine-readable state with
`expected_state` and will separately score the 25-question not-covered subset.

## Important

Do not change expected labels to make a model look better. If a question is found to
be answerable after corpus changes, revise the corpus/question deliberately and record
the change in Git history.
