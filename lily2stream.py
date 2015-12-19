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
        e = ly.musicxml.writer()
        e.parse_text(lytext)
        xml = e.musicxml()
        m = xml.tostring().decode("utf-8")
        s = music21.converter.parse(m, format="musicxml")
        return s

    @staticmethod
    def unparse(stream):
        lpc = music21.lily.translate.LilypondConverter()
        lp_music_list = music21.lily.lilyObjects.LyMusicList()
        lpc.context = lp_music_list
        lpc.appendObjectsToContextFromStream(stream)
        return str(lpc.context)

if __name__ == "__main__":
    Lily2Stream.parse("{ <a b> }").show("txt")
    l = Lily2Stream()
    l.parse("{ a, b'' r <c d> }").show("txt")
