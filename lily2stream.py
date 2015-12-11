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

if __name__ == "__main__":
    l = Lily2Stream();
    l.parse("{a}").show("txt")