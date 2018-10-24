# !/usr/bin/env python
"""pybogged: A word game implemented with pyGTK"""
__version__ = "1.5"
__author__ = "John Gilmore"
__copyright__ = "(C) 2010,2012 John Gilmore. GNU GPL v3 or later."
__contributors__ = []
# TODO:Tooltips for the options
# TODO:optional funny/annoying messages on misses/repeats
# TODO:dice with different criteria, maybe in a drop-down?

# These are in the python standard library
import random
import pipes
from django.core.exceptions import ValidationError


class bogged:
    """Basic bogged rules engine & dice tracker"""
    def __init__(self, chromosome=None):
        """Set dice set description,etc"""
        self.maxwords = 0
        self.words = []

        if len(chromosome) == 16*6:
            # Chomosome length indicates a 4x4 grid of six-sided dice
            self.width = 4
            self.height = 4
            self.grid = [["A", "B", "C", "D"],
                         ["E", "F", "G", "H"],
                         ["I", "J", "K", "L"],
                         ["M", "N", "O", "P"]]
            self.used = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        elif len(chromosome) == 25*6:
            # Chomosome length indicates a 5x5 grid of six-sided dice
            self.width = 5
            self.height = 5
            self.grid = [["A", "B", "C", "D", "E"],
                         ["F", "G", "H", "I", "J"],
                         ["K", "L", "M", "N", "O"],
                         ["P", "Q", "R", "S", "T"],
                         ["U", "V", "W", "X", "Y"]]
            self.used = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
        else:
            raise ValidationError("Bad chromosome detected:" + str(len(chromosome)) +
                                  ". Must be 16 or 25 six sided dice characters in length "
                                  "(either 96 or 150 chars)" + chromosome)
        self.dice = []
        self.layout = ""
        for index in range(self.width * self.height):
            self.dice.append(chromosome[index*6:(index+1)*6])

    def newgame(self):
        """Start a new game"""
        # Randomly generate array of letters.
        # make a temporary local copy of self.dice
        dice = []
        self.layout = ""
        for i in self.dice:
            dice.append(i)
        for x in range(self.width):
            for y in range(self.height):
                index = random.randrange(len(dice))
                die = dice.pop(index)
                self.grid[x][y] = random.choice(die)
                self.layout += self.grid[x][y]
        # Zero "possible two letters" array
        self.possible2letters = {}
        # for each letter in grid, set it+neighbor to"true"
        for x in range(self.width):
            for y in range(self.height):
                b = self.grid[x][y]
                if b == "Q":
                    b = "U"
                    self.possible2letters["QU"] = 1
                for i in [-1, 0, 1]:
                    for j in [-1, 0, 1]:
                        if i == 0 and j == 0:
                            continue
                        # if out of range go to the next loop cycle.
                        if x+i < 0 or x+i > self.width-1 or y+j < 0 or y+j > self.height-1:
                            continue
                        a = self.grid[x+i][y+j]
                        self.possible2letters[b+a] = 1
        # Add each unique letter to a string
        letters = ""
        for x in range(self.width):
            for y in range(self.height):
                if not letters.count(self.grid[x][y]):
                    letters = letters + self.grid[x][y]
        if "Q" in letters and "U" not in letters:
            letters = letters + "U"
        # pipe from "grep" to search the dictionaries for words of three or more letters
        # which have only those letters in them.
        # "zcat -f $files | grep ^\[$letters\]\[$letters\]\[$letters\]\[$letters\]*$"
            # this creates a list of words which consist of only the letters on the grid.
        # Removed support for non-POSIX os's. Run a real os or suffer massive performance problems.
        grep = pipes.Template()
        grep.append("zcat --stdout -f $IN", "f-")
        grep.append("grep -E '^[" + letters.swapcase() + "]{3,}$' -", "--")
        dictionary = grep.open("/usr/share/dict/words", "r")
        # Clear wordlist
        self.words = []
        # Read from the above pipe, and for each word, call checkword and append to words list.
        for word in dictionary:
            word = word.strip()
            # print "checking:" + word
            if self.checkword(word.swapcase()):
                self.words.append(word)
                # print "found:" + word
        self.maxwords = len(self.words)

    def pgrid(self):
        """prints the grid nicely for command-line debugging"""
        print('/----\\')
        for x in range(self.width):
            a = '|'
            for y in range(self.height):
                if self.used[x][y]:
                    a = a + self.grid[x][y].swapcase()
                else:
                    a = a + self.grid[x][y]
            print(a + '|')
        print('\\----/')

    def checkword(self, word):
        """returns 1 if the given word can actually be legally made on the grid.
            Note that this is called only at the start of a game as part of the
            process of filling the self.words variable. Forever after, self.words
            is used."""
        if len(word) < 1:
            return 0
        # check that each letter combination exists in possible2letters
        for x in range(len(word)-1):
            if word[x:x+2] not in self.possible2letters:
                # print "rejected, not in 2 letters:" + word[x:x+2]
                return 0
        # for each grid, if it matches the first character:
        for x in range(self.width):
            for y in range(self.height):
                if self.grid[x][y] == word[0]:
                    # call checkword2 on the current grid.
                    if self.checkword2(word, 0, x, y):
                        return 1
        return 0

    def checkword2(self, word, index, x, y):
        """A recursive function used by checkword"""
        # mark the letter as used
        self.used[x][y] = 1
        # print "x=" + str(x) + " y=" +  str(y)
        # self.pgrid()
        # Special handling for the implicit "U" after each "Q"
        if word[index] == "Q" and index+1 < len(word):
            if word[index+1] == "U":
                index += 1
        # return true if at end of word
        if len(word)-1 == index:
            # mark the current letter as unused
            self.used[x][y] = 0
            return 1
        # if any neighbor matches the next letter:
        for i in [-1, 0, 1]:
            for j in [-1, 0, 1]:
                if i == 0 and j == 0:
                    continue
                # if out of range go to the next loop cycle.
                if x+i < 0 or x+i > self.width-1 or y+j < 0 or y+j > self.height-1:
                    continue
                a = self.grid[x+i][y+j]
                if self.used[x+i][y+j]:
                    # If this letter is already used, it doesn't count
                    continue
                if a == word[index+1]:
                    # Match found, look for next letter at index+1 on that grid
                    if self.checkword2(word, index + 1, x + i, y + j):
                        # return true if that checkword2 call returned true.
                        # mark the that letter as unused
                        self.used[x][y] = 0
                        return 1
        # mark the that letter as unused
        # return False
        self.used[x][y] = 0
        return 0
