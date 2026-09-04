#!/usr/bin/env python3
"""
Generates data/tasks.json -- the master maintenance catalog for the home.

Re-running this is SAFE: it preserves per-task state (lastCompleted, nextDue,
enabled, notes) for any task id that already exists in data/tasks.json, and only
adds/updates the catalog definitions. Use it when you want to add new tasks.

    python scripts/seed_tasks.py

Sources for the schedules are recorded per-task in the "source" field.
"""

import json
import os
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "tasks.json")

# --------------------------------------------------------------------------
# Home profile
# --------------------------------------------------------------------------
MOVE_IN = date(2026, 7, 28)
TODAY = date.today()
if TODAY < MOVE_IN:
    TODAY = MOVE_IN

HOME = {
    "nickname": "1940 Noble Drive",
    "state": "FL",
    "moveInDate": MOVE_IN.isoformat(),
    "construction": "new",
    "reminderEmail": "1940nobledrive@gmail.com",
    "equipment": {
        "ac_installer": "Natural Air Energy Saving Systems",
        "hvac": "Goodman Air Conditioning & Heating",
        "irrigation": "Hunter Irrigation Systems",
        "water_heater": "State Water Heaters",
        "washer": "LG",
        "dryer": "LG",
        "refrigerator": "LG",
        "range": "Samsung",
        "cooktop": "Samsung",
        "microwave": "Samsung",
    },
    "features": {
        "pool": False,
        "septic": False,
        "well": False,
        "waterSoftener": False,
        "gasAppliances": False,
        "fireplace": False,
        "twoStory": False,
        "screenedLanai": True,
        "irrigation": True,
        "garage": True,
        "dishwasher": True,
    },
    "warranty": {
        "workmanship1yr": (MOVE_IN + timedelta(days=365)).isoformat(),
        "systems2yr": date(MOVE_IN.year + 2, MOVE_IN.month, MOVE_IN.day).isoformat(),
        "structural10yr": date(MOVE_IN.year + 10, MOVE_IN.month, MOVE_IN.day).isoformat(),
    },
}

# --------------------------------------------------------------------------
# Schedule helpers
# --------------------------------------------------------------------------


def every(days):
    return {"type": "interval", "days": days}


def annually(month, day):
    return {"type": "fixed", "months": [month], "day": day}


def on_months(months, day=15):
    return {"type": "fixed", "months": sorted(months), "day": day}


def once(y, m, d):
    return {"type": "once", "date": date(y, m, d).isoformat()}


def _clamp_day(y, m, d):
    if m == 2:
        leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
        return min(d, 29 if leap else 28)
    if m in (4, 6, 9, 11):
        return min(d, 30)
    return min(d, 31)


def first_due(sched, index):
    """Compute the first sensible due date, at or after TODAY."""
    t = sched["type"]

    if t == "once":
        return sched["date"]

    if t == "fixed":
        day = sched["day"]
        best = None
        for year in (TODAY.year, TODAY.year + 1):
            for m in sched["months"]:
                cand = date(year, m, _clamp_day(year, m, day))
                if cand >= TODAY and (best is None or cand < best):
                    best = cand
        return best.isoformat()

    # interval: anchor on move-in, stagger so everything doesn't pile onto one day
    days = sched["days"]
    spread = 14 if days <= 60 else 28
    offset = index % min(spread, max(days - 1, 1))
    due = MOVE_IN + timedelta(days=days + offset)
    while due < TODAY:
        due += timedelta(days=days)
    return due.isoformat()


TASKS = []


def T(tid, title, category, sched, why, steps, source,
      priority="normal", diy=True, mins=15, cost=0, equip=None, requires=None):
    TASKS.append({
        "id": tid,
        "title": title,
        "category": category,
        "equipment": equip,
        "schedule": sched,
        "priority": priority,          # critical | high | normal | low
        "diy": diy,                    # False = hire a pro
        "estMinutes": mins,
        "estCost": cost,               # USD, rough
        "why": why,
        "steps": steps,
        "source": source,
        "requires": requires,          # feature flag key in HOME.features
    })


# ==========================================================================
# HVAC  -- Goodman equipment, installed by Natural Air Energy Saving Systems
# ==========================================================================
T("hvac-filter", "Replace HVAC air filter", "HVAC", every(45),
  "Florida runs the AC nearly year-round, so filters load up fast. A clogged filter chokes airflow, "
  "can freeze the evaporator coil, drives up your power bill, and neglect can jeopardize Goodman's parts warranty.",
  ["Read the filter size printed on the edge of the old filter and save it in this task's notes.",
   "Set the thermostat to OFF so the blower isn't pulling while the slot is open.",
   "Slide the old filter out; slide the new one in with the AIRFLOW ARROW pointing toward the air handler.",
   "Turn the thermostat back on.",
   "Write today's date on the new filter's cardboard edge with a marker."],
  "Goodman: replace/clean every 1-3 months. Florida HVAC guidance tightens this to 30-60 days in high-use season.",
  priority="high", mins=10, cost=25, equip="Goodman air handler"),

T("hvac-condensate-flush", "Flush AC condensate drain line with vinegar", "HVAC", every(30),
  "This is the #1 cause of emergency AC calls in Florida. Algae slime clogs the drain, water backs up into the pan, "
  "and the safety float switch shuts your AC off in 95-degree heat -- or worse, it overflows into the ceiling.",
  ["Find the condensate drain access -- usually a capped PVC tee near the indoor air handler.",
   "Turn the system OFF at the thermostat.",
   "Remove the cap and pour in 1 cup of plain white distilled vinegar.",
   "Wait 30 minutes, then pour a little water through to confirm it drains freely.",
   "Replace the cap and turn the system back on.",
   "Also check the exterior drain outlet is dripping when the AC runs."],
  "Florida HVAC standard practice: monthly vinegar flush to prevent biological slime clogs.",
  priority="critical", mins=20, cost=3, equip="Goodman air handler"),

T("hvac-tuneup-spring", "Professional HVAC tune-up (cooling season)", "HVAC", annually(3, 10),
  "Goodman's 10-year parts warranty expects documented annual maintenance. A spring tune-up also catches a weak "
  "capacitor or low refrigerant before the first 95-degree week, which is exactly when every tech in the county is booked.",
  ["Call Natural Air Energy Saving Systems (your installer) -- ask if you're still under a free/discounted service plan.",
   "Ask them to check refrigerant charge, capacitor, contactor, amp draw, coil condition and drain line.",
   "Get the written service report -- attach or note the invoice number here.",
   "File the report; you need it if you ever make a Goodman warranty claim."],
  "Goodman: professional tune-up at least once a year; twice a year for heat pumps.",
  priority="high", diy=False, mins=90, cost=150, equip="Goodman system"),

T("hvac-tuneup-fall", "Professional HVAC check (heating season)", "HVAC", annually(10, 10),
  "If your Goodman unit is a heat pump it heats as well as cools, and Goodman asks for service twice a year -- "
  "spring for cooling, fall for heating. Even a mild Florida winter needs the reversing valve and aux heat verified.",
  ["Schedule the fall visit with Natural Air.",
   "Ask specifically for heat pump / reversing valve and auxiliary heat strip checks.",
   "Confirm the emergency heat mode works before the first cold snap.",
   "File the service report with your warranty documents."],
  "Goodman: heat pumps should be serviced twice a year (spring and fall).",
  priority="normal", diy=False, mins=90, cost=150, equip="Goodman system"),

T("hvac-condenser-clean", "Clean outdoor condenser unit", "HVAC", on_months([4, 10], 5),
  "The outdoor coil dumps your home's heat outside. Grass clippings, dryer lint and Florida pollen mat the fins, "
  "so the compressor runs hotter and longer for the same cooling.",
  ["Shut power off at the outdoor disconnect box next to the unit.",
   "Clear leaves, grass and weeds within 2 feet on all sides.",
   "Rinse the coil fins from the INSIDE out with a garden hose on gentle spray -- never a pressure washer.",
   "Straighten any bent fins with a fin comb if you have one.",
   "Restore power and confirm the unit starts normally."],
  "Goodman preventive maintenance: keep condenser coils free of dirt and debris.",
  priority="normal", mins=30, cost=0, equip="Goodman condenser"),

T("hvac-vents-clean", "Clean supply and return vents / registers", "HVAC", every(90),
  "Dusty registers throw that dust straight back into your rooms and restrict airflow, and a blocked return "
  "makes the whole system work harder.",
  ["Vacuum every supply register with a brush attachment.",
   "Pull the return grille and vacuum both sides.",
   "Wipe grilles with a damp cloth.",
   "Confirm no furniture, rugs or curtains are blocking any vent."],
  "Standard HVAC airflow maintenance.",
  mins=30, cost=0),

T("hvac-thermostat-battery", "Replace thermostat batteries", "HVAC", annually(11, 1),
  "A dying thermostat battery can drop the call for cooling with no obvious warning. Replacing it on a schedule "
  "costs $4 and avoids a mystery no-cool service call.",
  ["Pull the thermostat face off the wall plate.",
   "Replace the AA/AAA batteries (note the type in this task's notes).",
   "Re-seat the face and confirm the display and the system respond."],
  "Manufacturer general guidance: annual battery replacement.",
  priority="low", mins=5, cost=5),

T("hvac-airhandler-inspect", "Inspect air handler, drain pan and lineset", "HVAC", every(90),
  "A slow leak in the drain pan or sweating, uninsulated refrigerant lines will quietly rot drywall or grow mold "
  "in your attic or closet long before you smell anything.",
  ["Look in the secondary drain pan under the air handler -- it should be bone dry.",
   "Check the large insulated copper line; the foam should be intact with no bare cold pipe sweating.",
   "Look for rust streaks, water stains or musty smell around the cabinet.",
   "Confirm the emergency float switch is seated and not tripped."],
  "Goodman preventive maintenance: inspect coils, refrigerant lines and drains.",
  priority="high", mins=15, cost=0, equip="Goodman air handler"),

T("hvac-register-warranty", "Register Goodman + Natural Air warranty", "HVAC", once(2026, 9, 20),
  "Goodman's best warranty terms usually require online registration within 60 days of installation. If you're past "
  "that window, the builder's registration may already cover you -- but you need to confirm and get it in writing.",
  ["Find the model and serial number on the outdoor unit's data plate; photograph it.",
   "Go to goodmanmfg.com warranty registration and check whether the unit is already registered.",
   "If not registered, register it now and note the installation date from your closing documents.",
   "Call Natural Air Energy Saving Systems and ask them to email confirmation of registration and your labor warranty term.",
   "Save all of it in your home documents folder."],
  "Goodman: registration required within 60 days of installation for full warranty term.",
  priority="critical", mins=30, cost=0, equip="Goodman system"),

# ==========================================================================
# WATER HEATER -- State Water Heaters
# ==========================================================================
T("wh-flush-first", "First tank flush + anode rod inspection (6-month)", "Water Heater",
  once(2027, 1, 28),
  "State Water Heaters explicitly calls for the FIRST drain, flush and anode inspection at six months, then annually. "
  "This one-time early check catches construction sediment and confirms the anode is protecting your tank.",
  ["Turn OFF power to the water heater at the breaker.",
   "Shut the cold water supply valve on top of the heater.",
   "Attach a hose to the drain valve and run it to a driveway or floor drain.",
   "Open the drain valve and a hot tap upstairs to break the vacuum; drain fully.",
   "Briefly reopen the cold supply to stir and flush remaining sediment; repeat until clear.",
   "Unscrew and inspect the anode rod -- replace it if it's under ~1/2 inch thick or heavily crusted.",
   "Close the drain, refill completely (hot tap runs steady with no air), THEN restore power."],
  "State Water Heaters manual: drain/flush tank and inspect anode rod after the first six months of operation.",
  priority="high", mins=90, cost=40, equip="State water heater"),

T("wh-flush-annual", "Drain and flush tank + inspect anode rod", "Water Heater", every(365),
  "Sediment on the tank floor insulates the heating element, wastes electricity, makes rumbling noises, and shortens "
  "tank life. The sacrificial anode rod is the only thing standing between your water and a rusted-through tank.",
  ["Turn OFF power at the breaker and shut the cold supply valve.",
   "Hose on the drain valve, open a hot tap to vent, drain the tank.",
   "Flush with short bursts of cold supply until the water runs clear.",
   "Remove and inspect the anode rod; replace if heavily consumed.",
   "Refill completely before restoring power -- powering a dry element destroys it."],
  "State Water Heaters manual: drain, flush and inspect the anode rod at least annually.",
  priority="high", mins=90, cost=40, equip="State water heater"),

