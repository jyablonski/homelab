import os

from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_or_update_superuser(apps, _schema_editor):
    username = os.getenv("DJANGO_SUPERUSER_USERNAME")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

    if not username or not password:
        return

    user_model = apps.get_model("auth", "User")
    user, _created = user_model.objects.get_or_create(
        username=username,
        defaults={"is_staff": True, "is_superuser": True},
    )
    if not user.is_staff:
        user.is_staff = True
    if not user.is_superuser:
        user.is_superuser = True
    user.password = make_password(password)
    user.save()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_or_update_superuser, migrations.RunPython.noop),
    ]
