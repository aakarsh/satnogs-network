# Generated by Django 2.2.14 on 2020-07-13 00:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_username_unicode_validator'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='last_name',
            field=models.CharField(blank=True, max_length=150, verbose_name='last name'),
        ),
    ]