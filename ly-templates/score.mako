\version "2.18.2"

\include "articulate.ly"

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

% if chorddefinitions:
% for c in chorddefinitions:

%%%% track ${c}
%   for fragment in chorddefinitions[c]:
${fragment}
%   endfor
% endfor
% endif

% if patterndefinitions:
% for p in patterndefinitions:

%%%% drum track ${p}
%   for fragment in patterndefinitions[p]:
${fragment}
%   endfor
% endfor
% endif

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
}

\score {
\unfoldRepeats \articulate
 <<
 % for p in parts:
    \${p}
 % endfor
 >>
  \midi {
    \tempo 4=${tempo}
  }
}