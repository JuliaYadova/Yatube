# Generated by Django 2.2.16 on 2022-01-23 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0007_auto_20220111_1459"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="image",
            field=models.ImageField(
                blank=True, upload_to="posts/", verbose_name="Картинка"
            ),
        ),
    ]
