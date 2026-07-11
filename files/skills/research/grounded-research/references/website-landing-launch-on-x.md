# Website / landing-page launch posts on X (session-grounded)

Condensed from a grounded pass (Composio Exa/Firecrawl/Perplexity + xurl live search + Buffer scrape + x-docs). Not a full mirror of upstream docs.

## Hard rule: links

Buffer analysis (~18.8M posts, 71k accounts; published findings used in 2025/26):

- Non-Premium posts with external links: ~0% median engagement after March 2025
- Premium link posts: still lowest ER vs text/image/video (~0.28% vs higher for native)
- Workarounds: Premium if outbound is core; **native first, link second**; **put URL in first reply**; bio link

Live xurl samples of "website is live" + naked link mostly underperformed story+media+proof posts.

## Format ladder

1. Native short video (15-45s tour) or multi-image before/after
2. Short thread (3-6; launch threads often 6-8) with proof
3. Text story without outbound URL
4. Main post with external URL (worst for organic)

X docs media caps: up to 4 photos OR 1 GIF OR 1 video per post.

## Campaign shape

Pre-launch 3-5d: problem → BTS → proof → countdown  
Launch: hero (no URL) + first-reply UTM + optional thread; pin; reply for 30-60m  
Post: feature spots, testimonials, cuts, 24h/1 week results

## Copy

Do: specific user outcome, metric/quote/before-after, one next step  
Don't: "excited to announce", naked "new site LIVE 🚀 [link]", hashtag piles

### Skeleton

Main:  
`We rebuilt [X] so [persona] can [outcome] without [pain].`  
`Biggest change: [one thing]. Before/after in media.`  
`Link in first reply.`

Reply: `https://site/?utm_source=x&utm_medium=organic&utm_campaign=site_relaunch`

## Timing

Default midweek (Tue-Thu) at audience local peak when you can engage. Saturday weak for B2B. Confirm with account analytics.

## Validation query

```bash
xurl --app hermes-x search '("new website" OR "landing page" OR redesign OR "site is live") -is:retweet lang:en' -n 25
```

Rank by public_metrics client-side. Prefer story + media + replies.

## Sources to re-scrape when stale

- https://buffer.com/resources/links-on-x/
- Monolit/Quip-style 2026 launch thread playbooks (Exa find current URLs)
- x-docs media best practices (attachment limits, not ranking)

Confidence: high on link suppression direction; moderate on exact hours; low on any single live sample as universal template.