T("wh-tp-valve", "Test T&P relief valve", "Water Heater", every(365),
  "The temperature & pressure relief valve is the water heater's last line of defense against becoming a rocket. "
  "It can seize shut from mineral scale, and testing it once a year is how you know it hasn't.",
  ["Make sure the discharge pipe runs to a safe place (floor drain or outside).",
   "Stand clear -- the water released is scalding hot.",
   "Lift the valve's test lever for a second and let it snap back.",
   "Water should gush out and stop cleanly when the lever closes.",
   "If it dribbles afterward or nothing comes out, call a plumber to replace the valve."],
  "State Water Heaters manual: operate the T&P valve annually.",
  priority="critical", mins=10, cost=0, equip="State water heater"),

T("wh-tp-inspect", "Full T&P valve inspection / replacement", "Water Heater", every(1095),
  "Beyond the annual lever test, the valve itself should be inspected on a 2-4 year cycle per the label on the valve. "
  "Florida's mineral content is hard on them.",
  ["Read the maintenance interval printed on the T&P valve's own label -- it governs.",
   "Have a plumber inspect or replace the valve if it's weeping, corroded, or past its labeled interval."],
  "State Water Heaters manual: inspect the T&P valve every 2-4 years; follow the valve's own label.",
  priority="high", diy=False, mins=45, cost=120, equip="State water heater"),

T("wh-temp-check", "Verify water heater set to 120°F", "Water Heater", every(365),
  "120°F is the sweet spot: hot enough to suppress Legionella, cool enough to avoid scalding kids, and every "
  "10 degrees lower cuts standby energy loss.",
  ["Run the kitchen hot tap for 2 minutes and measure with a cooking thermometer.",
   "If it's above 125°F or below 115°F, kill power at the breaker and adjust both upper and lower thermostats behind the access panels.",
   "Recheck after a few hours."],
  "DOE / manufacturer standard recommendation.",
  priority="normal", mins=15, cost=0, equip="State water heater"),

T("wh-leak-check", "Check water heater area for leaks and corrosion", "Water Heater", every(90),
  "Tanks almost never fail without warning -- they weep first. Catching a seep gives you weeks to plan a replacement "
  "instead of coming home to a flooded garage.",
  ["Look at the floor and drain pan under and around the tank.",
   "Check the cold inlet and hot outlet connections for green/white crust or drips.",
   "Feel the pipes and fittings for dampness.",
   "Confirm the drain pan's discharge line is clear."],
  "Standard plumbing preventive maintenance.",
  priority="high", mins=10, cost=0, equip="State water heater"),

# ==========================================================================
# IRRIGATION & LAWN -- Hunter
# ==========================================================================
T("irr-zone-audit", "Run full sprinkler zone-by-zone audit", "Irrigation & Lawn", every(90),
  "Hunter's core homeowner guidance is to check for leaks, clogged heads and worn parts. One stuck head can flood a "
  "bed and brown out a whole zone, and you'd never notice because it runs at 5am.",
  ["At the Hunter controller, use MANUAL mode to run each zone for ~2 minutes.",
   "Walk each zone while it runs.",
   "Look for: heads that don't pop up, blocked/misaimed spray, misting (pressure too high), geysers (broken head), soggy spots (leak).",
   "Clear grass overgrowth around each head with a trimmer or shovel.",
   "Note any broken heads in this task's notes and replace or call the irrigation company."],
  "Hunter Industries homeowner guidance: check for leaks, unclogged heads, and component wear.",
  priority="high", mins=45, cost=15, equip="Hunter controller", requires="irrigation"),

T("irr-seasonal-adjust", "Adjust Hunter controller seasonal schedule", "Irrigation & Lawn", on_months([3, 6, 9, 12], 1),
  "Florida's rainy season (roughly June-September) needs far less supplemental water than the March-May dry season. "
  "Hunter's Seasonal Adjust % lets you scale every program at once instead of reprogramming each zone.",
  ["Open the Hunter controller and find Seasonal Adjust (or Water Budget) %.",
   "Dry season (Mar-May): 100-120%. Rainy season (Jun-Sep): 50-70%. Cool season (Oct-Feb): 40-60%.",
   "Check your county/water-district day-of-week watering restrictions and match the program days.",
   "Verify the start time is early morning (4-6am) to cut evaporation and fungus.",
   "Use Hunter's free Run Time Calculator at hunterirrigation.com/tools/runtime to sanity-check run times."],
  "Hunter Industries: adjust watering schedules seasonally; Seasonal Adjust / Solar Sync features.",
  priority="normal", mins=20, cost=0, equip="Hunter controller", requires="irrigation"),

T("irr-controller-battery", "Replace Hunter controller backup battery", "Irrigation & Lawn", annually(2, 1),
  "The 9V backup keeps your programs and clock through power outages. If it's dead when a storm knocks power out, "
  "you'll come back to a controller that has forgotten every schedule.",
  ["Open the Hunter controller's face panel.",
   "Swap the 9V (or coin cell on newer models) backup battery.",
   "Confirm the date and time are still correct afterward.",
   "Photograph your program settings as a backup."],
  "Hunter controller manuals: replace backup battery annually.",
  priority="low", mins=10, cost=6, equip="Hunter controller", requires="irrigation"),

T("irr-rain-sensor", "Test and clean rain sensor", "Irrigation & Lawn", on_months([5, 11], 1),
  "Florida law requires a working rain sensor or shutoff device on automatic irrigation systems. A gummed-up sensor "
  "means you're watering in a thunderstorm and paying for it.",
  ["Locate the rain sensor (usually roof edge or fence, in open sky).",
   "Clear debris, spider webs and wasp nests from the vents.",
   "Press/soak the sensor to trigger it, then start a zone manually -- it should refuse to run.",
   "Let it dry and confirm normal operation returns.",
   "Replace the sensor if it doesn't trip (they typically last 5-8 years in Florida sun)."],
  "Florida Statute 373.62 requires a functioning rain sensor; Hunter sensor maintenance guidance.",
  priority="high", mins=20, cost=0, equip="Hunter rain sensor", requires="irrigation"),

T("irr-nozzle-clean", "Clean sprinkler nozzles and filter screens", "Irrigation & Lawn", on_months([4, 10], 20),
  "Grit from the municipal line collects in each head's filter screen. Symptoms look exactly like low water pressure "
  "or a bad valve, and people replace expensive parts chasing it.",
  ["Shut the zone off.",
   "Unscrew the nozzle and lift the filter screen out of the head's riser.",
   "Rinse the screen and nozzle; poke the orifice with a thin wire if needed.",
   "Reassemble, run the zone, and re-aim the spray arc so you're not watering the driveway or house."],
  "Hunter Industries homeowner guidance: keep sprinkler heads unclogged.",
  mins=45, cost=10, equip="Hunter heads", requires="irrigation"),

T("irr-backflow-test", "Backflow preventer inspection / certification", "Irrigation & Lawn", annually(4, 1),
  "The backflow device stops fertilizer and lawn chemicals from siphoning back into your drinking water. Most Florida "
  "utilities require a certified annual test and will fine you or shut off service if you skip it.",
  ["Check whether your city/utility sends an annual backflow test notice -- many do.",
   "Hire a licensed backflow tester (usually $60-100).",
   "Make sure they file the certification with the utility.",
   "Keep a copy."],
  "Typical Florida municipal cross-connection control requirement.",
  priority="normal", diy=False, mins=30, cost=80, requires="irrigation"),

T("lawn-fertilize", "Fertilize lawn", "Irrigation & Lawn", on_months([3, 5, 10], 1),
  "Most Florida counties BAN nitrogen/phosphorus fertilizer June 1 - September 30 during the rainy season, with real "
  "fines. That leaves early spring, late spring and fall as your windows.",
  ["Check your county's fertilizer ordinance and blackout dates before buying.",
   "Use a slow-release nitrogen product suited to St. Augustine / Bahia (whatever your sod is).",
   "Apply with a broadcast spreader at the bag's rate -- more is not better and burns the lawn.",
   "Sweep granules off driveway and sidewalk back onto grass so they don't wash into storm drains.",
   "Water in lightly unless rain is expected."],
  "Florida county fertilizer ordinances (summer blackout, typically Jun 1 - Sep 30).",
  mins=60, cost=45),

T("lawn-pest-check", "Inspect lawn for chinch bugs and fungus", "Irrigation & Lawn", every(90),
  "Chinch bugs will kill St. Augustine grass in irregular yellow-brown patches, usually starting in sunny spots near "
  "concrete. Caught early it's a $25 treatment; caught late it's resodding.",
  ["Walk the sunniest edges of the lawn, especially near driveway and sidewalk.",
   "Part the grass at the edge of any yellowing patch and look at the soil line for tiny black/white insects.",
   "Check for brown patch fungus: circular yellowing rings, worse after wet weather.",
   "Treat or call your lawn service if you find either."],
  "UF/IFAS Florida lawn pest guidance.",
  priority="normal", mins=20, cost=25),

T("lawn-tree-trim", "Trim trees and branches back from the house", "Irrigation & Lawn", annually(4, 15),
  "Do this BEFORE hurricane season, not during it. Overhanging limbs become roof-puncturing projectiles, and branches "
  "touching the house are a highway for ants, rats and roof damage.",
  ["Cut back anything overhanging the roof by at least 6 feet.",
   "Remove dead or weakly attached limbs.",
   "Keep all vegetation at least 3 feet off siding, soffits and the AC condenser.",
   "Hire an arborist for anything you'd need a ladder plus a saw for."],
  "Florida hurricane-preparedness standard guidance: trim before June 1.",
  priority="high", diy=False, mins=120, cost=250),

T("lawn-mulch", "Refresh mulch (keep 6 inches off the foundation)", "Irrigation & Lawn", annually(3, 20),
  "Mulch piled against the slab is a termite bridge -- it lets them cross your treated soil barrier undetected. "
  "Florida inspectors call the required gap the 'dead zone'.",
  ["Rake back old mulch and top up to 2-3 inches deep.",
   "Pull mulch back to leave a bare 6-inch gap against the foundation and siding.",
   "Keep mulch away from AC lineset penetrations and hose bibs.",
   "Consider rock instead of wood mulch within 12 inches of the house."],
  "Florida termite guidance: keep a 6-inch mulch-free 'dead zone' against the structure.",
  priority="normal", mins=120, cost=120),

# ==========================================================================
# REFRIGERATOR -- LG
# ==========================================================================
T("lg-fridge-water-filter", "Replace LG refrigerator water filter", "Kitchen", every(180),
  "LG rates its fridge filters for roughly six months or 200 gallons. Past that the carbon is spent, flow drops, and "
  "the filter housing itself can start harboring bacteria.",
  ["Find your filter part number (inside the fridge compartment or in the manual) -- record it in notes.",
   "Twist the old filter out (usually a quarter turn) and insert the new one.",
   "Run 2-3 gallons through the dispenser to purge carbon fines and air.",
   "Reset the filter indicator light (hold the filter/reset button ~3 seconds).",
   "Toss the first couple of batches of ice."],
  "LG refrigerator maintenance guidance: replace water filter on a ~6 month cycle.",
  priority="normal", mins=15, cost=45, equip="LG refrigerator"),

T("lg-fridge-air-filter", "Replace LG refrigerator air filter", "Kitchen", every(180),
  "Separate from the water filter. LG's Pure N Fresh style air filter is what keeps onion and leftovers smell from "
  "getting into everything else.",
  ["Locate the air filter cartridge on the rear interior wall of the fresh food compartment.",
   "Pop the cover, swap the cartridge.",
   "Reset the air filter indicator if your model has one."],
  "LG refrigerator maintenance guidance.",
  priority="low", mins=10, cost=25, equip="LG refrigerator"),

T("lg-fridge-coils", "Clean refrigerator condenser coils", "Kitchen", every(180),
  "Dust-blanketed coils make the compressor run hot and long. LG recommends once or twice a year -- twice if you have "
  "pets. It's the single biggest thing you can do for fridge lifespan.",
  ["Unplug the refrigerator or kill its breaker.",
   "Pull the unit out or remove the toe-kick grille at the bottom front.",
   "Vacuum the coils and the fan with a brush attachment; a coil brush helps reach the back.",
   "Vacuum the floor underneath too.",
   "Slide it back, plug in, and confirm it's level."],
  "LG: clean condenser coils once or twice a year; every six months with pets.",
  priority="normal", mins=30, cost=0, equip="LG refrigerator"),

