from app import create_app
from app.database import db

app = create_app()
ctx = app.app_context()
ctx.push()

db.execute_sql("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")
db.execute_sql("SELECT setval('urls_id_seq', (SELECT MAX(id) FROM urls))")
db.execute_sql("SELECT setval('events_id_seq', (SELECT MAX(id) FROM events))")

print('Sequences fixed!')
