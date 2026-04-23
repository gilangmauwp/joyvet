from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CdsCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clinic_key', models.CharField(db_index=True, help_text='UUID shared by all staff at this clinic', max_length=36)),
                ('case_id', models.BigIntegerField(help_text='Timestamp-based ID from the CDS tool')),
                ('data', models.JSONField(help_text='Full CDS case object')),
                ('saved_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'CDS Case',
                'verbose_name_plural': 'CDS Cases',
                'ordering': ['-saved_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='cdscase',
            unique_together={('clinic_key', 'case_id')},
        ),
    ]