T("lg-fridge-gaskets", "Clean door gaskets and test the seal", "Kitchen", every(90),
  "A gasket that's sticky with syrup or has taken a set will leak cold air continuously. It's a silent, expensive "
  "failure and takes five minutes to check.",
  ["Wipe both door gaskets with warm soapy water and dry them.",
   "Close a dollar bill in the door -- if it slides out with no drag, that spot isn't sealing.",
   "Check all four sides of both doors.",
   "Note any failing sections; gaskets are replaceable."],
  "LG refrigerator maintenance guidance.",
  priority="low", mins=15, cost=0, equip="LG refrigerator"),

T("lg-icemaker", "Clean and inspect ice maker + water line", "Kitchen", every(180),
  "Ice absorbs freezer odors and the supply line's compression fitting is a classic slow-leak spot that ruins "
  "flooring behind the fridge before anyone notices.",
  ["Empty the ice bin, wash it with warm soapy water, dry completely.",
   "Look behind the fridge at the water line shutoff and fitting for moisture or mineral crust.",
   "Confirm the line isn't kinked or pinched by the fridge.",
   "Discard the first full bin of ice after cleaning."],
  "LG appliance maintenance guidance.",
  priority="normal", mins=25, cost=0, equip="LG refrigerator"),

# ==========================================================================
# LAUNDRY -- LG washer & dryer
# ==========================================================================
T("lg-washer-tubclean", "Run LG washer Tub Clean cycle", "Laundry", every(30),
  "LG asks for monthly maintenance on the washer. Front loaders especially build a biofilm of detergent and body oils "
  "behind the drum -- that's where 'my clean laundry smells musty' comes from.",
  ["Empty the drum completely.",
   "Select TUB CLEAN on the control panel.",
   "Add the recommended tub cleaner tablet or 1 cup of white vinegar (never chlorine bleach plus vinegar).",
   "Run the full cycle.",
   "Wipe the door gasket and glass dry afterward, and leave the door ajar."],
  "LG washer maintenance: perform maintenance on each section roughly monthly.",
  priority="normal", mins=10, cost=4, equip="LG washer"),

T("lg-washer-dispenser", "Clean washer detergent dispenser drawer", "Laundry", every(30),
  "LG calls out the dispenser specifically -- at least once a month. Congealed detergent and softener residue stops "
  "the drawer dispensing properly and grows mold.",
  ["Pull the dispenser drawer fully out (there's usually a release tab).",
   "Soak the drawer and inserts in hot water; scrub with an old toothbrush.",
   "Wipe out the drawer cavity in the machine, including the jets in the roof of the cavity.",
   "Dry and reinstall."],
  "LG washer maintenance: clean the detergent dispenser at least once a month.",
  priority="normal", mins=15, cost=0, equip="LG washer"),

T("lg-washer-pumpfilter", "Clean washer drain pump filter", "Laundry", every(90),
  "The pump filter catches coins, hair pins and lint. When it clogs the washer throws a drain error mid-cycle and "
  "leaves you with a drum full of water.",
  ["Put a shallow pan and towels under the small access door at the bottom front.",
   "Open the door, pull the small drain hose out, uncap it and let the water drain into the pan (there will be more than you expect).",
   "Unscrew the filter counter-clockwise, clear the debris, rinse it.",
   "Screw it back in snugly and close the door.",
   "Run a short rinse cycle and check for leaks."],
  "LG front load washer maintenance guidance.",
  priority="normal", mins=25, cost=0, equip="LG washer"),

T("lg-washer-hoses-check", "Inspect washer fill hoses", "Laundry", on_months([3, 9], 10),
  "A burst washer hose delivers about 600 gallons an hour. It's one of the most common large water-damage claims "
  "there is, and it's completely preventable.",
  ["Pull the washer out far enough to see both hoses.",
   "Look for bulges, blisters, rust at the crimps, and dampness at the connections.",
   "Confirm both are hand-tight plus a quarter turn -- not cranked.",
   "Consider braided stainless hoses if yours are rubber.",
   "Locate the shutoff valves and make sure you could reach them fast."],
  "Standard homeowner insurance loss-prevention guidance.",
  priority="high", mins=15, cost=0, equip="LG washer"),

T("lg-washer-hoses-replace", "Replace washer fill hoses", "Laundry", every(1825),
  "Even good braided hoses are consumables. Five years is the widely used replacement interval regardless of how "
  "they look.",
  ["Shut both supply valves and unplug the washer.",
   "Unscrew old hoses (have a towel ready).",
   "Install new braided stainless hoses with fresh rubber washers.",
   "Open valves slowly and check for drips at all four connections.",
   "Write the install date on a piece of tape on the hose."],
  "Standard 5-year replacement interval for washer supply hoses.",
  priority="normal", mins=30, cost=30, equip="LG washer"),

T("lg-washer-gasket-wipe", "Wipe washer door gasket dry", "Laundry", every(7),
  "Thirty seconds a week is the whole difference between a fresh washer and a moldy one. Water pools in the fold at "
  "the bottom of the boot after every load.",
  ["Peel back the rubber door boot and wipe the fold with a dry cloth.",
   "Wipe the door glass and the frame.",
   "Leave the door and the dispenser drawer ajar between uses."],
  "LG: wipe away visible water from drum, gasket and door glass; leave door open to reduce odor.",
  priority="low", mins=3, cost=0, equip="LG washer"),

T("lg-dryer-lint", "Clean dryer lint trap", "Laundry", every(7),
  "LG says clean it before or after every single load. This is a reminder to also do a deeper wipe -- fabric softener "
  "sheets leave an invisible film on the screen that blocks airflow.",
  ["Pull the lint screen and clear it after each load.",
   "Weekly: wash the screen with warm soapy water and a brush to strip softener film, then dry it fully before reinserting.",
   "Water should pass straight through a clean screen -- if it beads up, it needs scrubbing."],
  "LG dryer maintenance: clean the lint trap before or after each load.",
  priority="high", mins=5, cost=0, equip="LG dryer"),

T("lg-dryer-sensor", "Wipe dryer moisture sensor strips", "Laundry", every(30),
  "LG calls for monthly cleaning of the moisture sensors with rubbing alcohol. When they're coated in softener "
  "residue the dryer thinks clothes are dry and shuts off early -- the classic 'my dryer stopped drying' complaint.",
  ["Find the two curved metal strips inside the drum, usually just below the lint trap opening.",
   "Wipe them with a cotton ball dampened with rubbing alcohol.",
   "Let them dry before running a load."],
  "LG dryer maintenance: wipe moisture sensor strips with rubbing alcohol monthly.",
  priority="normal", mins=5, cost=1, equip="LG dryer"),

T("lg-dryer-housing-vac", "Vacuum lint trap housing and check exhaust vent", "Laundry", every(90),
  "LG's quarterly item. Lint that gets past the screen packs into the housing and the duct -- this is the actual "
  "fire risk, not the screen.",
  ["Unplug the dryer.",
   "Vacuum deep into the lint trap slot with a crevice tool or dryer lint brush.",
   "Pull the dryer out, disconnect the flex duct, and vacuum both the duct and the dryer's outlet.",
   "Check the duct isn't crushed behind the dryer -- use rigid or semi-rigid metal, never plastic or foil.",
   "Reconnect with a clamp and push the dryer back, leaving a few inches of clearance."],
  "LG dryer maintenance: vacuum lint trap housing and check exhaust vent every 3 months.",
  priority="high", mins=40, cost=0, equip="LG dryer"),

T("lg-dryer-vent-pro", "Professional dryer exhaust vent cleaning", "Laundry", every(365),
  "LG recommends an annual professional exhaust cleaning to get the hidden lint in the wall run that you can't reach. "
  "Dryer fires cause thousands of house fires a year and lint is the ignition source in most of them.",
  ["Hire a dryer vent cleaning service (often $100-180).",
   "Ask them to clean the full run from dryer to the exterior hood and to verify airflow at the hood.",
   "Ask them to confirm the duct material and length meet code.",
   "Keep the receipt."],
  "LG dryer maintenance: schedule professional exhaust vent cleaning annually.",
  priority="high", diy=False, mins=60, cost=140, equip="LG dryer"),

T("dryer-vent-hood", "Check exterior dryer vent hood flap", "Laundry", on_months([4, 10], 12),
  "The flap outside should open when the dryer runs and close when it stops. A stuck-open flap is an invitation for "
  "lizards, wasps and birds; a stuck-closed one backs lint into the duct.",
  ["Run the dryer on air-fluff.",
   "Go outside and confirm the hood flap opens and you feel strong airflow.",
   "Clear lint, nests or webs from the hood.",
   "Confirm the flap closes fully when the dryer stops."],
  "Standard dryer vent maintenance.",
  priority="normal", mins=10, cost=0, equip="LG dryer"),

# ==========================================================================
# KITCHEN -- Samsung range / cooktop / microwave, dishwasher, disposal
# ==========================================================================
T("samsung-micro-grease", "Clean Samsung microwave grease filter", "Kitchen", every(30),
  "Samsung specifies cleaning the grease filter at least once a month. A saturated filter stops venting your cooktop "
  "and can drip grease back onto the range.",
  ["Slide the metal mesh filter(s) out from the underside of the microwave.",
   "Soak in hot water with degreasing dish soap for 10 minutes.",
   "Scrub gently with a soft brush, rinse, dry completely.",
   "Slide back in -- never run the microwave vent without the filter installed."],
  "Samsung: remove and clean the grease filter at least once per month.",
  priority="normal", mins=20, cost=0, equip="Samsung microwave"),

T("samsung-micro-charcoal", "Replace Samsung microwave charcoal filter", "Kitchen", every(270),
  "Only applies if your over-the-range microwave RECIRCULATES rather than venting outside. Samsung says every 6-12 "
  "months; the charcoal can't be washed and reused.",
  ["First confirm the unit recirculates -- if it's ducted outside, you can disable this task in Settings.",
   "Open the grille at the top front of the microwave (usually two screws).",
   "Slide the old charcoal cartridge out and the new one in.",
   "Reinstall the grille."],
  "Samsung: replace the charcoal filter every 6 to 12 months, more often if needed.",
  priority="low", mins=20, cost=30, equip="Samsung microwave"),

T("samsung-micro-interior", "Clean microwave interior and turntable", "Kitchen", every(14),
  "Baked-on splatter absorbs microwave energy, creates hot spots, and can scorch. Steam does most of the work for you.",
  ["Microwave a bowl of water with lemon slices for 4 minutes; let it sit 3 minutes.",
   "Wipe the interior, ceiling and door with a soft damp cloth.",
   "Wash the turntable and roller ring.",
   "Wipe the control panel with a barely-damp soft cloth only -- no sprays or abrasives."],
  "Samsung: wipe with a soft cloth and warm soapy water; avoid sprays, abrasives and sharp objects on the panel.",
  priority="low", mins=15, cost=0, equip="Samsung microwave"),

T("samsung-oven-deepclean", "Deep clean Samsung oven", "Kitchen", every(90),
  "Carbonized grease is what makes an oven smoke and smell. If you use the self-clean cycle, treat it as a scheduled "
  "event -- it runs extremely hot and can stress the door lock and thermal fuse.",
  ["Remove racks (self-clean discolors them) and wipe out loose debris.",
   "Run the self-clean cycle, or use a low-fume oven cleaner if you'd rather not.",
   "Open windows and turn on the range hood -- self-clean produces fumes that are hard on birds and pets.",
   "After it cools, wipe out the fine ash with a damp cloth.",
   "Wash racks separately in the sink."],
  "Samsung oven care guidance.",
  priority="normal", mins=45, cost=8, equip="Samsung range"),

T("samsung-cooktop-clean", "Deep clean cooktop and burners", "Kitchen", every(14),
  "Beyond the daily wipe: spills that cook onto a glass-ceramic surface can etch it permanently, and on a gas or "
  "coil top they block even heating.",
  ["Let the surface cool completely.",
   "Use a cooktop cleaning cream and a non-scratch pad for glass-ceramic; a razor scraper at a low angle for hardened spots.",
   "Buff dry with a microfiber cloth.",
   "Check that burner/element seating is clean and even."],
  "Samsung cooktop care guidance.",
  priority="low", mins=20, cost=8, equip="Samsung cooktop"),

