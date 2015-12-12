from collections import defaultdict

class HarvestedProperties(object):
    def __init__(self):
        """
        holds
         - voicedefinitions = list of rendered mako templates (lilypond fragments defining a complete voice,
                              e.g. piano right hand)
         - haslyrics = map of voice fragment name (string) to bool to indicate if a given voice also has lyrics
                       associated to it
         - hasclef = map of voice fragment name (string) to bool to indicate if a given voice also has an explicit
                     clef specification
         - instrumentname = map from voice fragment name (string) to string to hold the midi instrument name vor a given
                            voice
         - sorted_style_tracks = list of track name (string) in the order in which they appear in the style file
         - sorted_song_tracks = list of track name (string) in the order in which they appear in the song file
         - stafftypes = map of track name (string) to tuple of (stafftype, voicefragmentname)
         - staffproperties = map of voice fragment name (string) to a list of staff properties (lilypond properties)
        """

        self.voicedefinitions = []
        self.haslyrics = {}
        self.hasclef = {}
        self.instrumentname = {}
        self.sorted_style_tracks = []
        self.sorted_song_tracks = []
        self.stafftypes = defaultdict(list)
        self.staffproperties = defaultdict(list)
