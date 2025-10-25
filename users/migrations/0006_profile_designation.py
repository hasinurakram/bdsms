# Generated manually on 2025-10-02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_user_phone_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='designation',
            field=models.CharField(blank=True, help_text='Designation/Role for committee members', max_length=100, null=True),
        ),
    ]
