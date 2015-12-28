import os
import sys
from collections import defaultdict

import music21
from mako.template import Template
from ruamel.yaml import load, RoundTripLoader

from harvestedproperties import HarvestedProperties
from lily2stream import Lily2Stream
from numberutils import int_to_roman, int_to_text, split_roman_prefix, starts_with_one_of
from voiceleading import VoiceLeader, SHIIHS_VOICELEADING

HARMONY = 1
MELODY = 2
PERCUSSION = 3
SPLITREGEX = " |\||\n|\t"

import cProfile
import tempfile
import pstats


def profile(sort='cumulative', lines=50, strip_dirs=False):
    """A decorator which profiles a callable.
    Example usage:

    >>> @profile
        def factorial(n):
            n = abs(int(n))
            if n < 1:
                    n = 1
            x = 1
            for i in range(1, n + 1):
                    x = i * x
            return x
    ...
    >>> factorial(5)
    Thu Jul 15 20:58:21 2010    /tmp/tmpIDejr5

             4 function calls in 0.000 CPU seconds

       Ordered by: internal time, call count

       ncalls  tottime  percall  cumtime  percall filename:lineno(function)
            1    0.000    0.000    0.000    0.000 profiler.py:120(factorial)
            1    0.000    0.000    0.000    0.000 {range}
            1    0.000    0.000    0.000    0.000 {abs}

    120
    >>>
    """

    def outer(fun):
        def inner(*args, **kwargs):
            file = tempfile.NamedTemporaryFile()
            prof = cProfile.Profile()
            try:
                ret = prof.runcall(fun, *args, **kwargs)
            except:
                file.close()
                raise

            prof.dump_stats(file.name)
            stats = pstats.Stats(file.name)
            if strip_dirs:
                stats.strip_dirs()
            if isinstance(sort, (tuple, list)):
                stats.sort_stats(*sort)
            else:
                stats.sort_stats(sort)
            stats.print_stats(lines)

            file.close()
            return ret

        return inner

    # in case this is defined as "@profile" instead of "@profile()"
    if hasattr(sort, '__call__'):
        fun = sort
        sort = 'cumulative'
        outer = outer(fun)
    return outer


def merge_dicts(x, y):
    """
    Given two dicts, merge them into a new dict as a shallow copy.
    :param x: first dict
    :param y: second dict
    :return: firstdict updated from seconddict
    """
    z = x.copy()
    z.update(y)
    return z


def cleanup_string_for_lilypond(s):
    """
    turn string into lilypond identifier
    :param s: string
    :return: lilypondified string
    """
    c = s.replace("_", "").replace("-", "").replace("##", "dblsharp").replace("#", "sharp").replace("\n", "")
    import re
    nums = re.compile("\d+")
    numbers = [int(n) for n in re.findall(nums, c)]
    for n in reversed(sorted(numbers)):
        c = c.replace("{0}".format(n), int_to_text(int(n)))

    return c