T("samsung-oven-seal", "Check oven door seal and calibration", "Kitchen", every(365),
  "A crushed door gasket leaks heat, wastes energy and bakes unevenly. A miscalibrated oven quietly ruins baking and "
  "is a five-minute fix in the settings menu.",
  ["Inspect the braided door gasket for gaps, tears or flattened sections.",
   "Put an oven thermometer on the center rack, set to 350°F, wait 20 minutes past preheat, and read it.",
   "If it's off by more than 15°F, use the oven's temperature adjustment setting to calibrate.",
   "Recheck."],
  "Samsung range care guidance.",
  priority="low", mins=40, cost=15, equip="Samsung range"),

T("dishwasher-filter", "Clean dishwasher filter", "Kitchen", every(30),
  "Modern dishwashers have a manual filter that most people never learn exists. When it packs with food, dishes come "
  "out gritty and the machine starts to smell.",
  ["Pull the bottom rack out.",
   "Twist the cylindrical filter counter-clockwise and lift it out with the flat mesh screen underneath.",
   "Rinse both under hot water; scrub with a soft brush and dish soap.",
   "Reinstall and twist to lock -- make sure it seats fully or the pump can be damaged."],
  "Standard dishwasher manufacturer guidance.",
  priority="normal", mins=15, cost=0, requires="dishwasher"),

T("dishwasher-clean-cycle", "Run dishwasher cleaner cycle", "Kitchen", every(90),
  "Descales the spray arms and heating element and clears the grease film in the sump. Florida water is hard enough "
  "that scale builds noticeably.",
  ["Empty the dishwasher.",
   "Place a dishwasher cleaner tablet or a cup of white vinegar on the top rack.",
   "Run the hottest/longest cycle.",
   "Wipe the door edges and the gasket, which the cycle doesn't reach."],
  "Standard dishwasher manufacturer guidance.",
  priority="low", mins=10, cost=5, requires="dishwasher"),

T("disposal-clean", "Clean and deodorize garbage disposal", "Kitchen", every(30),
  "Food film on the grinding chamber walls and the underside of the splash guard is what actually smells -- not the "
  "drain. Ice scours the chamber.",
  ["Run a tray of ice cubes plus a half cup of coarse salt through with cold water.",
   "Follow with citrus peels (lemon or orange).",
   "Scrub the underside of the rubber splash guard with an old toothbrush and dish soap.",
   "Never put grease, fibrous vegetables, pasta or rice down it."],
  "Standard disposal maintenance.",
  priority="low", mins=10, cost=2),

T("range-hood-vent", "Verify kitchen exhaust actually vents", "Kitchen", every(365),
  "Worth confirming once a year: Florida humidity plus a recirculating hood means cooking moisture stays in the "
  "house, which feeds mold.",
  ["Run the vent on high and hold a tissue to the intake -- it should hold.",
   "Go outside and confirm air is coming out of the exterior hood, if ducted.",
   "Clear the exterior hood of debris and nests."],
  "Standard kitchen ventilation check.",
  priority="low", mins=10, cost=0),

# ==========================================================================
# PLUMBING
# ==========================================================================
T("plumb-main-shutoff", "Locate and label the main water shutoff", "Plumbing", once(2026, 9, 12),
  "The single most valuable ten minutes a new homeowner can spend. When a line lets go you have about 90 seconds of "
  "useful thinking time, and that is not when you want to be hunting for a valve in the dark.",
  ["Find the main shutoff -- typically at the street meter box, and often a second one where the line enters the house.",
   "Open the meter box lid (a long screwdriver helps) and confirm you can reach and turn the valve.",
   "Buy a water meter key if the valve needs one; keep it somewhere obvious.",
   "Turn the water fully off and back on once so you know it isn't seized.",
   "Photograph the location, tag the valve, and tell everyone in the house where it is."],
  "Universal homeowner emergency-preparedness guidance.",
  priority="critical", mins=30, cost=15),

T("plumb-valves-exercise", "Exercise all shutoff valves", "Plumbing", every(365),
  "Valves that never move seize open. You find out the day you need one, and then a small leak becomes a whole-house "
  "shutoff and an emergency plumber.",
  ["Work through every fixture: under each sink, behind each toilet, at the washer, at the water heater.",
   "Close each valve fully, then reopen fully, then back off a quarter turn.",
   "Note any that are stiff, weep, or won't seat -- those need replacing.",
   "Finish with the main shutoff."],
  "Standard plumbing preventive maintenance.",
  priority="normal", mins=45, cost=0),

T("plumb-leak-sweep", "Check under every sink and behind toilets for leaks", "Plumbing", every(90),
  "In new construction, supply connections and P-traps can loosen as the house settles through its first year. "
  "A slow drip under a vanity is invisible until the cabinet floor swells.",
  ["Empty each under-sink cabinet enough to see the floor.",
   "Run water and feel every connection: supply valves, supply lines, P-trap joints, disposal fitting.",
   "Look for water staining, swelling particleboard or a musty smell.",
   "Check the floor behind and beside each toilet, and the caulk line at the base.",
   "Lay a paper towel under suspect joints and check it the next day."],
  "New-construction settling guidance + standard plumbing maintenance.",
  priority="high", mins=30, cost=0),

T("plumb-toilets", "Inspect toilets for running and rocking", "Plumbing", every(90),
  "A silently running flapper wastes up to 200 gallons a day and shows up on your water bill before you ever hear it. "
  "A toilet that rocks will break its wax ring and leak into the subfloor.",
  ["Put a few drops of food coloring in each tank; wait 15 minutes without flushing.",
   "If color appears in the bowl, the flapper is leaking -- replace it (a $8 part).",
   "Grip the bowl and try to rock it -- it should be solid. If it moves, the closet bolts need tightening or the wax ring is failing.",
   "Confirm the fill valve shuts off cleanly and the water stops below the overflow tube."],
  "Standard plumbing maintenance / water conservation guidance.",
  priority="normal", mins=25, cost=10),

T("plumb-aerators", "Clean faucet aerators and showerheads", "Plumbing", on_months([3, 9], 5),
  "Central Florida water is hard. Scale in the aerator screens shows up as weak, spitting or sideways flow, and "
  "people replace whole faucets over a $2 screen.",
  ["Unscrew each aerator (a cloth protects the finish from the pliers).",
   "Soak parts in white vinegar for an hour, then brush the screen clear.",
   "For showerheads, bag vinegar around the head with a rubber band and soak overnight.",
   "Reassemble and run to flush loose grit."],
  "Standard hard-water plumbing maintenance.",
  priority="low", mins=45, cost=5),

T("plumb-washer-pan", "Check laundry drain pan and standpipe", "Plumbing", every(90),
  "The pan under the washer only helps if its drain isn't plugged, and a slow standpipe will back up and overflow "
  "during a spin cycle's fast drain.",
  ["Look in the pan for standing water or debris.",
   "Confirm the pan's drain line is clear.",
   "Run a wash cycle and watch the standpipe during drain -- it shouldn't fill and gurgle back.",
   "Pour a gallon of hot water plus a cup of vinegar down the standpipe if it's sluggish."],
  "Standard laundry plumbing maintenance.",
  priority="normal", mins=15, cost=0),

T("plumb-hosebibs", "Inspect exterior hose bibs and check for leaks", "Plumbing", on_months([4, 10], 8),
  "Outdoor spigots take UV and physical abuse, and a dripping bib on a slab foundation puts constant moisture right "
  "where you least want it.",
  ["Check each exterior spigot for drips at the handle and the spout.",
   "Replace worn washers or packing nuts.",
   "Confirm there's no soft ground or constant wet spot at the wall below.",
   "Check that hoses are disconnected when not in use."],
  "Standard exterior plumbing maintenance.",
  priority="low", mins=15, cost=8),

T("plumb-leak-detectors", "Test water leak detectors", "Plumbing", on_months([3, 9], 18),
  "If you have (or add) battery leak sensors under sinks, at the water heater and behind the washer, they only help "
  "if the batteries are alive.",
  ["Touch a wet finger or damp cloth across each sensor's contacts.",
   "Confirm each alarms.",
   "Replace batteries annually regardless.",
   "If you don't have any yet, this is a ~$15/each upgrade worth making."],
  "Loss-prevention best practice.",
  priority="low", mins=15, cost=10),

# ==========================================================================
# ELECTRICAL & SAFETY
# ==========================================================================
T("safety-smoke-test", "Test all smoke and CO alarms", "Electrical & Safety", every(30),
  "Monthly is the manufacturer and NFPA standard. In new construction the alarms are interconnected, so testing one "
  "should sound them all -- which also verifies the interconnect wiring the builder installed.",
  ["Press and hold the TEST button on each alarm until it sounds.",
   "Confirm every other alarm in the house sounds too (they should be interconnected).",
   "Warn the family first so nobody panics.",
   "Note any unit that doesn't join the chorus -- that's a builder warranty item right now."],
  "NFPA / manufacturer standard: test smoke alarms monthly.",
  priority="critical", mins=10, cost=0),

T("safety-smoke-battery", "Replace smoke alarm backup batteries", "Electrical & Safety", annually(11, 5),
  "Even hardwired alarms have a backup battery. The 3am low-battery chirp always happens on the coldest, busiest "
  "night -- do them all at once on a schedule instead.",
  ["Replace the backup battery in every alarm, even ones not chirping.",
   "Vacuum dust out of each alarm's vents while you're up there.",
   "Test each alarm afterward.",
   "Note: some newer units have sealed 10-year batteries -- if so, mark this task disabled in Settings."],
  "NFPA / manufacturer standard.",
  priority="high", mins=30, cost=25),

T("safety-smoke-replace", "Replace smoke/CO alarms (10-year life)", "Electrical & Safety",
  once(2036, 7, 28),
  "Smoke alarm sensors degrade and every manufacturer sets a hard 10-year expiration from the date of manufacture, "
  "not from installation. Yours are new, so this is a long way out -- but it's scheduled so it doesn't get forgotten.",
  ["Check the manufacture date printed on the back of each alarm.",
   "Replace every unit that is 10 years past its manufacture date.",
   "Replace CO alarms per their own (usually 7-10 year) rating."],
  "NFPA 72: replace smoke alarms 10 years from date of manufacture.",
  priority="normal", mins=60, cost=200),

T("safety-gfci-test", "Test GFCI and AFCI outlets and breakers", "Electrical & Safety", every(90),
  "GFCIs protect you from electrocution in wet areas -- kitchen, baths, garage, lanai and exterior. They do fail, and "
  "they fail silently in the unprotected state.",
  ["Press TEST on each GFCI outlet; the RESET button should pop and the outlet should go dead (check with a lamp or tester).",
   "Press RESET to restore.",
   "Do this for every GFCI: kitchen counters, all bathrooms, garage, lanai, exterior.",
   "Test AFCI breakers in the panel the same way (TEST button on the breaker).",
   "Any device that won't trip or won't reset needs replacing -- and while you're in year one, that's a builder warranty claim."],
  "NEC / manufacturer guidance: test GFCI devices monthly to quarterly.",
  priority="high", mins=20, cost=0),

T("safety-panel-check", "Inspect electrical panel", "Electrical & Safety", every(365),
  "You're looking for heat damage and loose connections -- discoloration, a burnt plastic smell, or a breaker that "
  "feels warm. Do not remove the panel's inner cover.",
  ["Open the panel door (the outer door only -- leave the dead-front cover on).",
   "Confirm every breaker is labeled clearly; fix the labels if the builder's are vague.",
   "Look and smell for scorching or overheating.",
   "Flip each breaker off and on once a year to keep the mechanism free.",
   "Confirm the panel isn't being used as a shelf and has 3 feet of clear working space."],
  "Standard electrical safety maintenance.",
  priority="normal", mins=20, cost=0),

T("safety-surge-protector", "Check whole-house surge protector status light", "Electrical & Safety", every(90),
  "Florida leads the country in lightning strikes. A whole-house surge protector sacrifices itself absorbing surges "
  "and then sits there dead with a green light turned off, protecting nothing.",
  ["Find the surge protective device at or beside your main panel.",
   "Confirm the status/protection indicator light is green (or per its manual).",
   "If the indicator is off or red, the device is spent -- replace it.",
   "If you don't have one, strongly consider adding one; Florida lightning makes it one of the best $300 you can spend."],
  "Manufacturer guidance for surge protective devices; Florida lightning exposure.",
  priority="normal", mins=5, cost=0),

