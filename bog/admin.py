from django.contrib import admin
from .models import DiceSet, Word, Puzzle, Play, Player, WordList

# Register your models here.
admin.site.register(DiceSet)
admin.site.register(Word)
admin.site.register(Puzzle)
admin.site.register(Play)
admin.site.register(Player)
admin.site.register(WordList)
