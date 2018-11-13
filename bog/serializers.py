from rest_framework import serializers
from rest_framework.serializers import ALL_FIELDS
from bog import models
from .pyBogged import bogged
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError


class WordListSerializer(serializers.ModelSerializer):

    # This is NOT a related field because we need to catch the errors later on, and
    # add an "oops" record to the database instead of rejecting it as invalid input.
    word = serializers.CharField(
        write_only=True,
        max_length=25,
        min_length=2,
        allow_blank=False,
        trim_whitespace=True,
    )
    puzzle = serializers.SlugRelatedField(
        write_only=True,
        slug_field='puzzle',
        queryset=models.Play.objects.filter(player=None),
        allow_null=False,
    )

    def create(self, validated_data):
        """
        This function exists becuase it's the only function this serializer
        is allowed to do, AND we've got some caveats about doing it. Mainly verifying
        that it's a valid word etc.

        Basically, we go through and try to do everything. If there's an error, it will
        mostly be a DoesNotExist, and mostly we want to throw that back for the frontend to
        deal with.
        """
        errormessage = ""

        # puzzleplay is the universal play object, with player=None
        puzzleplay = validated_data['puzzle']

        # play is THIS USER'S play object. We'll need this to check what rules this user is
        # playing by.
        try:
            try:
                play = models.Play.objects.filter(puzzle=puzzleplay.puzzle,
                                                  player=self.context['request'].user.player)[0]
            except AttributeError:
                raise PermissionDenied
        except IndexError:
            # There is no play record for this user/puzzle combination. Create it.
            play = models.Play(puzzle=puzzleplay.puzzle, player=self.context['request'].user.player)
            play.save()

        try:
            # Here, we get the correct word record for this word. But note the roundabout method
            # This is to make sure that it exists FOR THIS PUZZLE. Simply finding it isn't enough.
            word = models.WordList.objects.filter(
                play=puzzleplay,
                word__word=validated_data['word']
            )[0].word
        except IndexError:
            errormessage = "invalid word. Not on this puzzle or not a word."
            if play.missed:
                # Track missed words by adding a wordlist record with no word.
                word = None
            else:
                raise IntegrityError(errormessage)

        # Create the wordlist object.
        wordlist = models.WordList(word=word, play=play, foundtime=validated_data['foundtime'])

        try:
            wordlist.save()
        except IntegrityError:
            errormessage = "Not Unique. Word alread found."
            # The user entered the same word again.
            if play.repeats:
                # Track repeated words by adding a wordlist record with no word.
                wordlist.word = None
                # This "save" call should never get a uniqueness check failed, because null!=null
                # (according to SQL)
                wordlist.save()
            else:
                raise IntegrityError(errormessage)

        # Lie about it: If word=null, raise an integrityError
        if(wordlist.word is None):
            raise IntegrityError(errormessage)

        return wordlist

    class Meta:
        fields = ['puzzle', 'word', 'foundtime']
        model = models.WordList


class DiceSetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        # fields = ('id', 'description', 'dice')
        fields = ALL_FIELDS
        model = models.DiceSet


class OtherOptionsSerializer(serializers.ModelSerializer):
    """
    Used exclusively for de-serializing the options in puzzle creation
    """
    class Meta:
        exclude = ('player', 'id', )
        model = models.Play


class OptionsSerializer(serializers.ModelSerializer):
    class Meta:
        exclude = ('player', 'puzzle', 'words')
        model = models.Play


class OptionsListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.filter(player__isnull=True)
        return super().to_representation(data)


