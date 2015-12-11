import os
import sys

from mako.template import Template
from ruamel.yaml import load, RoundTripLoader

from harvestedproperties import HarvestedProperties
from numberutils import int_to_roman, roman_to_int
from voiceleading import VoiceLeader


def merge_dicts(x, y):
    '''Given two dicts, merge them into a new dict as a shallow copy.'''
    z = x.copy()
    z.update(y)
    return z


def cleanup_string_for_lilypond(s):
    return s.replace("_", "").replace("-", "")

def starts_with_one_of(strng, list_of_strings):
    for s in list_of_strings:
        if strng.startswith(s):
            return True
    return False

def split_roman_prefix(s):
    for i in reversed(range(len(s))):
        prefix = s[:i - 1]
        try:
            num = roman_to_int(prefix)
            print(prefix)
            suffix = s[i - 1:]
            accidental = ""
            if starts_with_one_of(suffix, ["bb", "##"]):
                accidental = suffix[:2]
                suffix = suffix[2:]
            elif starts_with_one_of(suffix, ["b", "#"]):
                accidental = suffix[:1]
                suffix = suffix[1:]
            return num, accidental, suffix
        except:
            pass
    return None, None, None

class StyleCompiler(object):
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
        song = self.load_song(self.options.inputfile)
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
        harvestedproperties = self.calculate_voice_definitions(knownchords, song, style)
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
        knownchords = set([])
        for name in style["tracks"]:
            if name in chorddefinitions:
                print("*** WARNING: track with name {0} is specified multiple times".format(name))
            chorddefinitions[name] = []

            for staff in style["tracks"][name]["staves"]:
                for chord in style["tracks"][name]["staves"][staff]["chords"]:
                    knownchords.add(chord)
                    fragname = self.fragmentname(name, staff, chord)
                    fragcontent = style["tracks"][name]["staves"][staff]["chords"][chord]
                    fragment = "{0} = {1}".format(fragname, fragcontent)
                    chorddefinitions[name].append(fragment)

        return chorddefinitions, knownchords

    def calculate_voice_definitions(self, knownchords, song, style):
        h = HarvestedProperties()
        h.voicedefinitions = []
        h.haslyrics = {}
        h.hasclef = {}
        h.instrumentname = {}
        h.sorted_style_tracks = []
        h.sorted_song_tracks = []
        refpitch = style["specified-relative-to"]
        destpitch = refpitch[:]
        from collections import defaultdict
        h.stafftypes = defaultdict(list)
        h.staffproperties = defaultdict(list)
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
                            if c in knownchords:
                                if refpitch == destpitch:
                                    musicelements.append("\\" + self.voicename(name, staff) + c)
                                else:
                                    musicelements.append( "{{ \\transpose {0} {1} {{ {2} }} }}".format(refpitch, destpitch, "\\" + self.voicename(name, staff) + c))
                                previous_chord = c
                            elif starts_with_one_of(c.upper(), ["III", "II", "IV", "I", "VII", "VI", "V"]): # calculate from previous chord
                                cname = "{0}to{1}".format(previous_chord, c)
                                vname = self.voicename(name,staff) + cname
                                print(vname)
                                musicelements.append(vname)
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

        for name in song["tracks"]:
            for staff in song["tracks"][name]["staves"]:
                destpitch = refpitch[:]
                if "instrumentName" in song["tracks"][name]:
                    h.instrumentname[name] = song["tracks"][name]["instrumentName"]
                else:
                    h.instrumentname[name] = name
                h.sorted_song_tracks.append(name)
                voicefragmentname = self.voicefragmentname(name, staff)
                h.stafftypes[name].append( (song["tracks"][name]["type"], voicefragmentname)  )
                h.staffproperties[voicefragmentname].append( song["tracks"][name]["staves"][staff]["staffProperties"])
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
                            musicelements.append("{{\\transpose {0} {1} {{ {2} }} }}".format(refpitch, destpitch, lycode))
                    elif "transpose" in element:
                        destpitch = element["transpose"]["to"]
                voice = staff_voice_template.render(voicefragmentname=voicefragmentname,
                                                    musicelements=musicelements)
                h.voicedefinitions.append(voice)

                if "lyrics" in song["tracks"][name]["staves"][staff]:
                    h.haslyrics[voicefragmentname] = True
                    lyrics = song["tracks"][name]["staves"][staff]["lyrics"]
                    staff_lyrics_template = Template(filename=os.path.join(self.rootpath, "ly-templates", "lyrics.mako"))
                    rendered_lyrics = staff_lyrics_template.render(voicefragmentname=voicefragmentname + "Lyrics",
                                                                   musicelements=[ lyrics.replace("|", "|\n") ])
                    h.voicedefinitions.append(rendered_lyrics)
                else:
                    h.haslyrics[voicefragmentname] = False

        return h
