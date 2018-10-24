from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.core.exceptions import ValidationError

# This model consists of three main parts: users, games, and words.
# games, users, and words are interrelated with a many/many/many relationship
# In addition, there's metadata associated with that relationship, primarily a timespan
# which defines the time after start the puzzle that this particular user found this particular
# word.

# Security:
#   Each user is allowed to get their list of words, and to see which of the words they've found
#   have been found by which other users. IFF the puzzle has been completed by this user, that user
#   is also allowed to see the complete word list, and all the words other users got as well as
#   their own.

# Words are not required in that relationship, as in the case that a user enters a non-existant or
# misspelled word. Also, words may be duplicated if the user enters them twice. This may or may not
# count against the users score.

# The puzzle/user relationship contains completion time if any, and a cached score. It should also
# contain a copy of the game rules (timer or not, etc) that where used to calculate that score. This
# prevents later changes to game rules changing the score, and also allows for user handicapping.


# puzzle. Contains base set of game rules, game geometry (5x5 or 4x4, though others should be
# supported if added.) Also contains creation time & user.

# user. one-to-one with admin/users, and contains handicapping information etc.

# words. Simply a spelling (up to 25 letters) and id. nothing more

# Puzzle/word relationship. Contains no other info, maybe combined with user/puzzle/word.

# user/puzzle/word relationship. Contains the time (interval after game start) of entry.

# user/puzzle relationship. Contains start time, finish interval, game rules, final score.


class DiceSet(models.Model):
    """
    This stores a "set" of dice that are used to generate puzzles. The letters are uppercase, and
    each die is assumed to be exactly SIX letters long. This means that two-letter dice faces are
    stored as one letter here. For instance, 'Q' is assumed to actually be 'Qu'. Other two letter
    combos would have to be implemented the same way. Using lowercase letters, perhaps?

    Be aware that this would of course require modifications to the front end to allow players to
    enter words that would otherwise not be available, and to display 'Q' as 'Qu' etc.

    The geometry is assumed to be square, and there are only two possibilities. 4x4 (length=16*6)
    or 5x5 (length=25*6) Though in theory we can suppport odd (non-square) geometries and
    non-six-sided dice, this is not currently supported.

    description
        A brief description of this set of dice.

    dice
        String conforming to pybogged's expectations. Specifically, only uppercase letters,
        and length must be exactly 96 or exactly 150 for 4x4 or 5x5 games respectively.
    """
    description = models.CharField(max_length=200)
    dice = models.CharField(max_length=25*6, unique=True)

    def save(self, *args, **kwargs):
        if len(self.dice) != 96 and len(self.dice) != 150:
            raise ValidationError("Bad dice length detected:" + str(len(self.dice))
                                  + ". Must be 16 or 25 six sided dice characters in "
                                  "length (either 96 or 150 chars)")

        # Normalize the dice set. Do this by alphabatizing each die, then the set as dice.
        # Doing this insures that sets of dice that are the same (have the same results)
        # are in fact the same string. Note the comparisons here ARE case-sensitive. This isn't
        # important now, as everything is uppercase. But may be important in the future.
        dicelist = [list(self.dice[i:i+6]) for i in range(0, len(self.dice), 6)]
        for die in dicelist:
            die.sort()
        dicelist = ["".join(die) for die in dicelist]
        dicelist.sort()
        self.dice = "".join(dicelist)

        # And finally save the model.
        models.Model.save(self, *args, **kwargs)


class Word(models.Model):
    """
    Stores one word, correctly spelled, all lowercase, with no punctuation (i.e. "aren't" = "arent")
    Note that there is essentially NO other information here. I've even considered using "word" as
    the primary key.
    """
    word = models.CharField(max_length=25, unique=True)

    def __str__(self):
        return self.word + '(' + str(self.pk) + ')'


class Puzzle(models.Model):
    """
    Defines a particular throw of the dice, and a set of rules. This then becomes playable.
    It is REQUIRED to add ALL findable words to the WordList, with player=null and duration=null
    at the time the puzzle is created.

    diceset
        The diceset that was used to create this puzzle. Not required, as puzzles could be created
        directly, or the dice set deleted afterwards.

    layout
        Required to be length 16 or length 25, representing the 4x4 or 5x5 playing grid.
        This field is all that is REALLY required to define a puzzle. All else is details.
    """
    # moved to the "Play" record
    # created = models.DateTimeField(auto_now_add=True)

    # This is to users, instead of players to allow easier creation of puzzles.
    createdby = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # We don't cascade on delete, as this is just for reference.
    # Everything we need to know about the puzzle is stored here.
    diceset = models.ForeignKey(DiceSet, on_delete=models.SET_NULL, null=True)

    layout = models.CharField(max_length=25, unique=True)

    # players = model.ManyToManyField(Player, through='Play')


