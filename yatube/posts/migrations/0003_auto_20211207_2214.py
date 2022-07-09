# Generated by Django 2.2.19 on 2021-12-07 19:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0002_auto_20211207_2109"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="group",
                to="posts.Group",
            ),
        ),
    ]
