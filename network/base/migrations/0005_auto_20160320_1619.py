# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-20 16:19
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0004_station_horizon'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[(b'Radio', b'Radio'), (b'SDR', b'SDR')], max_length=10)),
                ('rictld_number', models.PositiveIntegerField(blank=True, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='station',
            name='uuid',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name='station',
            name='rig',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.Rig'),
        ),
    ]