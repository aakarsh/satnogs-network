# Generated by Django 1.11.11 on 2018-12-06 18:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0050_satellite_norad_follow_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='station',
            name='rig',
        ),
        migrations.DeleteModel(
            name='Rig',
        ),
    ]
