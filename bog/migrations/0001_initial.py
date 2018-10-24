# Generated by Django 2.1.2 on 2018-10-17 21:10

import datetime
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
            name='DiceSet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dice', models.CharField(max_length=150, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Play',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('complete', models.BooleanField(default=False)),
                ('score', models.IntegerField(blank=True, default=0)),
                ('time', models.DurationField(blank=True, default=datetime.timedelta(0, 300))),
                ('missed', models.BooleanField(default=False)),
                ('repeats', models.BooleanField(default=False)),
                ('showmaximum', models.BooleanField(default=True)),
                ('minimumwordlength', models.IntegerField(default=3)),
                ('handicap', models.FloatField(default=1.0)),
            ],
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minimumwordlength', models.IntegerField(default=3, null=True)),
                ('handicap', models.FloatField(default=1.0, null=True)),
                ('ignoreduration', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Puzzle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('layout', models.CharField(max_length=25, unique=True)),
                ('createdby', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('diceset', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='bog.DiceSet')),
            ],
        ),
        migrations.CreateModel(
            name='Word',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(max_length=25, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='WordList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('foundtime', models.DurationField(null=True)),
                ('play', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bog.Play')),
                ('word', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='bog.Word')),
            ],
        ),
        migrations.AddField(
            model_name='player',
            name='puzzles',
            field=models.ManyToManyField(through='bog.Play', to='bog.Puzzle'),
        ),
        migrations.AddField(
            model_name='player',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='play',
            name='player',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='bog.Player'),
        ),
        migrations.AddField(
            model_name='play',
            name='puzzle',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bog.Puzzle'),
        ),
        migrations.AddField(
            model_name='play',
            name='words',
            field=models.ManyToManyField(through='bog.WordList', to='bog.Word'),
        ),
    ]