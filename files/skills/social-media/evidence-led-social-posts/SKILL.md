---
name: evidence-led-social-posts
description: Research, draft, and package high-performing social posts using account history, creator-style references, topic outliers, and verifiable claims. Use for X/Twitter launch posts, comparison posts, video announcements, rankings, and threads.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [social-media, x, twitter, writing, research, outliers, launches, copywriting]
---

# Evidence-led social posts

Create social posts from current evidence rather than generic copywriting formulas. The goal is a sharp, credible post that fits the user's established voice and gives the attached artifact a clear reason to exist.

## Trigger conditions

Use this skill when the user asks for:

- X/Twitter post or thread ideas
- launch, comparison, ranking, or announcement copy
- copy modeled on a creator's style
- outlier research before drafting
- a post promoting a video, benchmark, experiment, or product

For X research and account access, load `xurl` first. For the final anti-slop pass, load `humanizer` when available.

## Workflow

### 1. Establish the factual spine

Extract only claims supported by the user's results or current source material:

- what was tested
- number of subjects or products
- whether conditions were comparable
- concrete tasks or use cases
- winner, runner-up, and surprise
- strongest caveat or close call
- attached asset and desired action

Do not invent test rigor, prices, speed measurements, dates, access conditions, or rankings. If the user supplies a ranking, preserve it unless live evidence contradicts it.

### 2. Research the original sources

When the user gives an account, creator, post URL, or topic, inspect that source directly. Do not substitute session history for the current X timeline.

Collect three evidence sets:

1. **User voice:** recent original posts, especially posts on the same topic.
2. **Reference creator:** recent original posts from the named creator.
3. **Topic outliers:** relevant posts from the current news window.

Exclude replies and reposts where possible. Capture post text, date, impressions, likes, replies, reposts, quotes, and bookmarks.

### 3. Identify outliers correctly

Do not rank posts by likes alone. For a quick within-account comparison, use a weighted engagement signal:

```text
likes + replies + 2*reposts + 2*quotes + 3*bookmarks
```

Compute an outlier multiple against that account or query's median. Treat this as a heuristic, not a universal quality score. Also inspect impressions and bookmark rate because useful long-form posts often earn saves rather than replies.

Never compare raw engagement between a huge creator and a smaller user without normalizing. Learn structural patterns from the larger creator, not expected reach.

### 4. Extract structure, not imitation

From a reference creator, identify reusable mechanics:

- first-line hook type
- proof or authority placement
- specificity and numbers
- pacing and line breaks
- reveal timing
- use of lists
- ending and call to action
- relationship between post copy and attached media

Do not copy signature phrasing, capitalization habits, or entire sentence structures. State that the draft uses structural patterns rather than impersonating the creator.

### 5. Choose one dominant narrative

A strong post needs one central story. Useful patterns include:

- **Reversal:** “I thought X won. Then Y arrived.”
- **Controlled experiment:** “I gave N subjects the same task.”
- **Unexpected podium:** expected winner, close second, surprise third.
- **Contrarian observation:** the common evaluation method misses what matters.
- **Practical verdict:** best overall, fastest, best value, or best for a defined job.

Do not turn a post into release-note soup. Put the full lineup, methodology, and caveats in a first reply or thread when they weaken the opening.

### 6. Separate the hooks across title, post, and media

If a video title or thumbnail already carries the winner or reversal, the post should add proof, personality, or mechanism rather than repeat the same sentence.

A useful division is:

- post: narrative or personal reversal
- thumbnail/image: visual proof or experiment scale
- video title/link: explicit payoff
- first reply: full methodology, lineup, and discussion question

### 7. Draft distinct options

Produce 3 to 5 genuinely different directions, not cosmetic rewrites:

- recommended narrative version
- shorter version
- contrarian version
- creator-inspired structural version
- reply-oriented version when appropriate

Lead with the recommended draft and explain the choice briefly. Keep X posts within the user's actual account limits when known. Use a character counter rather than guessing.

### 8. Humanize and verify

Before delivery:

- read the copy aloud
- remove generic AI claims such as “changes everything” or “the landscape shifted”
- remove unnecessary hashtags and company-tag piles
- preserve natural contractions and imperfect rhythm
- check every proper noun and model spelling
- verify rankings and numbers
- confirm that superlatives are scoped, for example “best overall in my Hermes test” rather than “best model in the world”
- do not use em dashes for users who prohibit them

## Recommended output format

1. **Best post** ready to paste
2. **Why this angle** in 2 to 4 bullets
3. **Alternative versions** with clearly different hooks
4. **Suggested first reply** for methodology, full lineup, or a question
5. **Research signal** listing the few outlier patterns that materially affected the copy
6. **Confidence** label

Do not bury the paste-ready copy beneath a long research report.

## Pitfalls

- Generic “latest models this week” framing has no conflict or payoff.
- Listing every product in the opener creates metadata soup.
- A ranking without test mechanism feels arbitrary.
- Saying “destroyed” when results were close harms credibility.
- Copying a creator's voice too literally becomes impersonation.
- Raw likes are not an outlier analysis.
- Search results may contain engagement bait or fabricated claims. Use them as style signals only unless independently verified.
- Do not post, reply, quote, or upload media without the user's explicit approval.

## Supporting references

- See `references/ai-model-comparison-posts.md` for the reusable research findings and post structures from frontier-model comparison launches.
