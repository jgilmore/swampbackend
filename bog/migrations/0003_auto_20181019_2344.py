# Generated by Django 2.1.2 on 2018-10-19 23:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bog', '0002_diceset_description'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='play',
            options={'ordering': ('-date',)},
        ),
        migrations.AlterField(
            model_name='play',
            name='puzzle',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='bog.Puzzle'),
        ),
        migrations.AlterUniqueTogether(
            name='play',
            unique_together={('player', 'puzzle')},
        ),
        migrations.AlterUniqueTogether(
            name='wordlist',
            unique_together={('play', 'word')},
        ),
    ]
