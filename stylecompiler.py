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
    c = s.replace("_", "").replace("-", "").replace("##", "dblsharp").replace("#", "sharp")
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
        # print(options)

    def load_style(self, stylename):
        style = ""
        fname = os.path.join(self.rootpath, "styles", stylename) + ".yaml"
        try:
            with open(fname, "r") as f:
                style = f.read()
            parsed_style = load(style, RoundTripLoader)
            style = parsed_style["style"]
            print("*** Loaded style file ", fname)
        except:
            print("*** Error: couldn't load style file {0}. {1}".format(fname, sys.exc_info()[0]))
        return style

    def load_song(self, songname):
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
        return song

    def fragmentname(self, trackname, staffname, chordname):
        ct = cleanup_string_for_lilypond(trackname)
        cs = cleanup_string_for_lilypond(staffname)
        cc = cleanup_string_for_lilypond(chordname)
        return ct + cs + cc

    def voicename(self, trackname, staffname):
        ct = cleanup_string_for_lilypond(trackname)
        cs = cleanup_string_for_lilypond(staffname)
        return ct + cs;

    def voicefragmentname(self, trackname, staffname):
        return self.voicename(trackname, staffname) + "Voice"

    def lyricsfragmentname(self, trackname, staffname):
        return self.voicenamefragmentname(trackname, staffname) + "Lyrics"

    def compile(self):
        # read song and style specs
        song = self.load_song(self.options.inputfile[0])
        song_style = song["style"]
        song_title = song["header"]["title"]
        song_writer = song["header"]["composer"]
        print("*** Rendering {0} by {1} to lilypond".format(song_title, song_writer))

        # read style specs
        style = self.load_style(song_style)

        # read lilypond template
        lytemplate = Template(filename=os.path.join(self.rootpath, "ly-templates", "score.mako"))

        globalproperties = merge_dicts(style["global"], song["global"])

        chorddefinitions, knownchords = self.calculate_chord_definitions(style)
        harvestedproperties = self.calculate_voice_definitions(knownchords, chorddefinitions, song, style)
        stavedefinitions, tracktostaff = self.calculate_staff_definitions(harvestedproperties)

        sorted_track_names = []
        for name in harvestedproperties.sorted_song_tracks:
            sorted_track_names.append(tracktostaff[name])
        for name in harvestedproperties.sorted_style_tracks:
            sorted_track_names.append(tracktostaff[name])

        if self.options.outputfile:
            filename = os.path.abspath(self.options.outputfile[0])
            if os.path.isfile(filename) and not self.options.force:
                print ("*** REFUSING TO OVERWRITE EXISTING OUTPUT FILE {0}! QUIT. (use --force to overwrite existing files).".format(self.options.outputfile))
                sys.exit(1)
            elif os.path.isfile(filename) and self.options.force:
                print ("*** WARNING: OVERWRITING EXISTING OUTPUT FILE {0} AS REQUESTED!".format(self.options.outputfile))

            try:
                with open(filename, "w") as f:
                    f.write(lytemplate.render(headerproperties=song["header"],
                                globalproperties=globalproperties,
                                chorddefinitions=chorddefinitions,
                                voicedefinitions=harvestedproperties.voicedefinitions,
                                stavedefinitions=stavedefinitions,
                                parts=sorted_track_names,
                                tempo=song["midi"]["tempo"]))
                    print ("*** Wrote result in {0}. Please run lilypond on that file.".format(filename))

            except:
                print("*** ERROR WRITING TO FILE {0}. COMPILATION FAILED.".format(self.options.outputfile))
        else:
            print(lytemplate.render(headerproperties=song["header"],
                                    globalproperties=globalproperties,
                                    chorddefinitions=chorddefinitions,
                                    voicedefinitions=harvestedproperties.voicedefinitions,
                                    stavedefinitions=stavedefinitions,
                                    parts=sorted_track_names,
                                    tempo=song["midi"]["tempo"]))

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
                    all_staffprops.append({ 'instrumentName' : harvestedproperties.instrumentname[staffname]})
                    staffdefinition = stafftemplate.render(
                        staffname=staffname + "Staff",
                        staffproperties=all_staffprops,
                        voicefragmentname=voicename,
                        clef=harvestedproperties.hasclef[voicename],
                        lyricsname=lyricsname)
                    stavedefinitions.append(staffdefinition)
                    tracktostaff[staffname] = staffname+"Staff"
            elif stafftype == "PianoStaff":
                no_of_voices = len(harvestedproperties.stafftypes[staffname])
                lyricsname = {}
                sorted_voices = []
                for i, voice in enumerate(harvestedproperties.stafftypes[staffname]):
                    voicename = voice[1]
                    sorted_voices.append((int_to_roman(i + 1), voicename))
                    stafftemplate = Template(filename=os.path.join(self.rootpath, "ly-templates", "PianoStaff.mako"))
                    lyricsname[voicename] = None
                    if harvestedproperties.haslyrics[voicename]:
                        lyricsname[voicename] = voicename + "Lyrics"
                staffdefinition = stafftemplate.render(
                    staffname=staffname + "PianoStaff",
                    staffproperties=[{'instrumentName': harvestedproperties.instrumentname[staffname]}],
                    voicenames=sorted_voices,
                    voiceproperties=harvestedproperties.staffproperties,
                    clef=harvestedproperties.hasclef,
                    lyricsname=lyricsname
                )
                stavedefinitions.append(staffdefinition)
                tracktostaff[staffname] = staffname+"PianoStaff"
            else:
                assert False, "Stafftype {0} not supported yet!!!".format(stafftype)
        return stavedefinitions, tracktostaff

    def calculate_chord_definitions(self, style):
        chorddefinitions = {}
        knownchords = defaultdict(set)
        for name in style["tracks"]:
            if name in chorddefinitions:
                print("*** WARNING: track with name {0} is specified multiple times".format(name))
            chorddefinitions[name] = []

            for staff in style["tracks"][name]["staves"]:
                for chord in style["tracks"][name]["staves"][staff]["chords"]:
                    fragcontent = style["tracks"][name]["staves"][staff]["chords"][chord]
                    self.register_chord(name, staff, chord, fragcontent, knownchords, chorddefinitions)

        return chorddefinitions, knownchords

    def register_chord(self, name, staff, chord, fragcontent, knownchords, chorddefinitions):
        knownchords[name].add(chord)
        fragname = self.fragmentname(name, staff, chord)
        fragment = "{0} = {1}".format(fragname, fragcontent)
        chorddefinitions[name].append(fragment)

    def calculate_voice_definitions(self, knownchords, chorddefinitions, song, style):
        h = HarvestedProperties()
        refpitch = style["specified-relative-to"]["key"]
        for name in style["tracks"]:
            if "instrumentName" in style["tracks"][name]:
                h.instrumentname[name] = style["tracks"][name]["instrumentName"]
            else:
                h.instrumentname[name] = name
            h.sorted_style_tracks.append(name)
            for staff in style["tracks"][name]["staves"]:
                destpitch = refpitch[:] # reset for each staff
                voicefragmentname = self.voicefragmentname(name, staff)
                h.stafftypes[name].append( (style["tracks"][name]["type"], voicefragmentname)  )
                h.staffproperties[voicefragmentname].append( style["tracks"][name]["staves"][staff]["staffProperties"])
                h.hasclef[voicefragmentname] = "treble"
                if "clef" in style["tracks"][name]["staves"][staff]:
                    h.hasclef[voicefragmentname] = style["tracks"][name]["staves"][staff]["clef"]
                staff_voice_template = Template(filename=os.path.join(self.rootpath, "ly-templates", "voice.mako"))
                voicename = self.voicename(name, staff)
                musicelements = []
                h.haslyrics[voicefragmentname] = False
                previous_chord = None
                vl = VoiceLeader()

                for harmonyelement in song["harmony"]:
                    if "chords" in harmonyelement:
                        chords = harmonyelement["chords"]
                        import re
                        chords = re.split(" |\|\n|\t", chords)
                        for c in chords:
                            if c in knownchords[name]:
                                if refpitch == destpitch:
                                    musicelements.append("\\" + self.voicename(name, staff) + \
                                                         cleanup_string_for_lilypond(c))
                                else:
                                    musicelements.append( "{{ \\transpose {0} {1} {{ {2} }} }}".format(refpitch,
                                                                                                       destpitch,
                                                                                                       "\\" + self.voicename(
                                                                                                           name,
                                                                                                           staff) + \
                                                                                                       cleanup_string_for_lilypond(
                                                                                                           c)))
                                previous_chord = c
                            elif self.to_be_derived_from_existing(c): # calculate from previous chord
                                cname = cleanup_string_for_lilypond("{0}".format(c))
                                vname = self.voicename(name,staff) + cname
                                number, accidental, modifier = split_roman_prefix(c)
                                one_chord = "I" + modifier

                                if "I" not in knownchords[name]:
                                    print("ERROR! Style always needs at least specification of the I chord.")
                                    print("In case of track {0}, staff {1} we couldn't find it.".format(name,staff))
                                    print("Bailing out.")
                                    sys.exit(1)

                                if one_chord not in knownchords[name] and (
                                not modifier.startswith("m")) and modifier != "":
                                    # minor can be calculated from major if needed; other types require explicit hints
                                    print("ERROR! Cannot find chord {0} in style file.".format(one_chord))
                                    print("Need it to calculate chord {0} in track {1}, staff {2}.".format(c,
                                                                                                        name,
                                                                                                        staff))
                                    print("Bailing out.")
                                    sys.exit(2)

                                elif one_chord not in knownchords[name] and modifier.startswith("m"):
                                    #
                                    # e.g. you try to calculat VIm but Im doesn't exist in the style file
                                    # in that case: calculate VIm from I.
                                    #
                                    style_scale = style["specified-relative-to"]["key"]
                                    style_scale_mode = style["specified-relative-to"]["mode"]
                                    name_to_constructor = {
                                        "major" : music21.scale.MajorScale,
                                        "minor" : music21.scale.MinorScale
                                    }
                                    source_scale = name_to_constructor[style_scale_mode](style_scale)
                                    sourcepitch = music21.pitch.Pitch(style_scale)
                                    target_distance = self.scaledegree_distance_from_I(number+accidental)
                                    target_interval = music21.interval.Interval(target_distance)
                                    target_pitch = music21.interval.transposePitch(sourcepitch, target_interval)
                                    target_scale = music21.scale.MinorScale(target_pitch.name)
                                    fragment = style["tracks"][name]["staves"][staff]["chords"]["I"]
                                    vl = VoiceLeader()
                                    l = Lily2Stream()
                                    s = l.parse(fragment)
                                    note_stream = s.flat.getElementsByClass(["Note"])
                                    pitches = [ n.pitch for n in note_stream ]
                                    result = vl.calculate(pitches, source_scale, target_scale,
                                                 reorder_notes=SHIIHS_VOICELEADING, map_accidentals=True)
                                    for p, n in enumerate(note_stream):
                                        n.pitch = result[p]
                                    new_fragment = "{ " + l.unparse(s.flat.getElementsByClass(["Note","Rest"])) + " }"
                                    if refpitch == destpitch:
                                        musicelements.append("\\"+vname)
                                    else:
                                        musicelements.append("{{ \\transpose {0} {1} {{ {2} }} }}".format(refpitch,
                                                                                                         destpitch,
                                                                                                       "\\"+vname))
                                    self.register_chord(name, staff, c, new_fragment, knownchords, chorddefinitions)

                                elif one_chord in knownchords[name]:
                                    #
                                    # e.g. you try to find VIm7 and Im7 exists in the style file
                                    #
                                    style_scale = style["specified-relative-to"]["key"]
                                    style_scale_mode = style["specified-relative-to"]["mode"]
                                    name_to_constructor = {
                                        "major" : music21.scale.MajorScale,
                                        "minor" : music21.scale.MinorScale
                                    }
                                    source_scale = name_to_constructor[style_scale_mode](style_scale)
                                    sourcepitch = music21.pitch.Pitch(style_scale)
                                    target_distance = self.scaledegree_distance_from_I(number+accidental)
                                    target_interval = music21.interval.Interval(target_distance)
                                    target_pitch = music21.interval.transposePitch(sourcepitch, target_interval)
                                    target_scale = music21.scale.MajorScale(target_pitch.name)
                                    if "m" in modifier:
                                        target_scale = music21.scale.MinorScale(target_pitch.name)
                                    # start from Im7 to calculate VIm7
                                    fragment = style["tracks"][name]["staves"][staff]["chords"][one_chord]
                                    vl = VoiceLeader()
                                    l = Lily2Stream()
                                    s = l.parse(fragment)
                                    note_stream = s.flat.getElementsByClass(["Note"])
                                    pitches = [ n.pitch for n in note_stream ]
                                    result = vl.calculate(pitches, source_scale, target_scale,
                                                 reorder_notes=SHIIHS_VOICELEADING, map_accidentals=True)
                                    for p, n in enumerate(note_stream):
                                        n.pitch = result[p]
                                    new_fragment = "{ " + l.unparse(s.flat.getElementsByClass(["Note","Rest"])) + " }"
                                    if refpitch == destpitch:
                                        musicelements.append("\\"+vname)
                                    else:
                                        musicelements.append("{{ \\transpose {0} {1} {{ {2} }} }}".format(refpitch,
                                                                                                         destpitch,
                                                                                                       "\\"+vname))
                                    self.register_chord(name, staff, c, new_fragment, knownchords, chorddefinitions)

                                previous_chord = c

                            else:
                                musicelements.append(c)

                    elif "ly" in harmonyelement:
                        e = harmonyelement["ly"]
                        if type(e) == type([]):
                            for el in e:
                                musicelements.append(el)
                        else:
                            musicelements.append(e)
                    elif "transpose" in harmonyelement:
                        destpitch = harmonyelement["transpose"]["to"]

                voice = staff_voice_template.render(voicefragmentname=voicefragmentname,
                                                    musicelements=musicelements)
                h.voicedefinitions.append(voice)
        if "tracks" in song:
            for name in song["tracks"]:
                for staff in song["tracks"][name]["staves"]:
                    destpitch = refpitch[:]
                    if "instrumentName" in song["tracks"][name]:
                        h.instrumentname[name] = song["tracks"][name]["instrumentName"]
                    else:
                        h.instrumentname[name] = name
                    h.sorted_song_tracks.append(name)
                    voicefragmentname = self.voicefragmentname(name, staff)
                    h.stafftypes[name].append((song["tracks"][name]["type"], voicefragmentname))
                    h.staffproperties[voicefragmentname].append(
                            song["tracks"][name]["staves"][staff]["staffProperties"])
                    h.hasclef[voicefragmentname] = "treble"
                    if "clef" in song["tracks"][name]["staves"][staff]:
                        h.hasclef[voicefragmentname] = style["tracks"][name]["staves"][staff]["clef"]
                    staff_voice_template = Template(filename=os.path.join(self.rootpath, "ly-templates", "voice.mako"))
                    musicelements = []
                    for element in song["tracks"][name]["staves"][staff]["music"]:
                        if "ly" in element:
                            lycode = element["ly"].replace("|", "|\n")
                            if refpitch == destpitch:
                                musicelements.append(lycode)
                            else:
                                musicelements.append(
                                    "{{\\transpose {0} {1} {{ {2} }} }}".format(refpitch, destpitch, lycode))
                        elif "transpose" in element:
                            destpitch = element["transpose"]["to"]
                    voice = staff_voice_template.render(voicefragmentname=voicefragmentname,
                                                        musicelements=musicelements)
                    h.voicedefinitions.append(voice)

                    if "lyrics" in song["tracks"][name]["staves"][staff]:
                        h.haslyrics[voicefragmentname] = True
                        lyrics = song["tracks"][name]["staves"][staff]["lyrics"]
                        staff_lyrics_template = Template(
                            filename=os.path.join(self.rootpath, "ly-templates", "lyrics.mako"))
                        rendered_lyrics = staff_lyrics_template.render(voicefragmentname=voicefragmentname + "Lyrics",
                                                                       musicelements=[lyrics.replace("|", "|\n")])
                        h.voicedefinitions.append(rendered_lyrics)
                    else:
                        h.haslyrics[voicefragmentname] = False
        return h

    def to_be_derived_from_existing(self, c):
        return starts_with_one_of(c.upper(), ["III", "II", "IV", "I", "VII", "VI", "V"])

    def scaledegree_distance_from_I(self, degree):
        """
        :param degree: e.g. "VIb"
        :return: chromatic distance from "I" to degree
        """
        d = {
            ("I", "I") :    0,
            ("I", "Ib") :  -1,
            ("I", "Ibb") : -2,
            ("I", "I#") :   1,
            ("I", "I##") :  2,

            ("I", "II") :    2,
            ("I", "IIb") :   1,
            ("I", "IIbb") :  0,
            ("I", "II#") :   3,
            ("I", "II##") :  4,

            ("I", "III") :    4,
            ("I", "IIIb") :   3,
            ("I", "IIIbb") :  2,
            ("I", "III#") :   5,
            ("I", "III##") :  6,

            ("I", "IV") :    5,
            ("I", "IVb") :   4,
            ("I", "IVbb") :  3,
            ("I", "IV#") :   6,
            ("I", "IV##") :  7,

            ("I", "V") :    7,
            ("I", "Vb") :   6,
            ("I", "Vbb") :  5,
            ("I", "V#") :   8,
            ("I", "V##") :  9,

            ("I", "VI") :    9,
            ("I", "VIb") :   8,
            ("I", "VIbb") :  7,
            ("I", "VI#") :   10,
            ("I", "VI##") :  11,

            ("I", "VII") :    11,
            ("I", "VIIb") :   10,
            ("I", "VIIbb") :  9,
            ("I", "VII#") :   12,
            ("I", "VII##") :  13,
            }
        return d[("I",degree)] if ("I",degree) in d else 0
