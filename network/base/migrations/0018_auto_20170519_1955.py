# Generated by Django 1.10.6 on 2017-05-19 19:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0017_auto_20170321_1046'),
    ]

    operations = [
        migrations.AlterField(
            model_name='antenna',
            name='antenna_type',
            field=models.CharField(choices=[('dipole', 'Dipole'), ('yagi', 'Yagi'), ('helical', 'Helical'), ('parabolic', 'Parabolic'), ('vertical', 'Verical'), ('turnstile', 'Turnstile'), ('quadrafilar', 'Quadrafilar'), ('eggbeater', 'Eggbeater'), ('lindenblad', 'Lindenblad')], max_length=15),
        ),
    ]
