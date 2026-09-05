# Setup

Five steps, about 20 minutes total. Do them in order — each one builds on the last.

You'll create two credentials yourself (a Gmail app password and a GitHub token). Never
paste either one into a chat, an email, or a file in this repository. They go only into the
places named below.

---

## 1 · Turn on GitHub Pages

This is what makes the app reachable from your phone.

1. Go to **https://github.com/rfiagbe/MY-HOME-MAINTENANCE-HUB/settings/pages**
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. That's it — no other options to set.

Then open the **Actions** tab. A workflow called *Deploy to GitHub Pages* should be running
(or you can start it manually with **Run workflow**). When it finishes, your app is live at:

```
https://rfiagbe.github.io/MY-HOME-MAINTENANCE-HUB/
```

Open that link. You should see the dashboard with tasks in it. At this point the app is
**read-only** — check-offs won't persist yet. Step 3 fixes that.

---

## 2 · Set up reminder emails

### 2a. Create a Gmail app password

The Action needs to log into a Gmail account to send mail. Use **1940nobledrive@gmail.com**
itself, or any Gmail account you control — mail will arrive at 1940nobledrive@gmail.com
either way.

1. Sign in to that Google account.
2. Go to **https://myaccount.google.com/security** and turn on **2-Step Verification** if it
   isn't already on. Google will not offer app passwords without it.
3. Go to **https://myaccount.google.com/apppasswords**
4. Name it `Home Maintenance Hub` and click **Create**.
5. Google shows a **16-character password** like `abcd efgh ijkl mnop`. Copy it now — it is
   shown exactly once. The spaces don't matter.

### 2b. Add it as repository secrets

Go to **https://github.com/rfiagbe/MY-HOME-MAINTENANCE-HUB/settings/secrets/actions**
and click **New repository secret** three times:

| Name | Value |
|---|---|
| `GMAIL_USER` | the full Gmail address doing the sending, e.g. `1940nobledrive@gmail.com` |
| `GMAIL_APP_PASSWORD` | the 16-character app password from step 2a |
| `REMINDER_TO` | `1940nobledrive@gmail.com` |

Secrets are encrypted and are never visible again after you save them — not to you, not in
logs, not to anyone with read access to the repo.

### 2c. Test it

1. Go to the **Actions** tab → **Maintenance reminders** → **Run workflow**.
2. Tick **Send even if nothing is due**, leave dry-run off, and run it.
3. Check 1940nobledrive@gmail.com within a minute or two.

If it fails, open the run's log. `Username and Password not accepted` almost always means
2-Step Verification isn't on, or the app password was mistyped.

**From then on it runs by itself, every day at 8am Eastern.** You'll get an email when
something is due in 7 days, when something is due that day, and a Monday digest if anything
has slipped. Quiet days send nothing.

---

## 3 · Connect the app so check-offs save

Without this the app can display data but can't write it back.

### 3a. Create a fine-grained token

1. Go to **https://github.com/settings/personal-access-tokens/new**
2. **Token name:** `Home Maintenance Hub`
3. **Expiration:** 1 year (calendar a reminder to renew — or choose *No expiration* if you'd
   rather not think about it)
4. **Repository access:** choose **Only select repositories**, then pick
   `MY-HOME-MAINTENANCE-HUB` — and nothing else.
5. **Permissions → Repository permissions:** find **Contents** and set it to
   **Read and write**. Leave every other permission alone.
6. **Generate token**, then copy the `github_pat_…` string. It's shown once.

This token can only read and write files in this one repository. It cannot touch your other
repos, your account settings, or anything else.

### 3b. Paste it into the app

1. Open `https://rfiagbe.github.io/MY-HOME-MAINTENANCE-HUB/` on the device you want to use.
2. Go to the **Settings** tab.
3. Fill in:
   - **Repository:** `rfiagbe/MY-HOME-MAINTENANCE-HUB` (may already be filled in)
   - **Branch:** `main`
   - **Token:** paste it
4. Tap **Save & connect**. The pill in the top-right should turn green and read **Synced**.
5. Tap **Test connection** to confirm it reports write access.

Now every check-off commits straight to `data/` in the repo.

### 3c. Using more than one device

Repeat 3a and 3b on each device. A token isn't tied to a device, so one token *would* work
everywhere — but **make a separate token per device** and name them accordingly
(`Home Hub — Phone`, `Home Hub — PC`). Revocation is the reason: lose the phone, revoke that
one token, and everything else keeps working. With a shared token you'd have to revoke it
everywhere and re-paste on every device.

Devices don't overwrite each other. Every change is stamped with the time it was made, and
when two devices have both written, the app merges them: completion history is unioned, and
for each individual task whichever side was edited more recently wins. Checking off different
tasks on your phone and your PC keeps both. The app also re-reads the repo whenever you
switch back to it, so you see the other device's work without pressing anything.

---

## 4 · Put it on your phone's home screen

**iPhone (Safari — it must be Safari, not Chrome):**
Open the site → tap the **Share** button → **Add to Home Screen** → **Add**.

**Android (Chrome):**
Open the site → **⋮** menu → **Add to Home screen** / **Install app**.

It gets its own icon and opens without browser chrome, like a native app.

---

## 5 · First things to actually do

The app is seeded with real deadlines. A few are time-sensitive right now:

| Task | Why now |
|---|---|
| **Locate and label the main water shutoff** | Ten minutes. Do it before you need it. |
| **Register Goodman + Natural Air warranty** | Registration windows are often 60 days from install. Confirm where you stand. |
| **Register all appliance warranties** | LG, Samsung, State — and record every model/serial number while you're at it. |
| **Get a wind mitigation inspection** | ~$125 once, often $500–1,500/year off a Florida premium on a new build. |
| **File the Florida Homestead Exemption** | Hard deadline **March 1, 2027**. Scheduled for January so a paperwork problem doesn't cost you the year. Update your driver's license to this address first. |
| **★ 11-month builder warranty inspection** | Scheduled for **May 28, 2027**. Your 1-year workmanship warranty ends **July 28, 2027**. This is the single highest-value item in the app. |

Open **Settings → Home notes** and fill in your HVAC filter size, model and serial numbers,
and contractor phone numbers. You will want them at an inconvenient moment.

---

## Troubleshooting

**The site 404s.** The Pages deploy hasn't finished, or Source isn't set to *GitHub Actions*.
Check the Actions tab.

**Check-offs don't stick / pill says "Local".** The token isn't saved or lacks write access.
Settings → **Test connection** will say which.

**"Save failed (409)".** Two devices edited at once. The app re-reads and retries
automatically; if it still fails, tap **Pull latest from GitHub** and redo the last change.

**No reminder emails.** Run the workflow manually with **Send even if nothing is due** to
separate "nothing was due" from "sending is broken". Also note GitHub disables scheduled
workflows in repositories with no activity for 60 days — any commit re-enables them, and
using the app commits.

**The app shows old data after a check-off.** Pages redeploys on every commit, which takes a
minute. The app reads through the GitHub API rather than the deployed files, so tap **⟳** in
the header if something looks stale.
