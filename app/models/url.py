import datetime
import random
import string
from peewee import CharField, TextField, BooleanField, DateTimeField, AutoField, IntegerField, ForeignKeyField
from app.database import BaseModel
from app.models.user import User


def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


class URL(BaseModel):
    id = AutoField()
    user_id = IntegerField(null=True)
    short_code = CharField(unique=True, max_length=10, index=True)
    original_url = TextField()
    title = CharField(max_length=255, null=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "urls"
