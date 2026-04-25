from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_create_superuser"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS source;",
            reverse_sql="DROP SCHEMA IF EXISTS source CASCADE;",
        ),
    ]
