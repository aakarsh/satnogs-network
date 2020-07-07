from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='antenna',
            name='antenna_type',
            field=models.CharField(max_length=15, choices=[('dipole', 'Dipole'), ('yagi', 'Yagi'), ('helical', 'Helical'), ('parabolic', 'Parabolic'), ('vertical', 'Verical')]),
        ),
    ]