class Player(models.Model):
    """
    Extra information about a players skill level, handicapping, etc.

    minimumwordlength
        Overrides the puzzle default if set.

    handicap
        Multiply the puzzle handicap by this, and then multiply the score by the result to
        get a final score. Normally not set, which is in effect the same as "1.0"

        Set to <1 for advanced players, or >1 for beginers.

    ignoreduration
        Set to true for begining players who should not be kicked when the timer expires.
        Essentially, zeros the "duration" field when creating a new play for this player.

    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    puzzles = models.ManyToManyField(Puzzle, through='Play')

    # Handicapping information.
    minimumwordlength = models.IntegerField(default=3, null=True)
    handicap = models.FloatField(default=1.0, null=True)
    ignoreduration = models.BooleanField(default=False)


class Play(models.Model):
    """
    How did a player do at a particular puzzle? This is created when a player STARTS a puzzle, and
    is the item referenced by wordslist. Though at first glance this "game rules" type information
    may seem to be unique to a puzzle, and not a puzzle/player relationship, keep in mind that
    individual player handicapping may result in a players rules being different from the defaults
    for that puzzle.

    When created with a null player when a puzzle is created, used to store the definitive word
    list and the default (non-handicapped) game options.

    player
        null for initial puzzle wordlist and default game settings.

    words
        lists all words this player found, or that are findable (if player==null)

    score
        blank until the player completes the puzzle, or if player==null

    date
        the date and time the puzzle was created/rolled and the words added.

    time
        The duration that the player has to complete the puzzle. Defaults to 5 minutes.
        If zero, indicates that there is no time limit on this puzzle.

    complete
        True if the game is over, either through out of time or giving up.
        If set without player, this game is no longer playable.

    missed
        If True, Misspelled words count against the player's score.
        If false, there is no penalty for misspelled words.

    repeats
        If True, there's a penalty for a player entering a word they've already found.

    showmaximum
        If False, players are not given information about how many words are left to find.

    minimumwordlength
        The smallest word that will be counted. Almost always 3, but may be set to 4 to handicap
        an advanced player, or even 2 to give begining players an advantage.
        1, however, would just be silly.

    handicap
        The difficulty rating for this puzzle. Players scores are multiplied by this. Also another
        way to handicap players that gives more flexibility.

    """
    player = models.ForeignKey(Player, on_delete=models.CASCADE, null=True)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE, related_name="options")
    words = models.ManyToManyField(Word, through='WordList')
    date = models.DateTimeField(auto_now_add=True)

    # This field should be indexed, because we'll often search for
    # "player=null&complete=False&orderby=-date"

    complete = models.BooleanField(default=False)
    # Store score, options, Start time, duration, gave up, etc.
    score = models.IntegerField(default=0, blank=True)
    time = models.DurationField(default=timedelta(minutes=5), blank=True)
    missed = models.BooleanField(default=False)
    repeats = models.BooleanField(default=False)
    showmaximum = models.BooleanField(default=True)
    minimumwordlength = models.IntegerField(default=3)
    handicap = models.FloatField(default=1.0)

    def save(self, *args, **kwargs):
        if self.player and not self.pk:
            # On creation of a new play method for a player, initialize from puzzles' play object.
            pplay = Play.objects.get(player=None, puzzle=self.puzzle)
            self.score = 0
            self.time = 0 if self.player.ignoreduration else pplay.time
            self.missed = pplay.missed
            self.repeats = pplay.repeats
            self.showmaximum = pplay.showmaximum
            self.minimumwordlength = pplay.minimumwordlength + self.player.minimumwordlength
            self.handicap = pplay.handicap * self.player.handicap
        return super().save(*args, **kwargs)

    class Meta:
        unique_together = (("player", "puzzle"), )
        ordering = ('-date',)


class WordList(models.Model):
    """
    Detailed information about words in a puzzle, when they were found, etc.

    play
        Link to the puzzle/player combo that's currently happening.

    word
        If null, assume to be a record of a player misspelling a word.

    foundtime
        If null, play.player must also be null. This is assumed to be the inital list of words
        that's finable in this particular puzzle.

    """
    play = models.ForeignKey(Play, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.CASCADE, null=True)

    # This is nullable only if player is null.
    foundtime = models.DurationField(null=True)

    class Meta:
        unique_together = (("play", "word"), )
