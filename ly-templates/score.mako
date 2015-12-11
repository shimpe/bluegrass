\version "2.18.2"

\header {
% for property in headerproperties:
    ${property} = "${headerproperties[property]}"
% endfor
}

global = {
% for property in globalproperties:
    \${property} ${globalproperties[property]}
% endfor
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% begin of style fragment definitions
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% for c in chorddefinitions:

%%%% track ${c}
%   for fragment in chorddefinitions[c]:
${fragment}
%   endfor
% endfor

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% begin of song voice definitions (made from style fragments)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% for voicedef in voicedefinitions:
${voicedef}
% endfor

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% begin of staff definitions (staves embed voices)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% for staff in stavedefinitions:
${staff}
% endfor

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% making score from staves (the score groups staves)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\score {
 <<
 % for p in parts:
    \${p}
 % endfor
 >>

  \layout { }
  \midi {
    \tempo 4=${tempo}
  }
}
