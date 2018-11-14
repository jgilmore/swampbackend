from bog import serializers
from . import models
from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from django.shortcuts import get_object_or_404
from django.db import IntegrityError

# Create your views here.

# So, let's think about it. The basic sequence goes like this:
#  1. Create a dice set.
#  2. Pick a dice set from a list, and hit "create"
#     2a. This initiates a long sequence of actions, starting by rolling the dice, and ending with
#     creating multiple word records.
#  3. Modify game settings as needed.
#  4. Start the game.
#   4a. Create the "play" record based on the game defaults and the player's defaults.
#   4b. Request the game layout for this play. Display the layout, the maximum words, current score,
#   etc. Records retrieved: play, puzzle, puzzle.words.length,
#   4c. add a word
#     4c1. Word exists and is long enough, add it with the duration passed from the frontend.
#     4c2. Otherwise, it's rejected and a WordList record added, either empty or referncing the
#     too short word.
#   4d. Update word lists of other players.
#     4d1. This query looks like play.puzzle.play
#     play->puzzle->all plays where player!=null, all words, filterby(words in player->play->words)
#     And this result should be {'word': [playerlist],...}
#     Not only should it filter by player has the word, but also by otherplayer found it before my
#     current duration. That's interesting.
#  5. End the game. Time is up or the player hit "give up" button. (this is SOLELY client-side,
#  which means it's gameable - if the user edits values on their end, we'll just ignore it. cheating
#  is it's own punishment.)
#    5a. Update score by iteration through play.words.
#    5b. Mark play as completed.
#  6. Player record is updated with new handicap.


# Ok, based on all the above, we need:
# *    ListCreateDiceSet (no update,destroy,retrieve)
# *    ListCreatePuzzle (with auto-creation of associated play and word records)
# i     Create"play" record (with defaults)(works from "ListPuzzle")
#      query found words (complicated, returns {'word':{'player':time,..},..})
#      FoundAWord
# i     finish game (update score, etc)
# *    ListCreatePlayer
# *    RetrieveUpdateDestroyPlayer


@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        r'diceset':  reverse('diceset-list', request=request, format=format),
        r'play':     reverse('play-list', request=request, format=format),
        r'words':    reverse('wordlist', request=request, format=format, args=(1,)),
        r'word':     reverse('word-list', request=request, format=format),
        r'puzzle':   reverse('puzzle-list', request=request, format=format),
        r'player':   reverse('player-list', request=request, format=format),

        r'admin':    reverse('admin:index', request=request, format=format),
    })

    # queryset = models.Play.filter(pk=6).words.filter(play__puzzle='play__puzzle')


class WordListViewSet(viewsets.GenericViewSet,
                      mixins.CreateModelMixin):
    """
    This API access point is called when the player finds a new word on the puzzle.
    An error is returned if the word doesn't exist on this particular puzzle.
    Note that the puzzleID is submitted, not the playID. The PlayID will be deduced
    from the puzzle and the logged in user.
    """
    queryset = models.WordList.objects.all()
    serializer_class = serializers.WordListSerializer

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as x:
            return Response(x.args, status=status.HTTP_409_CONFLICT)


class ListCreateDiceSetView(viewsets.ModelViewSet):
    queryset = models.DiceSet.objects.all()
    serializer_class = serializers.DiceSetSerializer
    permission_classes_by_action = {'list': [IsAuthenticated],
                                    'create': [IsAdminUser],
                                    'update': [IsAdminUser]}


class ListCreatePuzzleView(viewsets.ModelViewSet):
    """
    Use this to create new puzzles, and to get lists of current puzzles.
    New puzzles are automatically created with all attendant records:
        Play record with player=null
        word records for all possible words in the puzzle attached to the above play record

    Several filtering options are available. In particular, this will usually be accessed as:
        "/puzzle/?complete=false"

    Also, most recently created puzzles are listed first.
    """
    queryset = models.Puzzle.objects\
        .filter(options__complete=False, options__player__isnull=True)\
        .order_by('-options__date')
    serializer_class = serializers.PuzzleSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    # TODO: Create puzzle special effects


class CreateUpdatePlayView(viewsets.ModelViewSet):
    """
    Use this for:
        creating new play records (i.e. started a game)
        updating old play records (i.e. stopping a game by marking it complete)
        Fetching updated word lists (i.e. updating "who else has found these words")

    Notes:
        Non-admin users can only see their games.
        All fields except 'puzzle' are set to defaults on creation
        Only the 'complete' field is writeable thereafter, and it can only be set true.
        A "player" record will be automatically created if needed.

    Use /puzzle/ to find puzzles to play.
    """
    queryset = models.Play.objects.all()
    serializer_class = serializers.PlaySerializer
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        if(self.request.user.is_staff):
            # Admin users not required to have a player record.
            return models.Play.objects.all()
        else:
            # Normal users only get to see uncompleted games for themselves.
            if hasattr(self.request.user, 'player'):
                return models.Play.objects.filter(
                    player=self.request.user.player, complete=False)
            else:
                return models.Play.objects.none()
            # Normal users required to have a player record so we can show them only their games.
            # We also only show them in-progress games. For statistics, we'll write some custom
            # query stuff elsewhere, and probably only return totals etc. (TODO)
    # TODO: Update score on finished with puzzle, etc.
    # TODO: On creation, update with puzzle/player defaults.


@api_view(["GET"])
def listwords(request, pk):
    """
    Use this to get a list of words the user has found on
    this puzzle. 'GET' is the only method allowed.
    """
    # request.auth()
    if(not request.user.is_authenticated):
        return Response({"Must be authenticated to list words"}, status=status.HTTP_403_FORBIDDEN)

    play = get_object_or_404(
        models.Play,
        puzzle__pk=pk,
        player__user=request.user
    )
    serializer = serializers.PlayWordListSerializer(play)
    return Response(serializer.data)


class PlayerModelView(viewsets.ModelViewSet):
    """
    Player records are associated, one-to-one, with users.
    This is for individual player handicapping etc.
    Required for players to actually play a game, but the user record alone is enough to create
    games, dice sets, etc. (though that of course requires admin priveliges)
    """
    queryset = models.Player.objects.all()
    serializer_class = serializers.PlayerSerializer
    permission_classes = (IsAdminUser,)
