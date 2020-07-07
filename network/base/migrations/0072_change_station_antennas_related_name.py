# Generated by Django 1.11.29 on 2020-04-26 18:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0071_rename_the_new_antenna_schema'),
    ]

    operations = [
        migrations.AlterField(
            model_name='antenna',
            name='antenna_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='antennas', to='base.AntennaType'),
        ),
    ]
