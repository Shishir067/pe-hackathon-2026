import datetime
from peewee import CharField, DateTimeField, AutoField
from app.database import BaseModel


class User(BaseModel):
    id = AutoField()
    username = CharField(unique=True, max_length=100)
    email = CharField(unique=True, max_length=200)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "users"
