import ly.musicxml
import music21

class Lily2Stream(object):
    def __init__(self):
        pass

    def parse(self, lytext=""):
        e = ly.musicxml.writer()
        e.parse_text(lytext)
        xml = e.musicxml()
        m = xml.tostring().decode("utf-8")
        s = music21.converter.parse(m, format="musicxml")
        return s

    def unparse(self, stream):
        lpc = music21.lily.translate.LilypondConverter()
        lp_music_list = music21.lily.lilyObjects.LyMusicList()
        lpc.context = lp_music_list
        lpc.appendObjectsToContextFromStream(stream)
        return str(lpc.context)

if __name__ == "__main__":
    l = Lily2Stream();
    l.parse("{ <a b> }").show("txt")