class PuzzleSerializer(serializers.ModelSerializer):
    """
    """
    options = OptionsListSerializer(child=OptionsSerializer())
    dicesetdesc = serializers.SlugRelatedField(
        read_only=True,
        slug_field='description')
    createdby = serializers.SerializerMethodField()

    def get_createdby(self, obj):
        return obj.createdby.get_full_name()

    def create(self, validated_data):

        # remove options from _writeable_fields after creating the new play instance.
        if 'options' in validated_data:
            options = validated_data['options']
            del validated_data['options']
        else:
            options = {}

        # Have to create the bog instance to get the randomized layout.
        # raise ValueError(validated_data)
        bog = bogged(validated_data['diceset'].dice)
        bog.newgame()
        validated_data['layout'] = bog.layout

        # Create the puzzle record
        puzzle = super().create(validated_data)

        options['puzzle'] = puzzle

        # Create the play record
        playserializer = OtherOptionsSerializer()
        play = playserializer.create(options)

        # Create the play.words records.
        for word in bog.words:
            word, created = models.Word.objects.get_or_create(word=word)
            models.WordList.objects.create(word=word, play=play)

        return puzzle

    class Meta:
        exclude = []
        model = models.Puzzle


class PlayerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        fields = ('id', 'user', 'minimumwordlength', 'handicap', 'ignoreduration')
        model = models.Player


class PuzzleWordSerializer(serializers.ModelSerializer):
    player = serializers.SerializerMethodField()

    def get_player(self, obj):
        # In practise, this is filtered so
        assert obj.play.player is not None, "Trying to show words attached to the puzzle?"
        return obj.play.player.user.get_full_name()

    class Meta:
        fields = ('player', 'foundtime', 'pk')
        model = models.WordList


class PlayWordSerializer(serializers.ModelSerializer):
    players = serializers.SerializerMethodField()
    word = serializers.SlugRelatedField(
        read_only=True,
        slug_field='word',
        allow_null=True)

    def get_players(self, obj):
        return serializers.ListSerializer(child=PuzzleWordSerializer()).to_representation(
            models.WordList.objects.filter(word=obj.word,
                                           play__puzzle=obj.play.puzzle,
                                           play__player__isnull=False)
                                   .exclude(play__player=obj.play.player)
        )
    # This shadows the "word" field forcing it to use a string

    class Meta:
        fields = ('id', 'word', 'foundtime', 'players')
        model = models.WordList


class PlayWordListSerializer(serializers.ModelSerializer):
    """
    This is our most commonly called serializer. It's purpose is to return an
    annotated list of words this player has found on this puzzle, and to provide a way
    for new found words to be added. "duration/word" in the one case, and "play" in the other.

    Note that we don't give a hoot about the other fields, only the words.
    """
    wordlist_set = serializers.ListSerializer(child=PlayWordSerializer())

    class Meta:
        fields = ('wordlist_set', 'pk')
        model = models.Play


class WordRelatedField(serializers.ModelSerializer):
    class Meta:
        fields = ('word', 'foundtime')
        model = models.WordList


class PlaySerializer(serializers.HyperlinkedModelSerializer):
    """
    This is only ever called to create plays for a particular player. At the same time,
    "player" is read-only, and is instead set from the logged in user, creating the
    player record if needed in the process. Also note that all values here are defaulted
    from the player/puzzle records on creation.

    Updates are permitted ONLY to set complete to true.
    """
    words = serializers.ListSerializer(child=WordRelatedField())

    def create(self, validated_data):
        validated_data['player'], __ = models.Player.objects.get_or_create(
            user=self.context['request'].user)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if not self.partial:
            raise NotImplementedError("Only partial updates are allowed")

        user = self.context['request'].user
        if self.instance.player.user != user and not user.is_staff and not user.is_superuser:
            raise PermissionDenied("You're only authorized to update your own plays")

        # Once created, puzzle is read-only
        if 'puzzle' in validated_data:
            del validated_data['puzzle']
        # Complete may not be set to false, except when creating a new record.
        if 'complete' in validated_data and not validated_data['complete']:
            del validated_data['complete']
        if 'words' in validated_data:
            words = validated_data.pop('words')
        else:
            words = []

        play = super().update(instance, validated_data)

        for word in words:
            models.Word(word=word, play=play).save()

        return play

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'puzzle' and field != 'complete':
                self.fields[field].read_only = True

    class Meta:
        fields = serializers.ALL_FIELDS
        model = models.Play
        # TODO: selective initialization of play based on default play & player handicaps.
