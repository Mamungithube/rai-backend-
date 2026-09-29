import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('notification_type', models.CharField(choices=[('system', 'System'), ('comment_reply', 'Comment & Concern Reply'), ('support_reply', 'Support Ticket Reply'), ('betting', 'Betting / Pick of the Day'), ('community', 'Community'), ('general', 'General')], db_index=True, default='general', max_length=30)),
                ('reference_id', models.CharField(blank=True, help_text='e.g. ticket_code or object id', max_length=100, null=True)),
                ('data', models.JSONField(blank=True, default=dict, help_text='Extra payload for deep linking in mobile app')),
                ('is_read', models.BooleanField(db_index=True, default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['user', '-created_at'], name='notificatio_user_id_05b4e3_idx'),
                    models.Index(fields=['user', 'is_read'], name='notificatio_user_id_427618_idx'),
                    models.Index(fields=['user', 'notification_type'], name='notificatio_user_id_502bd6_idx'),
                ],
            },
        ),
    ]
