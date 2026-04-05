import datetime
import re
import random
import string

from peewee import CharField, TextField, IntegerField, DateTimeField, BooleanField
from app.database import BaseModel

URL_REGEX = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

def is_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    return bool(URL_REGEX.match(url.strip()))

def generate_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

class ShortURL(BaseModel):
    code = CharField(unique=True, max_length=10, index=True)
    target = TextField()
    hits = IntegerField(default=0)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'short_urls'
