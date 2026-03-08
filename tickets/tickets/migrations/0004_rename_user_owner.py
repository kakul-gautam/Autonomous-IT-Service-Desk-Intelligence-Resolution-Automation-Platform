from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0003_ticket_user'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ticket',
            old_name='user',
            new_name='owner',
        ),
    ]
