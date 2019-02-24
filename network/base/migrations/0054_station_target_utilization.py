# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-02-07 17:52
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0053_remove_station_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='station',
            name='target_utilization',
            field=models.IntegerField(blank=True, help_text=b'Target utilization factor for your station', null=True, validators=[django.core.validators.MaxValueValidator(100), django.core.validators.MinValueValidator(0)]),
        ),
    ]