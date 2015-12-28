import argparse
import stylecompiler
import sys
import os


def get_own_path():
    pathname = os.path.dirname(sys.argv[0])
    ap = os.path.abspath(pathname)
    return ap


def setup_argument_parser():
    parser = argparse.ArgumentParser(
        description="Arrange compiler for lilypond.",
        epilog="Thank you for smoking bluegrass.")
    parser.add_argument("-i", "--inputfile", dest="inputfile", default=["samples/test_muteunmute_melody_lyrics.yaml"], nargs=1)
    parser.add_argument("-o", "--outputfile", dest="outputfile", default=["output/cowboy.ly"], nargs=1)
    parser.add_argument("-f", "--force", dest="force", action="store_true", default=False)
    return parser


if __name__ == "__main__":
    p = setup_argument_parser()
    options = p.parse_args()
    rootpath = get_own_path()
    print("*** rootpath = ", rootpath)
    s = stylecompiler.StyleCompiler(rootpath, options)
    s.compile()
