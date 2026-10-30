# CivicSignal — From Complaints to Action

A runnable Flask + SQLite prototype for the PromptWars × ASTRA civic-impact challenge.

## Features
- Citizen complaint submission with category, address and optional coordinates.
- Automated category suggestion, short summary and explainable priority score.
- Possible duplicate detection using transparent word-overlap and string similarity heuristics.
- Admin triage dashboard with filters, report map and location-frequency hotspots.
- Department assignment, officer field, status workflow and status history.
- Citizen tracking by unique tracking ID.
- 36 synthetic demo reports (seed script); no real personal data.

## Requirements
- Python 3.9+
- Internet connection for Leaflet map tiles and Google Fonts (the rest runs locally).

## Windows PowerShell setup
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python app.py
```
Open `http://127.0.0.1:5000`.

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Main pages
- `/` — landing page
- `/report` — citizen submission
- `/track` — find a complaint by tracking ID
- `/admin` — administrator dashboard
- `/health` — simple health check

## Architecture
- `app.py`: Flask routes, SQLite persistence, AI-style triage heuristics and workflow.
- `templates/`: Jinja HTML pages.
- `static/style.css`: responsive frontend styling.
- `static/app.js`: Leaflet map rendering.
- `seed.py`: creates 36 synthetic reports.

## AI approach and honest limitations
This prototype uses deterministic, explainable heuristics rather than a hosted LLM:
1. **Category suggestion:** keyword rules map report text to a category. A citizen/admin can see the selected category.
2. **Summary:** extracts the first sentence and truncates long text.
3. **Duplicate flag:** compares token Jaccard overlap and `difflib.SequenceMatcher`; same category and nearby coordinates increase the score. It flags a *possible* duplicate, never automatically merges records.
4. **Priority:** transparent keyword/category scoring produces a 0–100 score and a plain-language reason. It is a triage aid, not a safety guarantee.
5. **Hotspots:** dashboard counts exact location strings. The map plots reports only when coordinates are supplied.

Not implemented: production LLM, image understanding, live government integrations, real dispatch, authentication/authorization, geocoding, true spatial clustering, notifications, or automatic duplicate merging. Admin routes are open for local demo use and must be protected before deployment. Demo coordinates and reports are synthetic.

## Demo flow (about 5 minutes)
1. Submit a report such as “An open manhole near the school is a serious danger to pedestrians” with location and coordinates.
2. Show the generated tracking ID, category, summary, priority and explanation.
3. Open `/admin`; show priority queue, map and hotspot counts.
4. Open the report and assign a department/officer; change status to “In Progress”.
5. Open the citizen tracking page and show the status history. Update to “Resolved” and add a resolution note.

## Reset demo database
Stop the server, delete `civicsignal.db`, then run `python seed.py` again.
