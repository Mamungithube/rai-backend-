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
            name='CommentConcern',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ticket_code', models.CharField(db_index=True, max_length=20, unique=True)),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('replied', 'Replied'), ('closed', 'Closed')], db_index=True, default='pending', max_length=20)),
                ('admin_reply', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('replied_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments_and_concerns', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['user', '-created_at'], name='comment_con_user_id_10df4a_idx'),
                    models.Index(fields=['status', '-created_at'], name='comment_con_status_d76ae9_idx'),
                    models.Index(fields=['ticket_code'], name='comment_con_ticket__cb705d_idx'),
                ],
            },
        ),
    ]
