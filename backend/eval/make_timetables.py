"""Generates two SYNTHETIC timetable images + hand-written ground truth for the live Gemini check.
These are clean, computer-drawn tables (easy case). Also test 2-3 real, redacted student timetable photos
before quoting accuracy on stage."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SETS = {
    "demo_A": [("Sun", "CS 201 Data Structures", "08:30", "09:30", "Eng 102"),
               ("Sun", "AI 305 Machine Learning", "11:30", "12:30", "IT 214"),
               ("Tue", "CS 250 Databases", "10:00", "11:00", "Eng 110")],
    "demo_B": [("Sun", "AI 454 Natural Language Processing", "10:00", "11:30", "IT 301"),
               ("Mon", "AI 381 MLOps", "12:00", "13:00", "Lab 4"),
               ("Wed", "CS 330 Operating Systems", "14:00", "15:30", "Eng 205")],
}
# demo_C: start time of row 2 is covered by an ink blot and row 1 has no room -> must be flagged, not invented
SETS["demo_C"] = [("Mon", "MATH 241 Linear Algebra", "09:00", "10:00", ""),
                  ("Wed", "PHYS 102 General Physics", "BLOT", "13:00", "Sci 12")]
FULL = {"Sun": "Sunday", "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday"}
for name, rows in SETS.items():
    img = Image.new("RGB", (1100, 140 + 60 * len(rows)), "white")
    d = ImageDraw.Draw(img)
    d.text((30, 25), f"Semester Timetable — Student ({name}, synthetic)", fill="black", font=ImageFont.truetype(FB, 28))
    cols = [30, 200, 620, 760, 900]
    for x, h in zip(cols, ["Day", "Course", "Start", "End", "Room"]):
        d.text((x, 85), h, fill="black", font=ImageFont.truetype(FB, 22))
    for i, r in enumerate(rows):
        y = 135 + 60 * i
        d.line([(25, y - 12), (1075, y - 12)], fill="gray")
        for x, v in zip(cols, (FULL[r[0]],) + r[1:]):
            if v == "BLOT":
                d.text((x, y), "12:00", fill="black", font=ImageFont.truetype(F, 22))
                d.ellipse([x - 8, y - 8, x + 80, y + 34], fill="black")     # unreadable on purpose
            else:
                d.text((x, y), v, fill="black", font=ImageFont.truetype(F, 22))
    img.save(HERE / f"{name}.png")
    truth = [{"weekday": r[0], "course": r[1], "start": None if r[2] == "BLOT" else r[2], "end": r[3],
              "room": r[4] or None} for r in rows]
    (HERE / f"{name}.truth.json").write_text(json.dumps(truth, indent=1))
print("written", [f"{n}.png" for n in SETS])
