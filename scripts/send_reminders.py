#!/usr/bin/env python3
"""
Daily maintenance reminder mailer.

Run by .github/workflows/reminders.yml once a day. Reads data/tasks.json and
emails:

  * tasks due in exactly 7 days  ("heads up")
  * tasks due today             ("do it today")
  * overdue tasks               (only alongside the above, or as a Monday digest,
                                 so you don't get nagged every single morning)

Nothing to report means no email is sent.

Environment:
  GMAIL_USER          Gmail address that sends the mail        (required)
  GMAIL_APP_PASSWORD  16-char Google app password              (required)
  REMINDER_TO         Override recipient (default: tasks.json) (optional)
  GITHUB_REPOSITORY   owner/repo, set automatically by Actions (optional)
  TIMEZONE            IANA zone, default America/New_York      (optional)

Flags:
  --dry-run   print the email to stdout instead of sending
  --force     send even if there is nothing due
"""

import json
import os
import smtplib
import sys
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TASKS_PATH = os.path.join(ROOT, "data", "tasks.json")

LOOKAHEAD_DAYS = 7
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def local_today():
    tzname = os.environ.get("TIMEZONE", "America/New_York")
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(tzname)).date()
        except Exception:
            pass
    return date.today()


def parse_day(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def app_url():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return "https://{}.github.io/{}/".format(owner.lower(), name)
    return ""


def is_active(task, features):
    if task.get("enabled") is False:
        return False
    req = task.get("requires")
    if req and not features.get(req):
        return False
    if (task.get("schedule") or {}).get("type") == "once" and task.get("lastCompleted"):
        return False
    return True


def sort_key(t):
    return (PRIORITY_ORDER.get(t.get("priority"), 2), t.get("nextDue") or "", t.get("title", ""))


def human_date(d):
    return d.strftime("%a %b %-d") if os.name != "nt" else d.strftime("%a %b %d")


def money(n):
    n = float(n or 0)
    return "free" if n <= 0 else "~${:,.0f}".format(n)


# --------------------------------------------------------------------------
# Email building
# --------------------------------------------------------------------------
CSS_CARD = (
    "border:1px solid #dfe3e1;border-left:4px solid {accent};border-radius:10px;"
    "padding:12px 14px;margin:0 0 10px;background:#ffffff;"
)

ACCENTS = {"critical": "#b91c1c", "high": "#b45309", "normal": "#0f766e", "low": "#c8cfcc"}


def render_task_html(t, today):
    due = parse_day(t.get("nextDue"))
    delta = (due - today).days if due else 0
    if delta < 0:
        when = '<span style="color:#b91c1c;font-weight:700">{} day{} overdue</span>'.format(
            -delta, "" if -delta == 1 else "s")
    elif delta == 0:
        when = '<span style="color:#b45309;font-weight:700">Due today</span>'
    else:
        when = '<span style="color:#1d4ed8;font-weight:600">Due {}</span>'.format(human_date(due))

    bits = [
        t.get("category", ""),
        "~{} min".format(t.get("estMinutes", 15)),
        money(t.get("estCost")),
    ]
    if t.get("diy") is False:
        bits.append("hire a pro")

    html = '<div style="{}">'.format(CSS_CARD.format(accent=ACCENTS.get(t.get("priority"), "#0f766e")))
    html += '<div style="font-size:15px;font-weight:650;color:#16211e;line-height:1.35">{}</div>'.format(
        esc(t.get("title", "")))
    html += '<div style="font-size:12px;color:#5b6b66;margin-top:5px">{} &middot; {}</div>'.format(
        when, " &middot; ".join(esc(b) for b in bits if b))
    if t.get("priority") in ("critical", "high") and t.get("why"):
        why = t["why"]
        if len(why) > 240:
            why = why[:237].rsplit(" ", 1)[0] + "…"
        html += ('<div style="font-size:12.5px;color:#0b5952;background:#d7efec;border-radius:7px;'
                 'padding:8px 10px;margin-top:8px;line-height:1.5">{}</div>').format(esc(why))
    html += "</div>"
    return html


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def section_html(title, subtitle, tasks, today):
    if not tasks:
        return ""
    h = '<h2 style="font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:#5b6b66;' \
        'margin:22px 0 4px">{} ({})</h2>'.format(esc(title), len(tasks))
    if subtitle:
        h += '<p style="font-size:12px;color:#8b9a95;margin:0 0 10px">{}</p>'.format(esc(subtitle))
    for t in tasks:
        h += render_task_html(t, today)
    return h


def build_html(today, overdue, due_today, due_soon, home, url):
    name = home.get("nickname") or "your home"
    total = len(overdue) + len(due_today) + len(due_soon)

    h = ('<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,Arial,sans-serif;'
         'background:#f6f7f6;padding:20px 12px;margin:0">'
         '<div style="max-width:620px;margin:0 auto">')

    h += ('<div style="background:#0f766e;color:#ffffff;border-radius:12px;padding:18px 20px;margin-bottom:6px">'
          '<div style="font-size:19px;font-weight:700">🏡 Home Maintenance</div>'
          '<div style="font-size:13px;opacity:.9;margin-top:3px">{} &middot; {}</div>'
          "</div>").format(esc(name), esc(today.strftime("%A, %B %d, %Y")))

    lead = []
    if due_today:
        lead.append("{} due today".format(len(due_today)))
    if due_soon:
        lead.append("{} due in a week".format(len(due_soon)))
    if overdue:
        lead.append("{} overdue".format(len(overdue)))
    h += '<p style="font-size:13.5px;color:#5b6b66;margin:14px 2px 0">{}.</p>'.format(
        esc(", ".join(lead).capitalize() if lead else "{} item(s)".format(total)))

    h += section_html("Overdue", "These have slipped past their date.", overdue, today)
    h += section_html("Due today", "", due_today, today)
    h += section_html("Coming up in 7 days", "Heads up so you can plan or book someone.", due_soon, today)

    if url:
        h += ('<div style="text-align:center;margin:26px 0 8px">'
              '<a href="{}" style="display:inline-block;background:#0f766e;color:#ffffff;'
              'text-decoration:none;font-weight:650;font-size:14px;padding:12px 22px;border-radius:9px">'
              "Open the dashboard</a></div>").format(esc(url))

    h += ('<p style="font-size:11px;color:#8b9a95;text-align:center;margin:18px 2px 0;line-height:1.6">'
          "Sent automatically by your Home Maintenance Hub.<br>"
          "Tick tasks off in the app and the schedule updates itself."
          "</p>")
    h += "</div></div>"
    return h


def build_text(today, overdue, due_today, due_soon, url):
    lines = ["HOME MAINTENANCE - " + today.strftime("%A, %B %d, %Y"), ""]

    def block(title, tasks):
        if not tasks:
            return
        lines.append(title.upper() + " (%d)" % len(tasks))
        for t in tasks:
            due = parse_day(t.get("nextDue"))
            d = (due - today).days if due else 0
            if d < 0:
                w = "%d days overdue" % -d
            elif d == 0:
                w = "due today"
            else:
                w = "due %s" % due.isoformat()
            lines.append("  - %s [%s, %s, ~%s min]" % (
                t.get("title", ""), w, t.get("category", ""), t.get("estMinutes", 15)))
        lines.append("")

    block("Overdue", overdue)
    block("Due today", due_today)
    block("Coming up in 7 days", due_soon)
    if url:
        lines.append("Dashboard: " + url)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    if not os.path.exists(TASKS_PATH):
        print("::error::data/tasks.json not found", file=sys.stderr)
        return 1

    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        doc = json.load(f)

    home = doc.get("home", {})
    features = home.get("features", {})
    today = local_today()

    overdue, due_today, due_soon = [], [], []
    for t in doc.get("tasks", []):
        if not is_active(t, features):
            continue
        due = parse_day(t.get("nextDue"))
        if not due:
            continue
        delta = (due - today).days
        if delta < 0:
            overdue.append(t)
        elif delta == 0:
            due_today.append(t)
        elif delta == LOOKAHEAD_DAYS:
            due_soon.append(t)

    for lst in (overdue, due_today, due_soon):
        lst.sort(key=sort_key)

    # Don't nag about overdue items every single day. Include them when there's
    # already a reason to write, or once a week on Monday as a digest.
    is_monday = today.weekday() == 0
    if not (due_today or due_soon) and not is_monday:
        overdue = []

    if not (overdue or due_today or due_soon) and not force:
        print("Nothing due. No email sent. ({})".format(today.isoformat()))
        return 0

    to_addr = (os.environ.get("REMINDER_TO") or home.get("reminderEmail") or "").strip()
    user = (os.environ.get("GMAIL_USER") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()

    url = app_url()
    html = build_html(today, overdue, due_today, due_soon, home, url)
    text = build_text(today, overdue, due_today, due_soon, url)

    subject_bits = []
    if due_today:
        subject_bits.append("{} due today".format(len(due_today)))
    if overdue:
        subject_bits.append("{} overdue".format(len(overdue)))
    if due_soon:
        subject_bits.append("{} in 7 days".format(len(due_soon)))
    subject = "🏡 Home maintenance: " + ", ".join(subject_bits) if subject_bits else "🏡 Home maintenance check-in"

    if dry:
        print("SUBJECT:", subject)
        print("TO:", to_addr or "(unset)")
        print()
        print(text)
        return 0

    if not to_addr:
        print("::error::No recipient. Set REMINDER_TO or home.reminderEmail in data/tasks.json.", file=sys.stderr)
        return 1
    if not user or not pw:
        print("::error::GMAIL_USER and GMAIL_APP_PASSWORD secrets are not set.", file=sys.stderr)
        return 1

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Home Maintenance Hub", user))
    msg["To"] = to_addr
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.login(user, pw)
        s.send_message(msg)

    print("Sent to {}: {}".format(to_addr, subject))
    return 0


if __name__ == "__main__":
    sys.exit(main())