class StyleCompiler(object):
    """
    class to compile a style file and a song file to a lilypond file
    """

    def __init__(self, rootpath, options):
        self.rootpath = rootpath
        self.options = options
        self.muted_staves = set([])
        self.muted_tracks = set([])
        # print(options)

    def load_style(self, subfolder, stylename):
        style = ""
        fname = os.path.join(self.rootpath, subfolder, stylename) + ".yaml"
        try:
            with open(fname, "r") as f:
                style = f.read()
            parsed_style = load(style, RoundTripLoader)
            style = parsed_style["style"]
            print("*** Loaded style file ", fname)
        except:
            print("*** Error: couldn't load style file {0}. {1}".format(fname, sys.exc_info()[0]))
            sys.exit(3)
        return style

    @staticmethod
    def load_song(songname):
        song = ""
        fname = songname
        try:
            with open(fname, "r") as f:
                song = f.read()
            parsed_song = load(song, RoundTripLoader)
            song = parsed_song["song"]
            print("*** Loaded song file ", fname)
        except Exception:
            print("*** Error: couldn't load song file {0}. {1}".format(fname, sys.exc_info()[0]))
            sys.exit(4)
        return song

    @staticmethod
    def fragmentname(trackname, staffname, chordname):
        ct = cleanup_string_for_lilypond(trackname)
        cs = cleanup_string_for_lilypond(staffname)
        cc = cleanup_string_for_lilypond(chordname)
        return ct + cs + cc

    @staticmethod
    def voicename(trackname, staffname):
        ct = cleanup_string_for_lilypond(trackname)
        cs = cleanup_string_for_lilypond(staffname)
        return ct + cs

    def voicefragmentname(self, trackname, staffname):
        return self.voicename(trackname, staffname) + "Voice"

    def lyricsfragmentname(self, trackname, staffname):
        return self.voicefragmentname(trackname, staffname) + "Lyrics"

    # @profile
    def compile(self):
        # read song and style specs
        song = self.load_song(self.options.inputfile[0])
        song_style = song["style"] if "style" in song else ""
        song_rhythm = song["rhythm"] if "rhythm" in song else ""
        song_title = song["header"]["title"]
        song_writer = song["header"]["composer"]
        print("*** Rendering {0} by {1} to lilypond".format(song_title, song_writer))

        # read style specs
        style = self.init_style(song_style)
        rhythm = self.init_percussion(song_rhythm)  # read lilypond template

        lytemplate = Template(filename=os.path.join(self.rootpath, "ly-templates", "score.mako"))

        globalproperties = merge_dicts(style["global"], song["global"])

        if song_style:
            chorddefinitions, knownchords = self.calculate_chord_definitions(style)
        else:
            chorddefinitions, knownchords = None, None

        if song_rhythm:
            patterndefinitions, knownpatterns = self.calculate_patterns(rhythm)
        else:
            patterndefinitions, knownpatterns = None, None

        harvestedproperties = self.calculate_voice_definitions(knownchords, chorddefinitions, knownpatterns,
                                                               patterndefinitions, song, style, rhythm)

        stavedefinitions, tracktostaff = self.calculate_staff_definitions(harvestedproperties)

        sorted_track_names = []
        for name in harvestedproperties.sorted_song_tracks:
            sorted_track_names.append(tracktostaff[name])
        for name in harvestedproperties.sorted_style_tracks:
            sorted_track_names.append(tracktostaff[name])

        if self.options.outputfile:
            filename = os.path.abspath(self.options.outputfile[0])
            if os.path.isfile(filename) and not self.options.force:
                print("*** REFUSING TO OVERWRITE EXISTING OUTPUT FILE {0}! QUIT. " + \
                      "(use --force to overwrite existing files).".format(self.options.outputfile))
                sys.exit(1)
            elif os.path.isfile(filename) and self.options.force:
                print("*** WARNING: OVERWRITING EXISTING OUTPUT FILE {0} AS REQUESTED!".format(self.options.outputfile))

            try:
                with open(filename, "w") as f:
                    f.write(lytemplate.render(headerproperties=song["header"],
                                              globalproperties=globalproperties,
                                              chorddefinitions=chorddefinitions,
                                              patterndefinitions=patterndefinitions,
                                              voicedefinitions=harvestedproperties.voicedefinitions,
                                              stavedefinitions=stavedefinitions,
                                              parts=sorted_track_names,
                                              tempo=song["midi"]["tempo"]))
                    print("*** Wrote result in {0}. Please run lilypond on that file.".format(filename))

            except:
                print("*** ERROR WRITING TO FILE {0}. COMPILATION FAILED.".format(self.options.outputfile))
        else:
            print(lytemplate.render(headerproperties=song["header"],
                                    globalproperties=globalproperties,
                                    chorddefinitions=chorddefinitions,
                                    patterndefinitions=patterndefinitions,
                                    voicedefinitions=harvestedproperties.voicedefinitions,
                                    stavedefinitions=stavedefinitions,
                                    parts=sorted_track_names,
                                    tempo=song["midi"]["tempo"]))

    def init_from_file(self, subfolder, filename):
        if filename:
            loaded_style = self.load_style(os.path.join("styles", subfolder), filename)
        else:
            loaded_style = {}
        if "global" not in loaded_style:
            loaded_style["global"] = {}
        return loaded_style

    def init_percussion(self, song_rhythm):
        rhythm = self.init_from_file("percussion", song_rhythm)
        return rhythm

    def init_style(self, song_style):
        style = self.init_from_file("instrumental", song_style)
        return style

    def calculate_staff_definitions(self, harvestedproperties):
        stavedefinitions = []
        tracktostaff = {}
        for staffname in harvestedproperties.stafftypes:
            stafftype = harvestedproperties.stafftypes[staffname][0][0]
            if stafftype == "Staff":
                for voice in harvestedproperties.stafftypes[staffname]:
                    voicename = voice[1]
                    stafftemplate = Template(filename=os.path.join(self.rootpath, "ly-templates", "Staff.mako"))
                    lyricsname = None
                    if harvestedproperties.haslyrics[voicename]:
                        lyricsname = voicename + "Lyrics"
                    all_staffprops = harvestedproperties.staffproperties[voicename][:]
                    all_staffprops.append({'instrumentName': harvestedproperties.instrumentname[staffname]})
                    staffoverr = harvestedproperties.staffoverrides[voicename] if voicename in \
                                                                                  harvestedproperties.staffoverrides else []
                    staffdefinition = stafftemplate.render(
                            staffname=staffname + "Staff",
                            staffproperties=all_staffprops,
                            staffoverrides=staffoverr,
                            voicefragmentname=voicename,
                            clef=harvestedproperties.hasclef[voicename],
                            lyricsname=lyricsname)
                    stavedefinitions.append(staffdefinition)
                tracktostaff[staffname] = staffname + "Staff"
            elif stafftype == "PianoStaff":
                lyricsname = {}
                sorted_voices = []
                stafftemplate = Template(filename=os.path.join(self.rootpath, "ly-templates", "PianoStaff.mako"))
                for i, voice in enumerate(harvestedproperties.stafftypes[staffname]):
                    voicename = voice[1]
                    sorted_voices.append((int_to_roman(i + 1), voicename))
                    lyricsname[voicename] = None
                    if harvestedproperties.haslyrics[voicename]:
                        lyricsname[voicename] = voicename + "Lyrics"
                staffoverr = harvestedproperties.staffoverrides[staffname] if staffname in \
                                                                              harvestedproperties.staffoverrides else []
                staffdefinition = stafftemplate.render(
                        staffname=staffname + "PianoStaff",
                        staffproperties=[{'instrumentName': harvestedproperties.instrumentname[staffname]}],
                        staffoverrides=staffoverr,
                        voicenames=sorted_voices,
                        voiceproperties=harvestedproperties.staffproperties,
                        clef=harvestedproperties.hasclef,
                        lyricsname=lyricsname
                )
                stavedefinitions.append(staffdefinition)
                tracktostaff[staffname] = staffname + "PianoStaff"
            elif stafftype == "DrumStaff":
                for voice in harvestedproperties.stafftypes[staffname]:
                    voicename = voice[1]
                    staffprops = harvestedproperties.staffproperties[voicename] if voicename in \
                                                                                   harvestedproperties.staffproperties else []
                    staffoverr = harvestedproperties.staffoverrides[voicename] if voicename in \
                                                                                  harvestedproperties.staffoverrides else []
                    stafftemplate = Template(filename=os.path.join(self.rootpath, "ly-templates", "DrumStaff.mako"))
                    staffdefinition = stafftemplate.render(
                            staffname=staffname + "DrumStaff",
                            instrumentName=harvestedproperties.instrumentname[staffname],
                            staffproperties=staffprops,
                            staffoverrides=staffoverr,
                            voicefragmentname=voicename,
                    )
                    stavedefinitions.append(staffdefinition)
                tracktostaff[staffname] = staffname + "DrumStaff"
            else:
                assert False, "Stafftype {0} not supported yet!!!".format(stafftype)
        return stavedefinitions, tracktostaff

    def calculate_chord_definitions(self, style):
        chorddefinitions = {}
        knownchords = defaultdict(lambda: defaultdict(set))
        for name in style["tracks"]:
            if name in chorddefinitions:
                print("*** WARNING: track with name {0} is specified multiple times".format(name))
            chorddefinitions[name] = []

            for staff in style["tracks"][name]["staves"]:
                for chord in style["tracks"][name]["staves"][staff]["chords"]:
                    fragcontent = style["tracks"][name]["staves"][staff]["chords"][chord]
                    self.register_chord(name, staff, chord, fragcontent, knownchords, chorddefinitions)

        return chorddefinitions, knownchords

    def calculate_patterns(self, rhythm):
        patterndefinitions = {}
        knownpatterns = defaultdict(lambda: defaultdict(set))
        if rhythm is not None and "tracks" in rhythm:
            for name in rhythm["tracks"]:
                if name in patterndefinitions:
                    print("*** WARNING: drum track with name {0} is specified multiple times".format(name))
                patterndefinitions[name] = []

                for staff in rhythm["tracks"][name]["staves"]:
                    for pat in rhythm["tracks"][name]["staves"][staff]["patterns"]:
                        fragcontent = rhythm["tracks"][name]["staves"][staff]["patterns"][pat]
                        self.register_pattern(name, staff, pat, fragcontent, knownpatterns, patterndefinitions)
        return patterndefinitions, knownpatterns

    def register_chord(self, name, staff, chord, fragcontent, knownchords, chorddefinitions):
        knownchords[name][staff].add(chord)
        fragname = self.fragmentname(name, staff, chord)
        fragment = "{0} = {1}".format(fragname, fragcontent)
        chorddefinitions[name].append(fragment)

    def register_pattern(self, name, staff, pat, fragcontent, knownpatterns, patterndefinitions):
        knownpatterns[name][staff].add(pat)
        fragname = self.fragmentname(name, staff, pat)
        fragment = "{0} = {1}".format(fragname, fragcontent)
        patterndefinitions[name].append(fragment)

    def calculate_voice_definitions(self, knownchords, chorddefinitions, knownpatterns, patterndefinitions, song, style,
                                    rhythm):
        h = HarvestedProperties()
        if "specified-relative-to" in style and "key" in style["specified-relative-to"]:
            refpitch = style["specified-relative-to"]["key"]
        else:
            refpitch = "c"

        if "tracks" in song:
            for name in song["tracks"]:
                self.process_track(MELODY, song, song, refpitch, name, knownchords,
                                   chorddefinitions, knownpatterns, h)

        if "tracks" in style:
            for name in style["tracks"]:
                self.process_track(HARMONY, song, style, refpitch, name, knownchords,
                                   chorddefinitions, knownpatterns, h)

        if rhythm is not None and "tracks" in rhythm:
            for name in rhythm["tracks"]:
                self.process_track(PERCUSSION, song, rhythm, refpitch, name, knownchords,
                                   chorddefinitions, knownpatterns, h)

        return h

    def process_track(self, harmonytype, song, style, refpitch, name, knownchords, chorddefinitions, knownpatterns, h):
        if "tracks" in style and name in style["tracks"] and "instrumentName" in style["tracks"][name]:
            h.instrumentname[name] = style["tracks"][name]["instrumentName"]
        else:
            h.instrumentname[name] = name
        h.sorted_style_tracks.append(name)
        if name in style["tracks"] and "staves" in style["tracks"][name]:
            for staff in style["tracks"][name]["staves"]:
                self.process_staff(harmonytype, song, style, refpitch, knownchords, chorddefinitions,
                                   knownpatterns, staff, name, h)

    def process_staff(self, harmonytype, song, style, refpitch, knownchords, chorddefinitions, knownpatterns,
                      staff, name, h):
        destpitch = refpitch[:]  # reset for each staff
        voicefragmentname = self.voicefragmentname(name, staff)
        h.stafftypes[name].append((style["tracks"][name]["type"], voicefragmentname))
        if "staffProperties" in style["tracks"][name]["staves"][staff]:
            h.staffproperties[voicefragmentname].append(style["tracks"][name]["staves"][staff]["staffProperties"])
        if "staffOverrides" in style["tracks"][name]["staves"][staff]:
            h.staffoverrides[voicefragmentname].append(style["tracks"][name]["staves"][staff]["staffOverrides"])
        h.hasclef[voicefragmentname] = "treble"
        if "clef" in style["tracks"][name]["staves"][staff]:
            h.hasclef[voicefragmentname] = style["tracks"][name]["staves"][staff]["clef"]
        staff_voice_template = Template(filename=os.path.join(self.rootpath,
                                                              "ly-templates", "voice.mako"))
        h.haslyrics[voicefragmentname] = False
        vl = VoiceLeader()
        self.process_harmony(harmonytype, song, style, refpitch, destpitch, knownchords, chorddefinitions,
                             knownpatterns, staff, name, staff_voice_template, voicefragmentname, h)

        if "lyrics" in style["tracks"][name]["staves"][staff]:
            h.haslyrics[voicefragmentname] = True
            lyrics = style["tracks"][name]["staves"][staff]["lyrics"]
            staff_lyrics_template = Template(
                    filename=os.path.join(self.rootpath, "ly-templates", "lyrics.mako"))
            rendered_lyrics = staff_lyrics_template.render(voicefragmentname=voicefragmentname + "Lyrics",
                                                           musicelements=[lyrics.replace("|", "|\n")])
            h.voicedefinitions.append(rendered_lyrics)
        else:
            h.haslyrics[voicefragmentname] = False

    def process_harmony(self, harmonytype, song, style, refpitch, destpitch, knownchords, chorddefinitions,
                        knownpatterns, staff, name, staff_voice_template, voicefragmentname, h):
        musicelements = []
        if harmonytype == MELODY and "music" in style["tracks"][name]["staves"][staff]:
            for element in style["tracks"][name]["staves"][staff]["music"]:
                if "notes" in element:
                    lycode = element["notes"].replace("|", "|\n")
                    self.insert_transposable_lilypondcode(refpitch, destpitch, lycode, musicelements)
                elif "ly" in element:
                    self.insert_raw_lilypondcode(element["ly"], musicelements)
                elif "transpose" in element:
                    destpitch = element["transpose"]["to"]
            voice = staff_voice_template.render(voicefragmentname=voicefragmentname, musicelements=musicelements)
            h.voicedefinitions.append(voice)

        if harmonytype == PERCUSSION and "percussion" in song:
            for harmonyelement in song["percussion"]:
                if "patterns" in harmonyelement:
                    patterns = harmonyelement["patterns"]
                    import re
                    patterns = (el for el in re.split(SPLITREGEX, patterns) if el)  # cut out empty entries
                    for p in patterns:
                        if name not in self.muted_tracks and staff not in self.muted_staves:
                            self.insert_nontransposable_pattern(p, knownpatterns, staff, name, musicelements)
                        else:
                            self.insert_nontransposable_pattern("\\" + self.voicename(name, staff) + "Rest",
                                                                knownpatterns, staff, name, musicelements)
                elif "ly" in harmonyelement:
                    self.insert_raw_lilypondcode(harmonyelement["ly"], musicelements)
                elif "mute-staff" in harmonyelement:
                    staffname = harmonyelement["mute-staff"]["staff"].strip()
                    self.muted_staves.add(staffname)
                elif "mute-track" in harmonyelement:
                    trackname = harmonyelement["mute-track"]["track"].strip()
                    self.muted_tracks.add(trackname)
                elif "unmute-staff" in harmonyelement:
                    staffname = harmonyelement["unmute-staff"]["staff"].strip()
                    self.muted_staves.remove(staffname)
                elif "unmute-track" in harmonyelement:
                    trackname = harmonyelement["unmute-track"]["track"].strip()
                    self.muted_tracks.remove(trackname)

            voice = staff_voice_template.render(voicefragmentname=voicefragmentname,
                                                musicelements=musicelements)
            h.voicedefinitions.append(voice)

        if harmonytype == HARMONY and "chords" in style["tracks"][name]["staves"][staff]:
            for harmonyelement in song["harmony"]:
                if "chords" in harmonyelement:
                    chords = harmonyelement["chords"]
                    import re
                    chords = (el for el in re.split(SPLITREGEX, chords) if el)  # cut out empty entries
                    for c in chords:
                        if name not in self.muted_tracks and staff not in self.muted_staves:
                            if c in knownchords[name][staff]:
                                self.insert_transposable_pattern(c, refpitch, destpitch, staff, name, musicelements)
                            elif self.to_be_derived_from_existing(c):  # calculate from previous chord
                                cname = cleanup_string_for_lilypond("{0}".format(c))
                                vname = self.voicename(name, staff) + cname
                                number, accidental, modifier = split_roman_prefix(c)
                                if "_" in modifier:
                                    msplit = modifier.split("_")
                                    modifier_without_suffix = msplit[1]
                                    modifier_without_prefix = msplit[0]
                                else:
                                    modifier_without_suffix = modifier
                                    modifier_without_prefix = modifier
                                one_chord = "I" + modifier_without_suffix

                                # if one_chord not in knownchords[name][staff] and not \
                                #     (one_chord.endswith("m") and one_chord[:-1] in knownchords[name][staff]):
                                #     print("ERROR! Style always needs at least specification of the I chord.")
                                #     print("In case of track {0}, staff {1} we couldn't find it.".format(
                                #             name, staff))
                                #     print("Bailing out.")
                                #     sys.exit(1)

                                if one_chord not in knownchords[name][staff] and \
                                        not modifier_without_prefix.startswith("m") and \
                                                modifier_without_prefix != "":
                                    # minor can be calculated from major if needed;
                                    # other types require explicit hints
                                    print("ERROR! Cannot find chord {0} in style file.".format(one_chord))
                                    print("Need it to calculate chord {0} in track {1}, staff {2}.".format(c,
                                                                                                           name, staff))
                                    print("Bailing out.")
                                    sys.exit(2)

                                elif one_chord not in knownchords[name][staff] and \
                                        modifier_without_prefix.startswith("m"):
                                    #
                                    # e.g. you try to calculat VIm but Im doesn't exist in the style file
                                    # in that case: calculate VIm from I.
                                    #
                                    style_scale = style["specified-relative-to"]["key"]
                                    style_scale_mode = style["specified-relative-to"]["mode"]
                                    name_to_constructor = {
                                        "major": music21.scale.MajorScale,
                                        "minor": music21.scale.MinorScale
                                    }
                                    source_scale = name_to_constructor[style_scale_mode](style_scale)
                                    sourcepitch = music21.pitch.Pitch(style_scale)
                                    target_distance = self.scaledegree_distance_from_I(number + accidental)
                                    target_interval = music21.interval.Interval(target_distance)
                                    target_pitch = music21.interval.transposePitch(sourcepitch, target_interval)
                                    target_scale = music21.scale.MinorScale(target_pitch.name)
                                    fragment = style["tracks"][name]["staves"][staff]["chords"]["I"]
                                    vl = VoiceLeader()
                                    l = Lily2Stream()
                                    s = l.parse(fragment)
                                    vlmethod = self.voiceleading_method(style, name, staff)

                                    self.transform_note_stream(s, source_scale, target_scale, vl, vlmethod)
                                    self.transform_chord_stream(s, source_scale, target_scale, vl, vlmethod)

                                    new_fragment = "{ " + l.unparse(
                                            s.flat.getElementsByClass(["Note", "Chord", "Rest"]).stream()) + " }"
                                    self.insert_transposable_voicename(refpitch, destpitch, vname, musicelements)
                                    self.register_chord(name, staff, c, new_fragment, knownchords,
                                                        chorddefinitions)

                                elif one_chord in knownchords[name][staff]:
                                    #
                                    # e.g. you try to find VIm7 and Im7 exists in the style file
                                    #
                                    style_scale = style["specified-relative-to"]["key"]
                                    style_scale_mode = style["specified-relative-to"]["mode"]
                                    name_to_constructor = {
                                        "major": music21.scale.MajorScale,
                                        "minor": music21.scale.MinorScale
                                    }
                                    source_scale = name_to_constructor[style_scale_mode](style_scale)
                                    sourcepitch = music21.pitch.Pitch(style_scale)
                                    target_distance = self.scaledegree_distance_from_I(number + accidental)
                                    target_interval = music21.interval.Interval(target_distance)
                                    target_pitch = music21.interval.transposePitch(sourcepitch, target_interval)
                                    target_scale = music21.scale.MajorScale(target_pitch.name)
                                    if "m" in modifier_without_prefix:
                                        target_scale = music21.scale.MinorScale(target_pitch.name)
                                    # start from Im7 to calculate VIm7
                                    fragment = style["tracks"][name]["staves"][staff]["chords"][one_chord]
                                    vl = VoiceLeader()
                                    l = Lily2Stream()
                                    s = l.parse(fragment)
                                    vlmethod = self.voiceleading_method(style, name, staff)

                                    self.transform_note_stream(s, source_scale, target_scale, vl, vlmethod)
                                    self.transform_chord_stream(s, source_scale, target_scale, vl, vlmethod)

                                    new_fragment = "{ " + l.unparse(
                                            s.flat.getElementsByClass(["Note", "Chord", "Rest"]).stream()) + " }"
                                    self.insert_transposable_voicename(refpitch, destpitch, vname, musicelements)
                                    self.register_chord(name, staff, c, new_fragment, knownchords,
                                                        chorddefinitions)
                            else:
                                musicelements.append(c)
                        else:
                            musicelements.append("\\" + self.voicename(name, staff) + "Rest")
                elif "ly" in harmonyelement:
                    self.insert_raw_lilypondcode(harmonyelement["ly"], musicelements)
                elif "transpose" in harmonyelement:
                    destpitch = harmonyelement["transpose"]["to"]
                elif "mute-staff" in harmonyelement:
                    staffname = harmonyelement["mute-staff"]["staff"].strip()
                    self.muted_staves.add(staffname)
                elif "mute-track" in harmonyelement:
                    trackname = harmonyelement["mute-track"]["track"].strip()
                    self.muted_tracks.add(trackname)
                elif "unmute-staff" in harmonyelement:
                    staffname = harmonyelement["unmute-staff"]["staff"].strip()
                    self.muted_staves.remove(staffname)
                elif "unmute-track" in harmonyelement:
                    trackname = harmonyelement["unmute-track"]["track"].strip()
                    self.muted_tracks.remove(trackname)

            voice = staff_voice_template.render(voicefragmentname=voicefragmentname,
                                                musicelements=musicelements)
            h.voicedefinitions.append(voice)

    def insert_transposable_voicename(self, refpitch, destpitch, vname, musicelements):
        if refpitch == destpitch:
            musicelements.append("\\" + vname)
        else:
            musicelements.append("{{ \\transpose {0} {1} {{ {2} }} }}".format(
                    refpitch, destpitch, "\\" + vname))

    def insert_transposable_pattern(self, c, refpitch, destpitch, staff, name, musicelements):
        if refpitch == destpitch:
            musicelements.append("\\" + self.voicename(name, staff) + \
                                 cleanup_string_for_lilypond(c))
        else:
            musicelements.append("{{ \\transpose {0} {1} {{ {2} }} }}".format(refpitch,
                                                                              destpitch,
                                                                              "\\" + self.voicename(
                                                                                      name, staff) + \
                                                                              cleanup_string_for_lilypond(
                                                                                      c)))

    def insert_nontransposable_pattern(self, p, knownpatterns, staff, name, musicelements):
        if p in knownpatterns[name][staff]:
            musicelements.append("\\" + self.voicename(name, staff) + \
                                 cleanup_string_for_lilypond(p))
        else:
            musicelements.append(p)

    def insert_transposable_lilypondcode(self, refpitch, destpitch, lycode, musicelements):
        if refpitch == destpitch:
            musicelements.append(lycode)
        else:
            musicelements.append("{{\\transpose {0} {1} {{ {2} }} }}".format(refpitch, destpitch, lycode))

    def insert_raw_lilypondcode(self, lycode, musicelements):
        e = lycode
        if isinstance(e, list):
            for el in e:
                musicelements.append(el)
        else:
            musicelements.append(e)

    def to_be_derived_from_existing(self, c):
        return starts_with_one_of(c.upper(), ["III", "II", "IV", "I", "VII", "VI", "V"])

    def scaledegree_distance_from_I(self, degree):
        """
        :param degree: e.g. "VIb"
        :return: chromatic distance from "I" to degree
        """
        d = {
            ("I", "I"): 0,
            ("I", "Ib"): -1,
            ("I", "Ibb"): -2,
            ("I", "I#"): 1,
            ("I", "I##"): 2,

            ("I", "II"): 2,
            ("I", "IIb"): 1,
            ("I", "IIbb"): 0,
            ("I", "II#"): 3,
            ("I", "II##"): 4,

            ("I", "III"): 4,
            ("I", "IIIb"): 3,
            ("I", "IIIbb"): 2,
            ("I", "III#"): 5,
            ("I", "III##"): 6,

            ("I", "IV"): 5,
            ("I", "IVb"): 4,
            ("I", "IVbb"): 3,
            ("I", "IV#"): 6,
            ("I", "IV##"): 7,

            ("I", "V"): 7,
            ("I", "Vb"): 6,
            ("I", "Vbb"): 5,
            ("I", "V#"): 8,
            ("I", "V##"): 9,

            ("I", "VI"): 9,
            ("I", "VIb"): 8,
            ("I", "VIbb"): 7,
            ("I", "VI#"): 10,
            ("I", "VI##"): 11,

            ("I", "VII"): 11,
            ("I", "VIIb"): 10,
            ("I", "VIIbb"): 9,
            ("I", "VII#"): 12,
            ("I", "VII##"): 13,
        }
        return d[("I", degree)] if ("I", degree) in d else 0

    def transform_chord_stream(self, s, source_scale, target_scale, vl, vlmethod):
        chord_stream = s.flat.getElementsByClass(["Chord"]).stream()
        if chord_stream:
            list_of_chordpitches = []
            for cd in chord_stream:
                pitches = [n.pitch for n in cd]
                if pitches:
                    result = vl.calculate(pitches, source_scale, target_scale,
                                          reorder_notes=vlmethod, map_accidentals=True)
                    this_chord = []
                    for p, n in enumerate(cd.pitches):
                        this_chord.append(result[p])
                    list_of_chordpitches.append(this_chord)
            for p, cs in enumerate(chord_stream):
                cs.pitches = list_of_chordpitches[p]

    def transform_note_stream(self, s, source_scale, target_scale, vl, vlmethod):
        note_stream = s.flat.getElementsByClass(["Note"]).stream()
        if note_stream:
            pitches = [n.pitch for n in note_stream]
            if pitches:
                result = vl.calculate(pitches, source_scale, target_scale,
                                      reorder_notes=vlmethod, map_accidentals=True)
                for p, n in enumerate(note_stream):
                    n.pitch = result[p]

    def voiceleading_method(self, style, name, staff):
        vlmethod = SHIIHS_VOICELEADING
        if "voiceLeadingMethod" in style["tracks"][name]["staves"][staff]:
            vlmethod = style["tracks"][name]["staves"][staff]["voiceLeadingMethod"]
        return vlmethod
