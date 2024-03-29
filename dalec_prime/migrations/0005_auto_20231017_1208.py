# Generated by Django 3.2.21 on 2023-10-17 10:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dalec_prime", "0004_alter_content_id_alter_fetchhistory_id"),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name="content",
            index_together=set(),
        ),
        migrations.AddIndex(
            model_name="content",
            index=models.Index(
                fields=["app", "content_type", "channel", "channel_object"],
                name="content",
            ),
        ),
    ]
