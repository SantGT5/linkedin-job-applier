import { logKind } from "./logLine";

test.each([
  ["________________", "divider"],
  ["[Waiting for you] Help Needed: Couldn't answer", "you"],
  ['Trying to Apply to "Dev | Acme" job. Job ID: 1', "job"],
  ['>>>> Now searching for "Go" <<<<', "heading"],
  ['Saved debug page "Easy Apply page - Contact" (https://x).', "debug"],
  ["AI job match score: 80/100 (threshold 60). Reason: good fit", "ai"],
  ["Failed to Easy apply!", "error"],
  ["Couldn't find the location button on the results page.", "error"],
  ['Skipping "Dev | Acme": Contains bad word "Senior".', "skip"],
  ['Already applied to "Dev | Acme" job. Job ID: 1!', "skip"],
  ['Successfully saved "Dev | Acme" job. Job ID: 1 info', "success"],
  ["Answered 4 question(s).", "success"],
  ['Details of "Dev | Acme" job did not load, skipping it. Job ID: 1!', "skip"],
  ["Found 25 jobs on page 1.", "plain"],
])("%s → %s", (text, kind) => {
  expect(logKind(text)).toBe(kind);
});
