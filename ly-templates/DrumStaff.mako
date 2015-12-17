${staffname}  = \new DrumStaff \with {
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
% if instrumentName:
\set Staff.instrumentName = #"${instrumentName}"
% endif
\new DrumVoice { \${voicefragmentname} }
>>
