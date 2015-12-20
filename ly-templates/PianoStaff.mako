${staffname}  = \new PianoStaff \with {
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
} <<
% for idx, (i, v) in enumerate(voicenames):
\new Staff = "${i}" \with {
% for q in voiceproperties[v]:
%    for key in q:
${key} = ${q[key]}
%    endfor
% endfor
}{ \clef "${clef[v]}" \${voicenames[idx][1]} }
% if lyricsname[v]:
\addlyrics { \${lyricsname[v]} }
% endif
% endfor
>>