T("safety-extinguisher", "Check fire extinguishers", "Electrical & Safety", on_months([4, 10], 1),
  "A pressure gauge in the green and a quick shake to keep the powder from caking. If you don't have one in the "
  "kitchen and the garage, get them -- ABC rated, at least 2A:10B:C.",
  ["Confirm the gauge needle is in the green band.",
   "Check the pin and tamper seal are intact and the nozzle is clear.",
   "Turn the extinguisher upside down and shake to loosen packed powder.",
   "Confirm everyone in the house knows where they are and how to use them (PASS: Pull, Aim, Squeeze, Sweep)."],
  "NFPA 10 monthly visual inspection guidance (relaxed here to semi-annual for household units).",
  priority="normal", mins=10, cost=0),

T("safety-extinguisher-replace", "Replace or service fire extinguishers", "Electrical & Safety", every(2190),
  "Disposable household extinguishers are generally considered good for about 6-12 years. If yours are the "
  "non-rechargeable type, replacement is cheaper than servicing.",
  ["Check the manufacture date stamped on the cylinder or label.",
   "Replace disposable units at ~6 years; have rechargeable units professionally serviced.",
   "Dispose of old units properly -- many fire departments accept them."],
  "NFPA 10 maintenance intervals.",
  priority="low", mins=30, cost=60),

T("garage-door-safety", "Test garage door auto-reverse safety", "Electrical & Safety", every(30),
  "The photo-eye sensors and the door's own force reversal are what stop it from closing on a child or a pet. "
  "Manufacturers ask for a monthly test and it takes 60 seconds.",
  ["Photo-eye test: with the door closing, wave a broom through the beam near the floor -- the door must reverse immediately.",
   "Force test: lay a 2x4 flat on the floor in the door's path and close it -- the door must reverse on contact.",
   "Confirm the photo-eye LEDs are lit and aligned.",
   "If either test fails, stop using the opener until it's adjusted or serviced."],
  "CPSC / garage door opener manufacturer guidance: test monthly.",
  priority="critical", mins=10, cost=0, requires="garage"),

T("garage-door-lube", "Lubricate and inspect garage door hardware", "Electrical & Safety", on_months([4, 10], 25),
  "Rollers, hinges and springs under a Florida garage's heat and humidity will squeal and wear fast without lubricant. "
  "Do NOT touch the torsion spring adjustment -- that's a serious injury risk.",
  ["Use a garage-door-specific lithium or silicone spray -- never WD-40 on rollers.",
   "Lubricate rollers, hinges, bearing plates, and the torsion spring coils.",
   "Wipe the track clean but do NOT lubricate the track itself.",
   "Check cables for fraying and check that the door is balanced: disconnect the opener and lift by hand -- it should stay put at waist height.",
   "Call a pro for spring or cable work. Never adjust the springs yourself."],
  "Garage door manufacturer maintenance guidance.",
  priority="normal", mins=30, cost=12, requires="garage"),

T("safety-exterior-outlets", "Check exterior outlet covers and lighting", "Electrical & Safety", on_months([5, 11], 8),
  "Florida rain finds every unsealed exterior outlet. The in-use bubble covers crack in UV and then the box fills "
  "with water.",
  ["Check every exterior and lanai outlet for a working weatherproof in-use cover.",
   "Replace cracked or missing covers.",
   "Test the GFCI protection on each.",
   "Replace burned-out exterior bulbs and check that motion/photocell fixtures still trigger."],
  "NEC weatherproofing requirements / standard exterior maintenance.",
  priority="low", mins=20, cost=25),

# ==========================================================================
# EXTERIOR, ROOF & STRUCTURE
# ==========================================================================
T("ext-roof-visual", "Visual roof inspection from the ground", "Exterior & Roof", on_months([5, 11], 3),
  "You're not getting on the roof. Binoculars from the ground catch lifted or missing shingles, displaced tiles, "
  "damaged vent boots and debris piles -- which is 90% of what matters.",
  ["Walk the full perimeter with binoculars.",
   "Look for: missing/lifted/curled shingles or slipped tiles, damaged ridge cap, debris in valleys.",
   "Check the rubber boots around plumbing vents -- they crack in Florida sun and are a top leak source.",
   "Check flashing at any wall intersections.",
   "Look at soffits and fascia for staining, which means water is getting somewhere it shouldn't.",
   "Photograph anything suspicious with the date -- useful for insurance and warranty claims."],
  "Standard Florida roof maintenance; also do this after every named storm.",
  priority="high", mins=30, cost=0),

T("ext-roof-pro", "Professional roof inspection", "Exterior & Roof", every(1095),
  "Your roof is new, so this is about documentation as much as condition. Many Florida insurers now want a recent "
  "roof inspection, and having a baseline report helps enormously with any future claim.",
  ["Hire a licensed roofing contractor or home inspector.",
   "Ask for a written report with photos.",
   "Ask them to check the sealant at all penetrations and the condition of vent boots.",
   "File the report with your insurance documents."],
  "Florida insurance and roofing industry practice.",
  priority="normal", diy=False, mins=90, cost=200),

T("ext-gutters", "Clean gutters and downspouts", "Exterior & Roof", on_months([5, 11], 6),
  "Overflowing gutters dump water at the foundation, stain the fascia and soffit, and in Florida they breed "
  "mosquitoes in the standing water.",
  ["Clear leaves and debris from the full run.",
   "Flush with a hose and confirm water exits every downspout freely.",
   "Check that downspout extensions carry water at least 4-6 feet from the foundation.",
   "Re-secure any loose hangers.",
   "Look for granule accumulation, which indicates shingle wear."],
  "Standard exterior maintenance, adjusted to Florida's wet season.",
  priority="normal", mins=90, cost=0),

T("ext-drainage", "Check grading and drainage away from the foundation", "Exterior & Roof", on_months([5, 11], 6),
  "New construction settles in its first couple of years and can create low spots that pond water against the slab. "
  "In Florida that's a termite and moisture invitation.",
  ["Walk the perimeter after a heavy rain and look for standing water within 6 feet of the house.",
   "Confirm soil slopes away from the slab -- roughly 6 inches of fall over the first 10 feet.",
   "Add soil to any settled areas against the foundation (but keep it below the slab/siding line).",
   "Confirm downspouts and any French drains discharge well away from the house.",
   "In year one, ponding against the house is a builder warranty item -- report it."],
  "New-construction settling + Florida drainage guidance.",
  priority="high", mins=30, cost=40),

T("ext-caulk", "Inspect and renew exterior caulk and seals", "Exterior & Roof", annually(11, 12),
  "Every place something penetrates the wall -- windows, doors, hose bibs, the AC lineset, dryer vent, light fixtures "
  "-- is a potential water and insect entry. Sealant fails first at the top of windows.",
  ["Walk the perimeter and inspect caulk at every window and door.",
   "Check seals around hose bibs, the AC refrigerant line penetration, dryer vent and exterior fixtures.",
   "Cut out cracked or separated caulk and re-apply a good exterior polyurethane or hybrid sealant.",
   "Do NOT caulk the weep holes at the bottom of window frames -- those are supposed to be open."],
  "Standard exterior envelope maintenance.",
  priority="normal", mins=120, cost=35),

T("ext-stucco-siding", "Inspect stucco / siding for cracks", "Exterior & Roof", annually(6, 12),
  "Hairline stucco cracks are normal as a new house settles. Anything wider than a credit card edge, stair-stepping, "
  "or growing between inspections is worth flagging to the builder while you're under warranty.",
  ["Walk all four elevations in good light.",
   "Photograph any crack next to a coin or ruler for scale, and date the photo.",
   "Compare to last year's photos -- growth is what matters, not existence.",
   "Look for bulging, soft spots or staining, which suggest moisture behind the finish.",
   "Report anything significant to the builder in writing before your warranty ends."],
  "New-construction settling guidance.",
  priority="normal", mins=45, cost=0),

T("ext-pressure-wash", "Pressure wash driveway, walkways and exterior", "Exterior & Roof", annually(2, 20),
  "Florida humidity grows algae and mildew on every north-facing surface. Beyond looks, biological growth holds "
  "moisture against your finishes and makes concrete slick and dangerous.",
  ["Pressure wash driveway, sidewalk, lanai deck and any pavers.",
   "Use LOW pressure plus a cleaning solution on stucco and painted surfaces -- high pressure damages them.",
   "Treat mildew on the shaded north side with a bleach or oxygen-bleach solution.",
   "Rinse plants beforehand and afterward so runoff doesn't burn them.",
   "Never pressure wash the roof -- soft-wash only, and hire that out."],
  "Standard Florida exterior maintenance.",
  priority="low", mins=180, cost=60),

T("ext-soffit-vents", "Check soffit and roof vents for blockage", "Exterior & Roof", annually(4, 20),
  "Your attic ventilation is what keeps Florida heat and moisture from cooking your roof deck and shingles from "
  "underneath. Blocked soffit vents also drive up your cooling bill.",
  ["Walk the perimeter and look up at the soffit vents.",
   "Clear wasp nests, spider webs, dirt and paint over-spray.",
   "From inside the attic, confirm insulation hasn't been pushed over the soffit vents at the eaves.",
   "Confirm the ridge or off-ridge vents are clear."],
  "Standard attic ventilation maintenance.",
  priority="normal", mins=30, cost=0),

T("ext-attic-inspect", "Inspect attic for leaks, moisture and pests", "Exterior & Roof", on_months([5, 11], 20),
  "The attic tells you about roof leaks months before a ceiling stain appears. Go up in the morning while it's still "
  "cool, and only step on the framing.",
  ["Bring a bright flashlight; step only on joists/trusses.",
   "Look at the underside of the roof deck for dark staining or daylight.",
   "Check around every penetration: plumbing vents, bath fans, the AC lineset.",
   "Look for rodent droppings, chewed wiring or insulation, and wasp nests.",
   "Confirm bath fan ducts actually vent OUTSIDE, not into the attic -- a very common builder defect worth catching under warranty.",
   "Check insulation depth is even and hasn't been disturbed."],
  "Standard attic inspection + Florida moisture guidance.",
  priority="high", mins=45, cost=0),

T("ext-repaint", "Repaint or reseal exterior", "Exterior & Roof", every(2555),
  "Florida UV and driving rain are brutal on exterior finishes. Seven years is a realistic repaint interval here, and "
  "the paint film is a big part of your water barrier.",
  ["Get 3 quotes; ask about pressure washing, caulk replacement and primer on bare spots.",
   "Confirm they'll use a quality elastomeric or acrylic rated for Florida.",
   "Keep the color codes and the leftover paint for touch-ups."],
  "Florida exterior finish lifespan guidance.",
  priority="low", diy=False, mins=240, cost=5000),

T("ext-driveway-seal", "Seal driveway or pavers", "Exterior & Roof", every(1095),
  "Sealing keeps oil stains from soaking in, stops paver sand from washing out, and slows the fading that Florida sun "
  "causes. Not urgent on a new driveway, hence the 3-year cycle.",
  ["Pressure wash and let dry fully (48 hours).",
   "Re-sand paver joints with polymeric sand if applicable.",
   "Apply sealer per label; watch the weather -- you need a dry window.",
   "Keep cars off for the full cure time."],
  "Standard concrete/paver maintenance.",
  priority="low", mins=240, cost=350),

T("ext-window-weeps", "Clear window tracks and weep holes", "Exterior & Roof", on_months([4, 10], 28),
  "Those little slots at the bottom of the exterior window frame are drains. When they clog with dirt and dead bugs, "
  "the track fills during a Florida downpour and water comes in over the sill.",
  ["Vacuum every window track and sill.",
   "Find the weep holes on the exterior bottom of each frame.",
   "Clear them with a thin wire or compressed air, then pour a cup of water into the track and confirm it drains out.",
   "Never caulk these shut.",
   "Also clear sliding glass door tracks and check the rollers."],
  "Florida window water-intrusion prevention.",
  priority="normal", mins=45, cost=0),

# ==========================================================================
# SCREENED LANAI
# ==========================================================================
T("lanai-screen-clean", "Clean lanai screens and frame", "Lanai & Screens", on_months([3, 10], 8),
  "Screen mesh collects pollen, dust and algae that both blocks airflow and holds moisture against the aluminum "
  "frame, accelerating corrosion at the fasteners.",
  ["Rinse screens from the inside out with a garden hose (low pressure only -- a pressure washer will blow the mesh out).",
   "Use a soft brush with mild soap on the frame and any algae.",
   "Clean the top track and the screen door.",
   "Rinse thoroughly and let dry."],
  "Standard Florida screen enclosure maintenance.",
  priority="low", mins=90, cost=10, requires="screenedLanai"),

