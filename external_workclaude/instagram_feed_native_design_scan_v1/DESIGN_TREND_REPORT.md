# Design Trend Report — Instagram Feed-Native Design Scan V1

All patterns below are `CANDIDATE` only. None are `VERIFIED`, `PROVEN`, `PROMOTED`, or supported by
causal performance claims — engagement numbers are cited as observational context, not proof of
what caused them.

## Pattern candidates

### 1. Dark gradient/neon typographic cover, no photography
**Accounts:** `click.wave.company`, `qjc.ai`, `mktg.with.ai`
**Description:** Near-black to dark-gradient background, bold white/neon-accent headline text, no
stock photography or illustration — pure typography plus a color gradient or radial glow. Often
paired with urgency-driven copy ("이젠 무조건 쓰셔야 합니다", "생존하지 못합니다") and/or an explicit
in-image swipe CTA button ("다음 페이지 →").
**Mapped layout:** `dark_editorial`
**Notes:** Cheapest style to produce (no photo sourcing needed). Appeared 3 times independently —
the most frequent single pattern in this sample.

### 2. Real photo + minimal text label (near-zero graphic design)
**Account:** `brandyclassic`
**Description:** A real, high-curiosity photo (a Tesla Roadster discovered after 13 years in a
shipping container) with only a small, light-weight text label — no heavy typography, no color
treatment, no branding overlay.
**Mapped layout:** `timeline`
**Notes:** This candidate had the highest engagement observed in the entire sample (648 likes),
markedly higher than every heavily-designed AI-tool cover. Worth testing whether narrative/curiosity
strength can substitute for production value in some content categories — but this is a single
data point, not a trend claim.

### 3. Bold numeral/list headline over a visually striking but topically-unrelated image
**Account:** `onnydesign`
**Description:** "무료 PNG 사이트 6" (a design-tool listicle) rendered in heavy bold white-on-blue
numerals, set against a dramatic AI-generated black panther image that has no literal connection to
the PNG-tool topic.
**Mapped layout:** `number_list`
**Notes:** Second-highest engagement in the sample (943 likes). Suggests visual pattern-interrupt
(a striking, unexpected image) may matter more than topical literalism for stopping the scroll —
again a single-account observation, not a proven mechanism.

### 4. Handwritten/notebook aesthetic + comment-to-DM CTA
**Account:** `marketer_c_`
**Description:** Blue marker handwriting on cream lined notebook paper, photographed flat-lay style
— no digital typography at all. Caption offers a free summarized PDF in exchange for any comment
("아무 댓글 남겨주시면 ... 정리해서 보내드릴게요").
**Mapped layout:** `notebook`
**Notes:** Reads as authentic/low-produced relative to the dark-editorial cluster. The
comment-for-DM-freebie CTA is a distinct, directly reusable lead-capture mechanic independent of
the visual style.

### 5. Cute mascot/pastel illustration for a dry productivity topic
**Account:** `ai.injae`
**Description:** A custom illustrated orange pixel-art mascot on a warm cream/pastel background,
paired with simple checklist icons ("이름 변경", "정리 완료"), used to soften a Claude
file-organization tutorial.
**Mapped layout:** `character_diary`
**Notes:** The only soft-pastel illustrated-mascot account in the sample; visually distinct from
the dominant dark-editorial AI-tool cluster.

### 6. News-badge + bordered headline box on a real event photo
**Accounts:** `today.incheon` (local community news), `nant.magazine` (investigative column)
**Description:** A small topic/section tag ("News", "#COLUMN") paired with a bold, often
black-bordered headline box directly over a real photo (event photo, architectural photo).
**Mapped layout:** `warning`
**Notes:** Distinct convention used by news/journalism-style accounts as opposed to marketing/AI
accounts — a small section tag builds recurring series identity ("#COLUMN") even on single-topic
posts.

### 7. Illustrated/webtoon-style commentary for gossip/tabloid content
**Account:** `yaya_look.at.this`
**Description:** A faceless illustrated avatar in a relevant costume (police uniform) over a
blurred photographic background, with heavy comic-book-style yellow-outlined black lettering.
**Mapped layout:** `warning`
**Notes:** Only illustrated/webtoon-style account observed; a visually distinct alternative to both
the dark-editorial and real-photo clusters. Content topic itself (a real scandal story) is not a
pattern to replicate — flagged as design-observation only.

### 8. Puzzle-piece brand-logo comparison metaphor
**Account:** `daglo_ai`
**Description:** Multiple competing AI-tool brand logos (Claude, Gemini) rendered as interlocking
jigsaw-puzzle pieces against a dark background, illustrating a "combine everything into one
subscription" value proposition.
**Mapped layout:** `comparison`
**Notes:** A distinctive, easily understood visual metaphor for aggregation/bundling pitches.

## Cross-cutting observations

- **Fake in-image slide counters as a hook device.** `hongik.man`'s cover included a designed-in
  "03/11"-style counter baked into the artwork itself, which did not match Instagram's actual
  5-slide carousel indicator. This is a deliberate curiosity/completionism hook worth studying as a
  technique, independent of the literal number used.
- **Comment-bait captions correlate with comment counts far exceeding likes.** Both
  `mktg.with.ai` and `click.wave.company` showed comment counts (188) roughly 5x their like counts
  (39) — consistent with, though not proof of, an explicit "comment X to receive Y" caption
  mechanic common in this account cluster.
- **AI/marketing-tool accounts dominate the dark_editorial style; non-AI accounts (local news,
  lifestyle, story-driven) lean toward real-photo-plus-minimal-text or bordered-headline styles.**
  This may simply reflect the seed account's recommendation graph rather than a platform-wide split.

## Layout mapping summary (candidate counts against the existing 10 layouts)

| Layout | Candidate count |
|---|---|
| `dark_editorial` | 4 |
| `warning` | 3 |
| `tutorial` | 3 |
| `number_list` | 2 |
| `notebook` | 1 |
| `character_diary` | 1 |
| `comparison` | 1 |
| `timeline` | 1 |
| `checklist` | 1 |
| `bold_ai` | 0 |

No candidate required an 11th layout — all 18 detailed candidates mapped cleanly onto the existing
set, though several were a judgment call between two plausible layouts (noted per-candidate in the
JSON `notes` field).
