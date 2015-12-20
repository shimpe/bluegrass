${staffname}  = \new Staff \with {
% for p in staffproperties:
%    for key in p:
${key} = ${p[key]}
%    endfor
% endfor
% for p in staffoverrides:
%    for key in p:
\override ${key}=${p[key]}
%    endfor
% endfor
} { \clef "${clef}" \${voicefragmentname} }
% if lyricsname:
\addlyrics { \${lyricsname} }
% endif
