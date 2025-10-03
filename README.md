### how start 

```
git clone https://github.com/Krim-code/worklog.git
cd worklog
python -m venv venv
venv/bin/activate
cd config
pip install -r requirements.txt
python manage.py runserver
```

### if you want gen example or drop db


```
python manage.py makemigrations worklog
python manage.py migrate
python manage.py loaddata worklog/fixtures/worktypes.json
python manage.py seed_demo_data --workers=8 --days=10 --entries-per-day=2

```