T("lanai-screen-inspect", "Inspect lanai screen for tears and loose spline", "Lanai & Screens", on_months([3, 10], 8),
  "One small tear becomes a large one fast under wind load, and it's the entry point for every mosquito and lizard in "
  "the county. Spline that has shrunk out of its channel is the usual cause.",
  ["Walk the inside perimeter looking for tears, holes and sagging panels.",
   "Check that the rubber spline is fully seated in its channel all the way around each panel.",
   "Push spline back in with a spline roller, or patch small tears with screen repair tape.",
   "Budget for re-screening a panel if it's badly stretched -- it's inexpensive per panel."],
  "Standard Florida screen enclosure maintenance.",
  priority="normal", mins=30, cost=20, requires="screenedLanai"),

T("lanai-hardware", "Check lanai frame anchors and fasteners", "Lanai & Screens", annually(4, 8),
  "The cage is anchored to the slab and often to the house. In salt air and Florida rain the screws corrode, and a "
  "cage with failing anchors is the first thing to go in a hurricane.",
  ["Inspect the anchor bolts where the frame meets the slab for rust or lifting.",
   "Check the fasteners where the cage attaches to the house.",
   "Look for bent or separated frame members.",
   "Replace corroded screws with stainless.",
   "Report structural issues to the builder if you're still in warranty."],
  "Florida screen enclosure / hurricane preparedness guidance.",
  priority="normal", mins=30, cost=15, requires="screenedLanai"),

T("lanai-door-tracks", "Clean and lubricate sliding door tracks", "Lanai & Screens", every(90),
  "Grit in the track destroys the rollers, and a slider that takes two hands to open is a slider whose rollers are "
  "already going. Also a security issue if it doesn't latch cleanly.",
  ["Vacuum the track thoroughly, then wipe with a damp cloth.",
   "Apply a dry silicone lubricant to the track -- not grease or oil, which attract grit.",
   "Test the door: it should glide with one finger.",
   "Confirm the latch engages fully and the security bar/pin works.",
   "Clear the track's weep holes so rain drains out."],
  "Standard sliding door maintenance.",
  priority="low", mins=20, cost=10),

# ==========================================================================
# PEST & TERMITE  (Florida-critical)
# ==========================================================================
T("pest-termite-bond", "Renew termite bond / soil treatment warranty", "Pest & Termite",
  annually(7, 15),
  "Your builder almost certainly had the soil pre-treated for termites, and that treatment came with a warranty that "
  "must be renewed -- usually annually, and usually starting at the one-year mark. If you let it lapse, reinstating it "
  "costs far more than the renewal. Formosan and subterranean termites are a genuine, expensive Florida threat.",
  ["Find the termite pre-treatment certificate in your closing documents -- it names the pest control company.",
   "Call that company and confirm: what does the bond cover (damage repair, or re-treatment only)? When is renewal due? What does it cost?",
   "Renew before the anniversary date.",
   "If you can't find the certificate, call your builder's warranty department and ask for a copy.",
   "Keep every renewal receipt -- continuous coverage is what matters."],
  "Florida new-construction soil pre-treatment warranties require annual renewal.",
  priority="critical", diy=False, mins=45, cost=175),

T("pest-termite-inspect", "Annual termite / WDO inspection", "Pest & Termite", annually(7, 20),
  "A Wood Destroying Organism inspection is what actually finds an active infestation. In Florida this is not "
  "optional maintenance -- it's the difference between a treatment and a structural repair.",
  ["Schedule a licensed WDO inspection (often included with your termite bond -- ask first).",
   "Have them check the slab perimeter, attic, garage, lanai and any wood framing.",
   "Get the written report.",
   "Address any conducive conditions they flag (mulch contact, moisture, wood-to-ground contact)."],
  "Florida WDO inspection standard practice.",
  priority="critical", diy=False, mins=60, cost=100),

T("pest-quarterly", "Quarterly pest control service", "Pest & Termite", every(90),
  "Florida's pest pressure is year-round and relentless -- ants, roaches, palmetto bugs, spiders, the occasional "
  "scorpion. Quarterly exterior treatment is the standard here and it's cheaper than reacting.",
  ["Confirm your quarterly service is scheduled (or set one up -- typically $40-70 per visit).",
   "Ask them to treat the perimeter, eaves, lanai and garage.",
   "Point out any activity you've seen since the last visit.",
   "Ask about their guarantee for interior re-treats between visits."],
  "Standard Florida pest management practice.",
  priority="normal", diy=False, mins=45, cost=55),

T("pest-entry-seal", "Seal pest entry points", "Pest & Termite", annually(10, 25),
  "Rodents get through a hole the size of a dime and Florida's cool season is when they come inside. The usual routes "
  "are the AC lineset penetration, plumbing penetrations, garage door seals and soffit gaps.",
  ["Walk the exterior looking for gaps around every pipe, wire and duct penetration.",
   "Seal small gaps with copper mesh plus sealant; use hardware cloth for larger ones.",
   "Check the garage door bottom seal and side weatherstripping for gaps and daylight.",
   "Confirm soffit and gable vents have intact screening.",
   "Check where the AC refrigerant line enters the wall -- it's very often left unsealed."],
  "Standard pest exclusion practice.",
  priority="normal", mins=90, cost=35),

T("pest-mulch-check", "Verify 6-inch clearance around foundation", "Pest & Termite", on_months([3, 9], 25),
  "Any soil, mulch or vegetation touching the stucco lets termites bypass the treated soil barrier entirely -- and it "
  "voids some termite bonds.",
  ["Walk the full perimeter.",
   "Pull mulch and soil back to leave 6 inches of bare foundation visible.",
   "Trim shrubs back to 3 feet from the wall.",
   "Remove any wood, cardboard or debris stored against the house.",
   "Move firewood well away from the structure."],
  "Florida termite guidance: maintain a 6-inch mulch-free zone.",
  priority="high", mins=45, cost=0),

# ==========================================================================
# STORM & HURRICANE  (Florida-critical)
# ==========================================================================
T("storm-season-prep", "Hurricane season preparation", "Storm & Hurricane", annually(5, 15),
  "Atlantic hurricane season runs June 1 to November 30. The whole point of doing this in mid-May is that plywood, "
  "batteries, gas cans and generators are all available and reasonably priced, which stops being true the moment a "
  "cone points at Florida.",
  ["Test that every hurricane shutter or panel is present, fits, and that you have all the hardware. Do a dry fit now.",
   "Restock the kit: 1 gallon of water per person per day for 7 days, non-perishable food, manual can opener, "
   "batteries, flashlights, NOAA weather radio, first aid, cash, phone power banks, pet supplies, prescriptions.",
   "Fill propane tanks and confirm the generator (if any) starts and has fresh fuel and oil.",
   "Confirm your evacuation zone and route on the county emergency management site.",
   "Photograph or video every room and the exterior for insurance -- narrate what things are.",
   "Put insurance policy, deed, IDs and this year's inspection reports in a waterproof folder or a cloud drive.",
   "Identify what goes inside from the lanai and yard when a storm is coming."],
  "NOAA / FEMA / Florida Division of Emergency Management guidance; season is June 1 - Nov 30.",
  priority="critical", mins=180, cost=250),

T("storm-shutters-test", "Test hurricane shutters or impact windows", "Storm & Hurricane", annually(4, 25),
  "The standard Florida advice is to confirm your shutters operate now, not when a storm is 48 hours out and every "
  "hardware store within 60 miles is sold out.",
  ["Locate all panels/shutters and confirm none are missing.",
   "Dry-fit at least a few panels; confirm every wingnut, bolt and track is present and not seized.",
   "Lubricate accordion or roll-down tracks.",
   "Label each panel with the window it fits if the builder didn't.",
   "If you have impact glass instead, confirm you have the certification paperwork for your insurance discount."],
  "Florida hurricane preparedness guidance: test shutters before season, not during.",
  priority="high", mins=90, cost=20),

T("storm-inventory", "Update home inventory for insurance", "Storm & Hurricane", annually(5, 20),
  "After a loss, the insurer asks you to prove what you owned. Almost nobody can. A 20-minute video walkthrough is "
  "the single highest-value insurance thing you can do.",
  ["Walk every room with your phone recording video, narrating items and rough values.",
   "Open closets, cabinets and the garage.",
   "Photograph serial numbers and model plates on all major appliances and the HVAC.",
   "Photograph receipts for big-ticket items.",
   "Store it in cloud storage, not just on the phone."],
  "Insurance industry standard loss-documentation guidance.",
  priority="high", mins=45, cost=0),

T("storm-post-check", "Post-storm damage inspection", "Storm & Hurricane", every(365),
  "Run this after any named storm or severe weather event, not just once a year. Insurers care about prompt "
  "reporting, and hidden damage gets much more expensive with time.",
  ["Walk the full exterior perimeter with your phone camera.",
   "Roof from the ground with binoculars: lifted shingles, displaced tiles, damaged vents.",
   "Check the lanai screen, frame and anchors.",
   "Check the AC condenser for debris, bent fins or shifting.",
   "Check soffits, fascia, gutters and the fence.",
   "Look in the attic for new water stains.",
   "Photograph everything with dates before doing any cleanup, and report to insurance promptly."],
  "Florida post-storm / insurance claim guidance.",
  priority="high", mins=45, cost=0),

T("storm-generator", "Service portable generator", "Storm & Hurricane", annually(5, 10),
  "Only relevant if you own one. Ethanol fuel gums up carburetors within months, and a generator that won't start is "
  "the most predictable disappointment in Florida.",
  ["Change the oil and the air filter.",
   "Drain old fuel or run it dry; use fresh fuel with stabilizer.",
   "Start it and run it under load for 20 minutes.",
   "Confirm you have the right extension cords and a safe placement plan -- NEVER in the garage or near windows (carbon monoxide kills people every hurricane season).",
   "If you don't own a generator, disable this task in Settings."],
  "Generator manufacturer maintenance guidance; CPSC CO safety warnings.",
  priority="normal", mins=60, cost=40),

# ==========================================================================
# WARRANTY, INSURANCE & DOCUMENTS  (highest-value items for a new build)
# ==========================================================================
T("warranty-11month", "★ Schedule 11-month builder warranty inspection", "Warranty & Documents",
  once(2027, 5, 28),
  "THE most important item in this entire app. Your builder's one-year workmanship warranty expires July 28, 2027. "
  "Hire an independent inspector around month 10 so you have time to document findings, submit the claim in writing, "
  "and give the builder a reasonable window to respond BEFORE the deadline. Anything found after that date is your "
  "money. A $400 inspection routinely finds thousands in covered defects.",
  ["Book a licensed home inspector with new-construction experience and thermal imaging -- do it in month 10, not month 12.",
   "Ask specifically for thermal imaging and moisture meter readings.",
   "Walk with them and take your own notes.",
   "Also gather your own list beforehand: every sticking door, nail pop, drywall crack, grout gap, running toilet, "
   "loose fixture, bad caulk line, HVAC balance issue and drainage complaint you've noticed all year.",
   "Get the written report with photos."],
  "Florida 11-month builder warranty inspection standard practice: schedule in month 10.",
  priority="critical", diy=False, mins=180, cost=400),

T("warranty-punchlist", "★ Submit builder warranty punch list in writing", "Warranty & Documents",
  once(2027, 6, 15),
  "Verbal requests to a builder are not enforceable. Everything goes through the warranty portal or email, dated, "
  "with photos. Submit well before July 28, 2027 and keep every confirmation.",
  ["Compile the inspector's report plus your own list into one document.",
   "Submit through the builder's official warranty portal, or email with a read receipt.",
   "Attach dated photos for every item.",
   "Keep a copy of the submission and every response.",
   "Follow up in writing every two weeks until items are resolved or formally denied.",
   "If the builder stalls past the warranty date, the written, dated submission is what protects you."],
  "Florida builder warranty claim best practice: document everything in writing with dated photos.",
  priority="critical", mins=120, cost=0),

T("warranty-1yr-expire", "Builder 1-year workmanship warranty EXPIRES", "Warranty & Documents",
  once(2027, 7, 28),
  "Milestone marker. After this date, cosmetic and workmanship defects -- drywall, paint, trim, tile, cabinets, "
  "flooring, most hardware -- become your expense.",
  ["Confirm every submitted warranty item has been resolved or has a written response.",
   "Archive all warranty correspondence permanently.",
   "Note that your 2-year systems and 10-year structural coverage continue."],
  "Standard builder warranty structure (1-year workmanship).",
  priority="high", mins=15, cost=0),

