@echo off
py -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python app.py
pause
