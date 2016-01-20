import ly.musicxml
import music21


class Lily2Stream(object):
    """
    class that converts simple lilypond fragments (containing only notes,rests and chords)
    to music21 streams
    """
    def __init__(self):
        pass

    @staticmethod
    def parse(lytext=""):
        """
        convert from lilypond to stream
        :param lytext: string containing simple lilypond fragment, e.g. "{ a b c }"
        :return: music21 stream
        """
        e = ly.musicxml.writer()
        e.parse_text(lytext)
        xml = e.musicxml()
        m = xml.tostring().decode("utf-8")
        s = music21.converter.parse(m, format="musicxml")
        return s

    @staticmethod
    def unparse(stream):
        """
        convert from music21 stream to lilypond fragment
        :param stream
        :return: string containing lilypond code fragment
        """
        lpc = music21.lily.translate.LilypondConverter()
        lp_music_list = music21.lily.lilyObjects.LyMusicList()
        lpc.context = lp_music_list
        lpc.appendObjectsToContextFromStream(stream)
        return str(lpc.context)

if __name__ == "__main__":

    # first triplet of single notes -> these work well
    l = Lily2Stream()
    s = l.parse("{ \\times2/3 { a8 b c } }")
    s.show("txt")

# looks ok:
#{0.0} <music21.metadata.Metadata object at 0x7feb9e3e42e8>
#{0.0} <music21.stream.Part 0x7feb9e3e4668>
#    {0.0} <music21.instrument.Instrument P1: >
#    {0.0} <music21.stream.Measure 1 offset=0.0>
#        {0.0} <music21.clef.TrebleClef>
#        {0.0} <music21.meter.TimeSignature 4/4>
#        {0.0} <music21.note.Note A>
#        {0.3333} <music21.note.Note B>
#        {0.6667} <music21.note.Note C>

    #s.show("musicxml") # looks ok
    print(l.unparse(s))
# looks ok:
# \new Staff  = xawweyfawxbxyzy { \partial 32*8
#      \clef "treble"
#      \time 4/4
#      \times 2/3 { a 8
#         b 8
#         c 8
#          }
#
#      \bar "|"  %{ end measure 1 %}
#       }

    # now triplet of chords -> these do not serialize to lilypond correctly
    # (but they do serialize to musicxml correctly)
    s = l.parse("{ \\times2/3 { <a c>8 <a b> <a c> } }")
    s.show("txt")

#looks ok:
#{0.0} <music21.metadata.Metadata object at 0x7feb9be4e390>
#{0.0} <music21.stream.Part 0x7feb9be4ea90>
#    {0.0} <music21.instrument.Instrument P1: >
#    {0.0} <music21.stream.Measure 1 offset=0.0>
#        {0.0} <music21.clef.TrebleClef>
#        {0.0} <music21.meter.TimeSignature 4/4>
#        {0.0} <music21.chord.Chord A3 C3>
#        {0.3333} <music21.chord.Chord A3 B3>
#        {0.6667} <music21.chord.Chord A3 C3>

    #s.show("musicxml") # looks ok
    print(l.unparse(s))

#wrong: triplet lost
#\new Staff  = xawweyfzfedaaaw { \partial 32*8
#      \clef "treble"
#      \time 4/4
#      < a  c  > 8
#      < a  b  > 8
#      < a  c  > 8
#      \bar "|"  %{ end measure 1 %}
#       }