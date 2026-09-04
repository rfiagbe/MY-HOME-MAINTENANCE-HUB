# 🏡 Home Maintenance Hub

A maintenance dashboard for a new-construction Florida home. Tracks **116 recurring and
one-time maintenance tasks**, tells you when each is due, emails you a reminder a week
before and again on the day, and keeps a permanent record of everything you've done.

Everything lives in this repository. No server, no database, no subscription.

---

## What it does

| | |
|---|---|
| **Dashboard** | Overdue, due today, next 7 days, next 30 days — plus a countdown on your builder warranty. |
| **All Tasks** | Every task, searchable and filterable. Open any one to see *why it matters* and *step-by-step how to do it*. |
| **History** | Permanent log of every completion — date, cost, DIY vs. pro, and your notes. |
| **Reports** | Completions by month, by category, schedule health, spend tracking, and what's slipping. |
| **Email reminders** | A GitHub Action runs daily and emails you 7 days out and on the due date. |
| **Phone** | Installs to your home screen as an app. Works offline. |

---

## Where the schedules come from

Every task records its own source. The schedules are not generic — they're pulled from the
manufacturers of the equipment actually in this house, then layered with Florida-specific
and new-construction requirements.

| Equipment | Key intervals |
|---|---|
| **Goodman** AC / heat pump<br>(installed by Natural Air Energy Saving Systems) | Filter every 1–3 months (tightened to 45 days for Florida's year-round load); professional tune-up at least annually, twice yearly for a heat pump; keep coils clear. Documented maintenance is expected for the 10-year parts warranty. |
| **State** water heater | Drain, flush and inspect the anode rod **after the first 6 months**, then at least annually. Operate the T&P valve annually; full T&P inspection every 2–4 years per the valve's own label. |
| **Hunter** irrigation | Check for leaks, clogged heads and worn components; adjust the schedule seasonally (Seasonal Adjust %); test the rain sensor. |
| **LG** washer | Monthly maintenance on each section: Tub Clean, dispenser drawer, gasket wiped dry. |
| **LG** dryer | Lint trap every load; moisture sensors wiped with alcohol monthly; trap housing and vent checked every 3 months; **professional exhaust cleaning annually**. |
| **LG** refrigerator | Water and air filters ~6 months; condenser coils once or twice a year. |
| **Samsung** microwave | Grease filter cleaned monthly; charcoal filter replaced every 6–12 months. |
| **Samsung** range / cooktop | Regular soft-cloth cleaning; scheduled deep clean; annual seal and calibration check. |

**Florida-specific additions** — monthly AC condensate line flush (the single most common
cause of emergency AC calls here), termite bond renewal and annual WDO inspection, hurricane
season prep in mid-May, rain sensor testing, window weep holes, lanai screen and anchor
inspection, the summer fertilizer blackout, and humidity management.

**New-construction additions** — Goodman warranty registration, the **11-month builder
warranty inspection** (the highest-value item in the whole app), written punch-list
submission, warranty expiry milestones, wind mitigation inspection for an insurance
discount, and the **Florida Homestead Exemption March 1 deadline**.

---

## Setup

See **[SETUP.md](SETUP.md)** — about 20 minutes, one time.

## Layout

```
index.html            the app
app.js  styles.css    logic and styling (no build step, no dependencies)
sw.js  manifest.webmanifest   PWA — installs to your phone's home screen
data/tasks.json       the catalog + every task's current due date  ← your data
data/history.json     permanent completion log                     ← your data
scripts/seed_tasks.py     regenerates the catalog (preserves your history)
scripts/send_reminders.py the email engine
scripts/make_icons.py     regenerates the app icons
.github/workflows/reminders.yml  daily email job
.github/workflows/deploy.yml     publishes the site to GitHub Pages
```

## Adding or changing tasks

Two ways:

- **In the app** — Settings has toggles for whole categories (pool, septic, dishwasher…),
  and every task can be individually disabled or snoozed from its detail sheet.
- **In the catalog** — edit `scripts/seed_tasks.py` and run `python scripts/seed_tasks.py`.
  Re-running is safe: it preserves `lastCompleted`, `nextDue`, notes and enabled/disabled
  state for every task that already exists, and only adds what's new.

## Privacy

The GitHub token you paste into Settings is stored in your browser's `localStorage` on that
device only. It is sent to `api.github.com` and nowhere else. Use a **fine-grained** token
scoped to this one repository with `Contents: Read and write` — nothing more. If you lose the
phone, revoke that token in GitHub settings and nothing else is affected.
