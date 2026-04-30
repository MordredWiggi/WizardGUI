# Data safety form — Play Console answers

The Data safety form lives under **App content → Data safety**. The wording
of the questions changes occasionally; this file maps each section to the
answer that's accurate for Wizard.

## Section 1 — Data collection and security

| Question | Answer |
|---|---|
| Does your app collect or share any of the required user data types? | **Yes** |
| Is all of the user data collected by your app encrypted in transit? | **Yes** (HTTPS for every leaderboard upload) |
| Do you provide a way for users to request that their data is deleted? | **Yes** — by emailing `malikji@gmx.de` |

## Section 2 — Data types

For every category, mark **Collected = Yes** only for the two listed below;
all others are **No**.

We share with no third parties, so **Shared = No** for every entry.

### Personal info → Name
| Field | Value |
|---|---|
| Collected | Yes |
| Shared | No |
| Processing | Not processed ephemerally — stored on the leaderboard server until deletion is requested |
| Required or optional | Optional (the user must explicitly tap "upload") |
| Purpose | App functionality (display names on group / global leaderboards) |

### App activity → In-app actions / game progress
| Field | Value |
|---|---|
| Collected | Yes |
| Shared | No |
| Processing | Not processed ephemerally — stored alongside the player name |
| Required or optional | Optional |
| Purpose | App functionality (leaderboard rankings) |

### Everything else
For each of the categories below, the answer is **No** to *both* "Collected"
and "Shared":

- Personal info: email address, user IDs, address, phone number, race/ethnicity, political/religious info, sexual orientation, other personal info
- Financial info: any
- Health and fitness: any
- Messages: emails, SMS/MMS, other in-app messages
- Photos and videos
- Audio files: voice or sound recordings, music files, other
- Files and docs
- Calendar
- Contacts
- App activity: search history, installed apps, other user-generated content, other actions
- Web browsing
- App info and performance: crash logs, diagnostics, other
- Device or other IDs
- Location: approximate or precise

## Section 3 — Security practices

| Question | Answer |
|---|---|
| Is data encrypted in transit? | **Yes** |
| Can users request deletion? | **Yes** — via email |
| Do you follow Play's Families Policy? | **Not applicable** — app is not in the Designed-for-Families program |
| Has your app been independently validated against a security standard? | **No** |

## Section 4 — Privacy policy URL

Paste the public URL where `privacy_policy.html` is hosted (see the README in
this folder for hosting suggestions).