T("warranty-2yr-expire", "Builder 2-year systems warranty EXPIRES", "Warranty & Documents",
  once(2028, 7, 28),
  "Your plumbing, electrical, HVAC ductwork and mechanical systems coverage typically ends at two years. Worth doing "
  "a focused systems check a couple of months beforehand.",
  ["Two months before this date, test every system deliberately: water pressure at all fixtures, all outlets and "
   "switches, HVAC airflow at every register, all drains.",
   "Submit anything found in writing before the deadline."],
  "Standard builder warranty structure (2-year systems).",
  priority="high", mins=60, cost=0),

T("warranty-appliances-register", "Register all appliance warranties", "Warranty & Documents",
  once(2026, 9, 18),
  "LG and Samsung both want registration, and it makes any warranty claim dramatically less painful. You'll also need "
  "the model and serial numbers on hand for parts and for your insurance inventory.",
  ["Photograph the model and serial plate on: LG washer, LG dryer, LG refrigerator, Samsung range, Samsung cooktop, Samsung microwave, dishwasher, water heater.",
   "Register the LG appliances at lg.com/us/support/register.",
   "Register the Samsung appliances at samsung.com/us/support/register.",
   "Register the State water heater at statewaterheaters.com.",
   "Record every model/serial number in this app's Settings > Notes, and keep the purchase receipts.",
   "Note each one's warranty expiration."],
  "Manufacturer registration guidance.",
  priority="high", mins=60, cost=0),

T("docs-homestead", "★ File Florida Homestead Exemption", "Warranty & Documents",
  once(2027, 1, 15),
  "The hard deadline is MARCH 1, 2027 for the 2027 tax year. Florida's homestead exemption takes up to $50,000 off "
  "your assessed value AND locks in the Save Our Homes 3% annual assessment cap. Missing it costs you real money "
  "every year and you cannot get it retroactively. File in January so a document problem doesn't run you past the deadline.",
  ["Go to your county Property Appraiser's website and find the homestead exemption application (most allow online filing).",
   "You must have owned and occupied the home as your permanent residence as of January 1, 2027 -- you moved in July 2026, so you qualify.",
   "Have ready: recorded deed or tax parcel number, Florida driver's license with THIS address, Florida vehicle registration, voter registration or declaration of domicile, and Social Security numbers for all owners.",
   "If your driver's license still shows an old address, update it FIRST -- this is the usual reason applications get rejected.",
   "Submit and save the confirmation.",
   "Also ask about additional exemptions you may qualify for (veteran, senior, disability)."],
  "Florida Statute 196.011: homestead exemption filing deadline is March 1.",
  priority="critical", mins=60, cost=0),

T("docs-wind-mitigation", "Get wind mitigation inspection for insurance discount", "Warranty & Documents",
  once(2026, 10, 15),
  "A one-time $75-150 inspection that documents your roof attachment, roof-to-wall connections, opening protection "
  "and roof geometry. On a new Florida build these features are all current-code, and the premium credits are often "
  "$500-1,500 per year. It typically pays for itself in the first month.",
  ["Hire a licensed wind mitigation inspector (form OIR-B1-1802).",
   "Send the completed form to your homeowners insurance agent and ask them to re-rate the policy.",
   "Ask specifically whether all applicable credits were applied.",
   "The form is generally valid for 5 years -- calendar the renewal.",
   "Keep a copy with your insurance documents."],
  "Florida OIR uniform mitigation verification inspection (form OIR-B1-1802).",
  priority="high", diy=False, mins=90, cost=125),

T("docs-insurance-review", "Review homeowners insurance policy", "Warranty & Documents", annually(6, 1),
  "Florida's insurance market is volatile and dwelling replacement costs have moved a lot. Review before hurricane "
  "season, when you still have time to make changes -- most insurers freeze binding once a storm is in the box.",
  ["Confirm dwelling coverage still reflects current rebuild cost, not market value.",
   "Check your hurricane/windstorm deductible -- it's usually a PERCENTAGE (2-5%) of dwelling coverage, not a flat amount. Know the dollar figure.",
   "Confirm you have flood coverage or have made an informed decision not to -- standard policies never cover flood, and much of Florida floods outside mapped zones.",
   "Verify personal property, loss of use and liability limits.",
   "Confirm your wind mitigation credits are still applied.",
   "Shop it against at least two other carriers."],
  "Florida insurance market guidance.",
  priority="high", mins=90, cost=0),

T("docs-organize", "Organize home documents and manuals", "Warranty & Documents",
  once(2026, 9, 25),
  "One folder, physical and digital, with everything. You will want this at the worst possible moment -- a leak, a "
  "claim, a warranty dispute -- and hunting for it then is miserable.",
  ["Create a cloud folder plus a physical file.",
   "Collect: closing documents, deed, survey, builder warranty booklet, termite pre-treatment certificate, "
   "all appliance manuals and receipts, HVAC install paperwork, insurance policy, permits.",
   "Photograph every model/serial plate in the house.",
   "Record contractor contacts: builder warranty line, Natural Air, plumber, electrician, pest control, roofer.",
   "Put the account numbers and key dates into this app's Settings > Notes."],
  "Homeowner records best practice.",
  priority="high", mins=120, cost=0),

T("docs-contractor-list", "Review and update trusted contractor list", "Warranty & Documents", annually(9, 15),
  "Find your plumber before you need a plumber. Emergency-rate strangers found at 11pm are how people get badly "
  "overcharged for bad work.",
  ["Keep current numbers for: HVAC (Natural Air), plumber, electrician, roofer, pest control, handyman, "
   "irrigation, garage door, appliance repair.",
   "Verify each is still licensed and insured (check at myfloridalicense.com).",
   "Note who you'd actually call again and who you wouldn't.",
   "Store the list in this app's Settings > Notes and in your phone contacts."],
  "Homeowner best practice.",
  priority="low", mins=45, cost=0),

# ==========================================================================
# INTERIOR
# ==========================================================================
T("int-nailpops", "Touch up drywall nail pops and settling cracks", "Interior", annually(6, 25),
  "Completely normal in the first two years as framing lumber dries and the house settles. Do a full pass right "
  "before your 11-month inspection so the builder fixes them on their dime.",
  ["Walk every room in raking light (a flashlight held flat against the wall reveals them).",
   "Mark nail pops, corner bead cracks and drywall seam cracks with painter's tape.",
   "Check above doors and windows and at ceiling corners -- the usual spots.",
   "Before month 11: photograph and submit to the builder as warranty items.",
   "After warranty: set the nail, spackle, sand, prime, touch up paint."],
  "New-construction settling; builder warranty best practice.",
  priority="normal", mins=90, cost=25),

T("int-caulk-wet", "Re-caulk tubs, showers and sinks", "Interior", annually(8, 10),
  "Failed caulk in a shower lets water into the wall cavity, and in Florida humidity that becomes mold fast. The "
  "corners and the tub-to-tile joint go first.",
  ["Inspect all wet-area caulk: tub/shower surrounds, tub-to-floor, sink backsplashes, toilet base.",
   "Look for gaps, cracks, mildew staining or caulk pulling away.",
   "Cut out failed caulk completely, clean with rubbing alcohol, dry fully.",
   "Apply 100% silicone caulk rated for kitchen and bath (not latex) and tool it smooth.",
   "Keep the shower dry for 24 hours."],
  "Standard wet-area maintenance; elevated priority in Florida humidity.",
  priority="normal", mins=90, cost=15),

T("int-grout", "Inspect and seal tile grout", "Interior", annually(8, 20),
  "Unsealed grout absorbs water and stains, and in showers it's the path to the substrate. Sealing is cheap and takes "
  "an afternoon.",
  ["Test whether grout needs sealing: drop water on it -- if it darkens and soaks in, it needs sealer.",
   "Clean grout thoroughly and let it dry 24 hours.",
   "Apply penetrating grout sealer with an applicator bottle; wipe excess off the tile before it hazes.",
   "Repair any cracked or missing grout first.",
   "Prioritize showers and the kitchen floor."],
  "Standard tile maintenance.",
  priority="low", mins=120, cost=30),

T("int-bathfans", "Clean bathroom exhaust fans", "Interior", on_months([4, 10], 18),
  "In Florida these fans are your primary mold defense. A dust-blanketed fan moves almost no air, and most people "
  "have never once cleaned theirs.",
  ["Kill power at the breaker.",
   "Pull the grille down (it usually squeezes off spring clips) and wash it in the sink.",
   "Vacuum the fan blades and housing with a brush attachment.",
   "Confirm the fan actually pulls -- a square of toilet paper should stick to the grille when running.",
   "Verify from the attic that the duct vents OUTSIDE, not into the attic space.",
   "Run the fan for 20 minutes after every shower."],
  "Florida humidity / mold prevention guidance.",
  priority="normal", mins=40, cost=0),

T("int-ceiling-fans", "Clean ceiling fans and check direction", "Interior", every(90),
  "Dusty blades throw dust around the room and can make a fan wobble. The seasonal direction change is a real "
  "comfort and efficiency gain.",
  ["Wipe blades top and bottom (an old pillowcase slipped over each blade catches the dust).",
   "Tighten the blade screws and the canopy -- wobble is usually just loose screws.",
   "Summer: blades should turn COUNTER-CLOCKWISE, pushing air down.",
   "Winter: CLOCKWISE on low, pulling air up.",
   "Confirm the light kit bulbs work."],
  "Standard ceiling fan maintenance.",
  priority="low", mins=30, cost=0),

T("int-humidity", "Check indoor humidity levels", "Interior", every(60),
  "Florida's whole battle is moisture. Keep indoor relative humidity between 45-55%. Above 60% you get mold, dust "
  "mites and that clammy feel; below 35% you get static and wood shrinkage.",
  ["Put a cheap hygrometer in the main living area and one in the primary bedroom.",
   "Read them and log the number in this task's notes.",
   "If consistently above 60%: run the AC fan on AUTO not ON, use bath and kitchen exhaust fans, "
   "consider a dehumidifier, and have the AC checked for oversizing or short cycling.",
   "Check for condensation on windows and on AC supply vents -- both are warning signs."],
  "Florida humidity/mold management guidance (target 45-55% RH).",
  priority="normal", mins=10, cost=0),

T("int-doors-hardware", "Tighten and lubricate doors, hinges and cabinet hardware", "Interior", annually(9, 25),
  "New-construction settling causes doors to bind and latch poorly within the first year. Cabinet screws work loose "
  "from daily use. This is a satisfying hour that makes the whole house feel tight again.",
  ["Tighten every cabinet door and drawer pull, and every hinge screw.",
   "Adjust cabinet door hinges so the doors line up evenly.",
   "Tighten interior and exterior door hinge screws; use a longer screw in the top hinge if a door sags.",
   "Lubricate hinges with a dry silicone or white lithium spray.",
   "Lubricate deadbolts and locksets with graphite or a dry lubricant -- not oil.",
   "Adjust strike plates on any door that doesn't latch cleanly."],
  "New-construction settling; standard hardware maintenance.",
  priority="low", mins=90, cost=15),

T("int-weatherstrip", "Check door and window weatherstripping", "Interior", annually(11, 20),
  "You're paying to cool air that leaks straight out. On a Florida slab home, the front and garage entry doors are "
  "usually the worst offenders.",
  ["Close each exterior door on a dollar bill -- if it pulls out freely, the seal is weak there.",
   "Look for daylight around closed doors, especially at the bottom corners.",
   "Check the door sweep at the bottom of each exterior door.",
   "Replace compressed or torn weatherstripping.",
   "Check the garage door's bottom seal and side stops."],
  "Standard energy-efficiency maintenance.",
  priority="low", mins=45, cost=35),

T("int-carpet-clean", "Deep clean carpets and rugs", "Interior", annually(1, 20),
  "Florida sand tracks in relentlessly and grinds carpet fibers. Annual extraction cleaning is what keeps carpet from "
  "looking five years old at year two -- and some carpet warranties require documented professional cleaning.",
  ["Check your carpet warranty -- many require professional hot-water extraction every 12-18 months to stay valid.",
   "Hire a professional or rent an extractor.",
   "Vacuum thoroughly first.",
   "Keep receipts if the warranty requires proof.",
   "Add walk-off mats at every exterior door to cut how much sand gets in."],
  "Carpet manufacturer warranty requirements.",
  priority="low", diy=False, mins=180, cost=200),

