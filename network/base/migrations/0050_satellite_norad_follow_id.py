# Generated by Django 1.11.11 on 2018-12-04 16:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0049_auto_20180915_1503'),
    ]

    operations = [
        migrations.AddField(
            model_name='satellite',
            name='norad_follow_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
