import datetime
from peewee import CharField, DateTimeField, AutoField, IntegerField, TextField
from app.database import BaseModel


class Event(BaseModel):
    id = AutoField()
    url_id = IntegerField(null=True)
    user_id = IntegerField(null=True)
    event_type = CharField(max_length=50)
    timestamp = DateTimeField(default=datetime.datetime.now)
    details = TextField(null=True)

    class Meta:
        table_name = "events"
