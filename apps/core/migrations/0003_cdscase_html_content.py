from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_cdscase'),
    ]

    operations = [
        migrations.AddField(
            model_name='cdscase',
            name='html_content',
            field=models.TextField(blank=True, default='', help_text='Printable HTML record'),
        ),
    ]
