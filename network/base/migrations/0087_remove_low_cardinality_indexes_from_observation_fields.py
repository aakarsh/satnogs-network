# Generated by Django 3.1.5 on 2021-02-16 00:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0086_add_index_to_observation_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='observation',
            name='archived',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='observation',
            name='audio_zipped',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='observation',
            name='status',
            field=models.SmallIntegerField(default=0),
        ),
    ]