T("int-dryer-area", "Check laundry room and garage for moisture and mildew", "Interior", every(90),
  "Enclosed Florida garages and laundry rooms sit warm and humid. Mildew starts on the concrete and the lowest few "
  "inches of drywall where nobody looks.",
  ["Check the lower drywall and baseboards in the laundry room and garage for staining or softness.",
   "Look behind and under the washer and dryer.",
   "Check stored cardboard boxes for softness or musty smell -- they're an early indicator and also a roach habitat.",
   "Improve ventilation or add a small dehumidifier if it's persistently damp.",
   "Move stored items off the floor onto shelves or pallets."],
  "Florida humidity/mold management guidance.",
  priority="normal", mins=20, cost=0)

# ==========================================================================
# OPTIONAL SYSTEMS
# This home doesn't have these today, so every task below is gated behind a
# feature flag that's currently OFF -- they stay invisible until you flip the
# matching switch in Settings. They're here so that if you add a pool, a
# softener, or a generator later, the schedule is already written.
# ==========================================================================

# ---- Pool / spa ----
T("pool-chemistry", "Test and balance pool chemistry", "Pool & Spa", every(7),
  "Unbalanced water etches plaster, corrodes the heater and pump seals, and stops sanitizing. Florida heat and rain "
  "swing the numbers fast, so weekly is the floor, not the ideal.",
  ["Test free chlorine (1-3 ppm), pH (7.4-7.6), total alkalinity (80-120 ppm), cyanuric acid (30-50 ppm).",
   "Adjust one thing at a time and retest after circulation.",
   "Check calcium hardness monthly (200-400 ppm).",
   "Log the readings in this task's notes so you can see trends."],
  "Standard residential pool care guidance.",
  priority="high", mins=20, cost=15, requires="pool"),

T("pool-baskets", "Empty skimmer and pump baskets", "Pool & Spa", every(7),
  "A clogged basket starves the pump, which runs hot and can burn out the motor seal -- a several-hundred-dollar "
  "failure caused by a two-minute chore.",
  ["Turn the pump OFF before opening the pump lid.",
   "Empty the skimmer basket(s) and the pump strainer basket.",
   "Rinse and reseat; check the pump lid O-ring and lubricate it if dry.",
   "Restore the pump and confirm the basket fills with water and there's no air in the lid."],
  "Standard pool equipment maintenance.",
  priority="normal", mins=10, cost=0, requires="pool"),

T("pool-brush-vac", "Brush and vacuum the pool", "Pool & Spa", every(7),
  "Algae takes hold on surfaces the circulation doesn't reach -- steps, corners, behind ladders. Brushing is what "
  "actually prevents it; chlorine alone doesn't.",
  ["Brush walls, steps and the waterline, working toward the main drain.",
   "Vacuum debris off the floor.",
   "Skim the surface.",
   "Empty the pool cleaner's bag if you have one."],
  "Standard pool care guidance.",
  priority="normal", mins=40, cost=0, requires="pool"),

T("pool-filter-clean", "Clean pool filter", "Pool & Spa", every(90),
  "Rising pressure on the filter gauge means restricted flow. Cleaning restores turnover and cuts pump run time.",
  ["Note the clean starting pressure; clean whenever it rises 8-10 psi above that.",
   "Cartridge: remove and hose the pleats out; soak in filter cleaner annually.",
   "Sand/DE: backwash and rinse, then recharge DE if applicable.",
   "Check O-rings and lubricate with silicone before reassembling."],
  "Pool filter manufacturer guidance.",
  priority="normal", mins=60, cost=25, requires="pool"),

T("pool-equipment-service", "Professional pool equipment service", "Pool & Spa", annually(3, 5),
  "An annual look at the pump, heater, salt cell and plumbing catches the small leaks and worn seals that turn into "
  "equipment-pad replacements.",
  ["Have the pump motor bearings, seals and impeller checked.",
   "Have the salt cell inspected and cleaned if you have one.",
   "Check the heater, valves and plumbing for leaks.",
   "Confirm bonding and GFCI protection at the equipment pad."],
  "Pool equipment manufacturer guidance.",
  priority="normal", diy=False, mins=90, cost=180, requires="pool"),

# ---- Septic ----
T("septic-inspect", "Septic system inspection", "Septic & Well", annually(2, 10),
  "An annual look at sludge and scum depth is what tells you when pumping is actually needed. A failed drain field "
  "is a five-figure repair, and it always announces itself first.",
  ["Have a licensed septic contractor measure sludge and scum layers.",
   "Have them check baffles, the tank lid and the outlet filter.",
   "Ask them to inspect the drain field for wet spots or odor.",
   "Keep the report; it establishes your pumping interval."],
  "EPA / Florida DOH septic guidance: inspect annually.",
  priority="high", diy=False, mins=60, cost=175, requires="septic"),

T("septic-pump", "Pump septic tank", "Septic & Well", every(1095),
  "Every 3-5 years for a typical household. Skipping it lets solids reach the drain field, which is the part you "
  "cannot cheaply replace.",
  ["Schedule a licensed pumper.",
   "Have them clean the outlet filter while the tank is open.",
   "Keep the receipt -- some counties require records.",
   "Don't drive or park over the tank or drain field, ever."],
  "EPA guidance: pump every 3-5 years for typical household use.",
  priority="high", diy=False, mins=120, cost=450, requires="septic"),

# ---- Well ----
T("well-water-test", "Annual well water quality test", "Septic & Well", annually(3, 15),
  "Private wells are not regulated or tested by anyone but you. Bacteria, nitrates and pH shift over time, and in "
  "Florida shallow aquifers respond quickly to surface conditions.",
  ["Order a test kit from your county health department or a certified lab.",
   "Test at minimum for coliform bacteria, nitrates, pH and total dissolved solids.",
   "Test after any flooding event regardless of schedule.",
   "Keep results to track trends."],
  "EPA / Florida DOH private well guidance: test annually.",
  priority="critical", mins=45, cost=90, requires="well"),

T("well-pressure-tank", "Check well pressure tank and switch", "Septic & Well", annually(3, 20),
  "A waterlogged pressure tank makes the pump short-cycle, which destroys the pump motor. You can hear it: the pump "
  "kicking on and off every few seconds while a tap runs.",
  ["Watch the pressure gauge while running water -- the pump should cycle slowly, not rapidly.",
   "With the pump off and system drained, check the tank's air charge (2 psi below cut-in pressure).",
   "Look for corrosion or leaks at the tank and the pressure switch.",
   "Call a well contractor if it's short-cycling."],
  "Well system manufacturer guidance.",
  priority="high", mins=30, cost=0, requires="well"),

# ---- Water softener / whole-house filter ----
T("softener-salt", "Check water softener salt level", "Plumbing", every(30),
  "If the brine tank runs dry the softener stops regenerating and hard water goes straight through, scaling your "
  "water heater and fixtures without any obvious signal.",
  ["Open the brine tank; salt should sit above the water line, roughly two-thirds full.",
   "Top up with the salt type your unit specifies (pellets vs. crystals matters).",
   "Break up any 'salt bridge' -- a hard crust that leaves an air gap under it.",
   "Note your usage rate so you can buy ahead."],
  "Water softener manufacturer guidance.",
  priority="normal", mins=10, cost=25, requires="waterSoftener"),

T("softener-service", "Clean brine tank and service softener", "Plumbing", annually(5, 25),
  "Sediment and salt mush accumulate in the bottom of the brine tank and eventually foul the injector, so the unit "
  "quietly stops softening.",
  ["Let the salt run low, then scoop out the remaining salt and sludge.",
   "Wash the tank with soapy water and rinse.",
   "Clean or replace the brine well screen and check the float.",
   "Sanitize the resin bed per the manual.",
   "Verify hardness with a test strip before and after."],
  "Water softener manufacturer guidance.",
  priority="normal", mins=90, cost=30, requires="waterSoftener"),

T("filter-cartridge", "Replace whole-house filter cartridge", "Plumbing", every(180),
  "A spent sediment cartridge restricts flow to the whole house and can start shedding what it caught.",
  ["Shut the inlet valve and relieve pressure with the housing's red button.",
   "Unscrew the housing with the supplied wrench, dump and rinse it.",
   "Fit the new cartridge; lubricate the housing O-ring with silicone grease.",
   "Reassemble, open the valve slowly, and check for leaks.",
   "Write the date on the housing with a marker."],
  "Whole-house filter manufacturer guidance.",
  priority="normal", mins=25, cost=35, requires="waterSoftener"),

# ---- Gas appliances ----
T("gas-inspection", "Gas line and appliance connection inspection", "Electrical & Safety", annually(10, 5),
  "Flexible connectors age and gas fittings can loosen. A licensed tech with a gas sniffer finds what you can't.",
  ["Have a licensed plumber or gas tech leak-test all connections and appliance connectors.",
   "Ask them to check flue draft and combustion on every gas appliance.",
   "Confirm shutoff valves at each appliance and at the meter work.",
   "Learn where the main gas shutoff is and keep the wrench with it."],
  "Gas utility / appliance manufacturer safety guidance.",
  priority="critical", diy=False, mins=60, cost=140, requires="gasAppliances"),

T("gas-co-detectors", "Test carbon monoxide detectors", "Electrical & Safety", every(30),
  "With gas appliances, CO detection isn't optional. CO is odorless and the symptoms mimic flu, which is exactly why "
  "it kills people in their sleep.",
  ["Press TEST on every CO alarm.",
   "Confirm you have one on every level and near sleeping areas.",
   "Check the manufacture date -- CO sensors expire in 7-10 years regardless of battery.",
   "Never run a generator, grill or car in the garage."],
  "NFPA 720 / CPSC guidance.",
  priority="critical", mins=10, cost=0, requires="gasAppliances"),

# ---- Fireplace ----
T("fireplace-inspect", "Chimney inspection and sweep", "Interior", annually(10, 12),
  "Creosote buildup is what causes chimney fires. Even light seasonal use in Florida still deposits it, and the cap "
  "and flashing are common water-entry points.",
  ["Hire a CSIA-certified chimney sweep for a Level 1 inspection.",
   "Have the flue swept if there's measurable creosote.",
   "Have them check the cap, crown, flashing and damper.",
   "For a gas log set, have the logs, burner and venting inspected instead."],
  "CSIA / NFPA 211: inspect annually.",
  priority="high", diy=False, mins=90, cost=200, requires="fireplace"),

T("fireplace-damper", "Check fireplace damper and firebox", "Interior", annually(11, 15),
  "A damper left open is a hole in your building envelope -- you're paying to cool the whole neighborhood. A stuck "
  "one is a smoke problem.",
  ["Open and close the damper fully; it should move freely and seal.",
   "Look up the flue with a flashlight for obstructions or nesting.",
   "Check firebox brick and mortar for cracks.",
   "Confirm the damper is closed and latched when not in use."],
  "Standard fireplace maintenance.",
  priority="low", mins=20, cost=0, requires="fireplace")

# --------------------------------------------------------------------------
# Build / merge
# --------------------------------------------------------------------------


def main():
    existing = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, "r", encoding="utf-8") as f:
                prev = json.load(f)
            for t in prev.get("tasks", []):
                existing[t["id"]] = t
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ! Could not read existing {OUT} ({e}); starting fresh.")

    seen = set()
    out_tasks = []
    for i, t in enumerate(TASKS):
        if t["id"] in seen:
            raise SystemExit(f"Duplicate task id: {t['id']}")
        seen.add(t["id"])

        prior = existing.get(t["id"])
        task = dict(t)
        if prior:
            # preserve user state
            task["nextDue"] = prior.get("nextDue") or first_due(t["schedule"], i)
            task["lastCompleted"] = prior.get("lastCompleted")
            task["enabled"] = prior.get("enabled", True)
            task["notes"] = prior.get("notes", "")
            task["timesCompleted"] = prior.get("timesCompleted", 0)
        else:
            task["nextDue"] = first_due(t["schedule"], i)
            task["lastCompleted"] = None
            task["enabled"] = True
            task["notes"] = ""
            task["timesCompleted"] = 0
        out_tasks.append(task)

    out_tasks.sort(key=lambda x: (x["nextDue"], x["title"]))

    doc = {
        "version": 1,
        "generatedAt": TODAY.isoformat(),
        "home": HOME,
        "tasks": out_tasks,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    cats = {}
    for t in out_tasks:
        cats[t["category"]] = cats.get(t["category"], 0) + 1

    print(f"Wrote {OUT}")
    print(f"  {len(out_tasks)} tasks across {len(cats)} categories\n")
    for c in sorted(cats, key=lambda k: -cats[k]):
        print(f"  {cats[c]:>3}  {c}")


if __name__ == "__main__":
    main()
