from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app2', '0002_afiliado'),
    ]

    operations = [
        migrations.AddField(
            model_name='afiliado',
            name='comision',
            field=models.DecimalField(default=0, max_digits=5, decimal_places=2),
        ),
    ]
