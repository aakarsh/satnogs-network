# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-08-27 11:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0045_auto_20180822_1947'),
    ]

    operations = [
        migrations.AddField(
            model_name='station',
            name='client_version',
            field=models.CharField(blank=True, max_length=10),
        ),
    ]
