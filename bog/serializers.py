from rest_framework import serializers
from rest_framework.serializers import ALL_FIELDS
from bog import models
from .pyBogged import bogged
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ALL_FIELDS
        model = User


class DiceSetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        # fields = ('id', 'description', 'dice')
        fields = ALL_FIELDS
        model = models.DiceSet


class WordSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ALL_FIELDS
        model = models.Word


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
