# Generated manually for is_futures addition to Match and Pick

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='is_futures',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='pick',
            name='is_futures',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddIndex(
            model_name='match',
            index=models.Index(fields=['is_futures', 'is_active'], name='betting_mat_is_futu_10b14c_idx'),
        ),
        migrations.AddIndex(
            model_name='pick',
            index=models.Index(fields=['is_futures', '-created_at'], name='betting_pic_is_futu_405788_idx'),
        ),
    ]
