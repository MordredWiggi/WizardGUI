# Play Store metadata

Source-of-truth copies of every text field that gets pasted into Play Console.
Keeping them here means future updates start from the previous wording instead
of from scratch.

## What goes where

| File | Where in Play Console |
|---|---|
| `<locale>/title.txt` | Store listing → App name |
| `<locale>/short_description.txt` | Store listing → Short description |
| `<locale>/full_description.txt` | Store listing → Full description |
| `<locale>/release_notes.txt` | Production → Release → "What's new in this release?" |
| `privacy_policy.html` | Hosted at a public URL; the URL goes into App content → Privacy policy |
| `data_safety.md` | Reference while filling App content → Data safety |
| `content_rating.md` | Reference while filling App content → Content rating + Target audience + Ads |

## Locales

`en-US`, `de-DE`, `fr-FR`, `hi-IN` — matches the four languages the app's UI
supports ([translations.dart](../lib/i18n/translations.dart)). Add `en-US`
first in Play Console; the others are added under "Manage translations".

## Character limits (Play Console hard caps)

- Title: 30
- Short description: 80
- Full description: 4000
- Release notes: 500

All files in this folder are within their cap.

## Hindi review

The Hindi copy was drafted programmatically. Have a native speaker review
before publishing — Wizard's audience in India is small enough that you can
ship without `hi-IN` if no reviewer is available.
