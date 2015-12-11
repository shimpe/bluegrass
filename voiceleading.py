import random
import copy
from collections import defaultdict

import music21

_VERYLARGENUMBER = 1000000  # effectively infinity
_MODULUS = 12  # size of the octave

_HALFMODULUS = int(0.5 + _MODULUS / 2.0)

DIRECT_TRANSPOSITION = 0
NAIVE_VOICELEADING = 2
TYMOCZKO_VOICELEADING = 3
SHIIHS_VOICELEADING = 1

"""

voiceleading_utilities version 1.0, (c) 2015 by Dmitri Tymoczko

Voiceleading_utilities is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser
General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
option) any later version. Voiceleading_utilities is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.   You should have received a copy of the GNU Lesser General Public
License along with Voiceleading_utilities.  If not, see <http://www.gnu.org/licenses/>.

A set of routines that identify the minimal voice leadings between sets of pitches and pitch classes.

1. bijective_vl finds the best bijective voice leading between pitch-class sets assuming a fixed number of voices
-  use this if you want to control the number of voices exactly, e.g., a 3-voice voice leading from [C, E, G] to [F, A,
C], or a 4-voice voice leading from [G, B, D, F] to [C, C, E, G]
- this routine will also rank all the voice-leadings by size, so that, e.g. you can use the second-most efficient voice
leading if you want NB: this routine passes back pairs of the form [startPC, path]

2. voicelead takes an input set of pitches and a target set of PCs, and outputs a set of pitches;
    - this is useful if you are generating music, and have a specific C-major chord in register; it will tell you where
each voice should go there is an option here to randomly choose one of the N most efficient voice leadings, so you are
not always restricted to the most efficient ones

3. nonbijective_vl allows notes to be doubled; sometimes this produces a more efficient voice leading than a bijective
voice leading
    - for this reason, you cannot always control the number of voices
    NB: this routine passes back pairs of PCs, from which you may need to calculate paths

(For details on the nonbijective_vl algorithm, see Tymozko, D., "The Geometry of Musical Chords", Science, 2006.)

Sometimes, you want something in between, e.g. the best 4-voice voice leading between triads or from a 4-voice seventh
to a triad; in this case, you need to iterate bijective_vl over all possible doublings of the chords.
This can be time consuming.

TODO: allow different choices of metric

"""

"""====================================================================================================================

bijective_vl expects two SORTED equal-length sets of integers representing PCs (in any modulus).
the sort parameter sorts the possible bijective VLs by size; by default it is set to False.  Set it to true only if you
want to choose from among the n most efficient VLs"""


def bijective_vl(first_pcs, second_pcs, sort=False):
    if len(first_pcs) != len(second_pcs):
        return False
    bijective_vl.full_list = []  # collects all the bijective VLs along with their size
    current_best = []  # current_best records the best VL we have found so far
    current_best_size = _VERYLARGENUMBER  # current_best_size is the size of the current best VL
    # (starts at infinity)
    new_size = 0
    new_paths = []
    for x in range(0, len(first_pcs)):  # iterate through every inversion of the  second PC
        second_pcs = second_pcs[-1:] + second_pcs[:-1]
        new_size = 0
        new_paths = []
        for i in range(0, len(first_pcs)):
            path = (second_pcs[i] - first_pcs[i]) % _MODULUS  # calculate most efficient path based on the pairs
            if path > _HALFMODULUS:  # negative numbers for descending paths
                path -= _MODULUS
            new_paths.append([first_pcs[i], path])
            new_size += abs(path)
        bijective_vl.full_list.append([new_paths, new_size])
    if new_size < current_best_size:  # record the current best size
        current_best_size = new_size
        current_best = new_paths
    bijective_vl.size = current_best_size
    if sort:
        bijective_vl.full_list = sorted(bijective_vl.full_list, key=lambda p: p[1])
    return current_best


"""===================================================================================================================

voicelead expects a source list of PITCHES and a target list of PCs, both should be the same length; it outputs one of
the topN most efficient voice leadings from the source pitches to the target PCs.
if topN is 1, it gives you the most efficient voice leading"""


def voicelead(in_pitches_input, target_pcs_output, top_n=1):
    in_pitches = [p.midi for p in in_pitches_input]
    target_pcs = [p.midi for p in target_pcs_output]
    in_pcs = sorted([p % _MODULUS for p in in_pitches])  # convert input pitches to PCs and sort them
    target_pcs = sorted(target_pcs)
    paths = bijective_vl(in_pcs, target_pcs, top_n != 1)  # find the possible bijective VLs
    if top_n != 1:  # randomly select on of the N most efficient
        # possibilities
        my_range = min(len(bijective_vl.full_list), top_n)
        paths = bijective_vl.full_list[random.randrange(0, my_range)][0]
    output = []
    temp_paths = paths[:]  # copy the list of paths
    for in_pitch in in_pitches:
        for path in temp_paths:  # when we find a path remove it from our list
            # (so we don't duplicate paths)
            if (in_pitch % _MODULUS) == path[0]:
                output.append(in_pitch + path[1])
                temp_paths.remove(path)
                break

    midi_to_pitch = []
    # print (output)
    from itertools import chain
    for m in output:
        for p in chain(target_pcs_output, in_pitches_input):
            if p.midi == m:
                midi_to_pitch.append(p)
                break
    # print (midi_to_pitch)
    return midi_to_pitch


"""====================================================================================================================

nonbijective_vl expects a source list of PCs or pitches and a target list of PCs or pitches, of any lengths; it outputs
the most efficient voice leading from source to target.  Voices can be arbitrarily doubled.

To see why this is interesting, compare bijective_vl([0, 4, 7, 11], [4, 8, 11, 3]) to nonbijective_vl([0, 4, 7, 11],
[4, 8, 11, 3])

for PCs, nonbijective_vl iterates over every inversion of the target chord; for each inversion it builds a matrix
showing the most efficient voice leading such that the first note of source goes to the first note of target
(see Tymoczko "The Geometry of Musical Chords" for details)

TODO: choose the smaller of source and target to iterate over??
"""


def nonbijective_vl(source, target, pcs=True):
    cur_vl = []
    cur_size = _VERYLARGENUMBER
    if pcs:
        source = [x % _MODULUS for x in source]
        target = [x % _MODULUS for x in target]
    source = sorted(list(set(source)))
    target = sorted(list(set(target)))
    temp_target = []
    if pcs:
        for i in range(len(target)):  # for PCs, iterate over every inversion of the target
            temp_target = target[i:] + target[:i]
            new_size = build_matrix(source, temp_target)  # generate the matrix for this pairing
            if new_size < cur_size:  # save it if it is the most efficient we've found
                cur_size = new_size
                cur_vl = find_matrix_vl()
        cur_vl = cur_vl[:-1]
    else:
        cur_size = build_matrix(source, temp_target)  # no need to iterate for pitches
        cur_vl = find_matrix_vl()
    return cur_size, cur_vl


def build_matrix(source, target, pcs=True):  # requires sorted source and target chords
    global theMatrix
    global outputMatrix
    global globalSource
    global globalTarget
    if pcs:
        source = source + [source[0]]
        target = target + [target[0]]

        def distance_func(x, y):
            return min((x - y) % _MODULUS, (y - x) % _MODULUS)  # add **2 for Euclidean distance
    else:

        def distance_func(x, y):
            return abs(x - y)
    globalSource = source
    globalTarget = target
    theMatrix = []
    for target_item in target:
        theMatrix.append([])
        for source_item in source:
            theMatrix[-1].append(distance_func(target_item, source_item))
    outputMatrix = [x[:] for x in theMatrix]
    i = j = 0
    for i in range(1, len(outputMatrix[0])):
        outputMatrix[0][i] += outputMatrix[0][i - 1]
    for i in range(1, len(outputMatrix)):
        outputMatrix[i][0] += outputMatrix[i - 1][0]
    for i in range(1, len(outputMatrix)):
        for j in range(1, len(outputMatrix[i])):
            outputMatrix[i][j] += min([outputMatrix[i][j - 1], outputMatrix[i - 1][j], outputMatrix[i - 1][j - 1]])
    return outputMatrix[i][j] - theMatrix[i][j]


def find_matrix_vl():  # identifies the voice leading for each matrix
    the_vl = []
    i = len(outputMatrix) - 1
    j = len(outputMatrix[i - 1]) - 1
    the_vl.append([globalSource[j], globalTarget[i]])
    while i > 0 or j > 0:
        new_i = i
        new_j = j
        my_min = _VERYLARGENUMBER
        if i > 0 and j > 0:
            new_i = i - 1
            new_j = j - 1
            my_min = outputMatrix[i - 1][j - 1]
            if outputMatrix[i - 1][j] < my_min:
                my_min = outputMatrix[i - 1][j]
                new_j = j
            if outputMatrix[i][j - 1] < my_min:
                my_min = outputMatrix[i][j - 1]
                new_i = i
            i = new_i
            j = new_j
        elif i > 0:
            i -= 1
        elif j > 0:
            j -= 1
        the_vl.append([globalSource[j], globalTarget[i]])
    return the_vl[::-1]


"""====================================================================================================================

A simple routine to put voice leadings in 'normal form.'  Essentially, we just apply the standard "left-packing"
algorithm to the first element
in a list of [startPC, path] pairs.

"""


def vl_normal_form(in_list):  # list of [PC, path] pairs
    my_list = sorted([[k[0] % _MODULUS] + k[1:] for k in in_list])
    current_best = [[(k[0] - my_list[0][0]) % _MODULUS] + k[1:] for k in my_list]
    vl_normal_form.transposition = my_list[0][0] * -1
    for i in range(1, len(my_list)):
        new_challenger = my_list[-i:] + my_list[:-i]
        transp = new_challenger[0][0] * -1
        new_challenger = sorted([[(k[0] - new_challenger[0][0]) % _MODULUS] + k[1:] for k in new_challenger])
        for j in reversed(range(len(my_list))):
            if new_challenger[j][0] < current_best[j][0]:
                current_best = new_challenger
                vl_normal_form.transposition = transp
            else:
                if new_challenger[j][0] > current_best[j][0]:
                    break
    return current_best

"""
Here starts code written by Stefaan Himpe
GPL License
"""

class VoiceLeader(object):
    """
    class to calculate voice leading from one pattern to the next
    (C) 2015 Stefaan Himpe - LGPL license
    """
    def __init__(self):
        pass

    def add_accidental_to_pitch_accidental(self, pitch, accidental):
        """
        :param pitch: a given pitch (with an optional accidental)
        :param accidental: new accidental to add on top of the existing accidental
        :return: new pitch with both accidentals combined
        """
        original_accidental = pitch.accidental
        f = music21.pitch.Accidental("flat")
        df = music21.pitch.Accidental("double-flat")
        tf = music21.pitch.Accidental("triple-flat")
        qf = music21.pitch.Accidental("quadruple-flat")
        s = music21.pitch.Accidental("sharp")
        ds = music21.pitch.Accidental("double-sharp")
        ts = music21.pitch.Accidental("triple-sharp")
        qs = music21.pitch.Accidental("quadruple-sharp")

        acc_amount_to_new_acc = {

            (df, df): qf,
            (df, f): tf,
            (df, None): df,
            (df, s): f,
            (df, ds): None,

            (f, df): tf,
            (f, f): df,
            (f, None): f,
            (f, s): None,
            (f, ds): s,

            (None, df): df,
            (None, f): f,
            (None, None): None,
            (None, s): s,
            (None, ds): ds,

            (s, df): f,
            (s, f): None,
            (s, None): s,
            (s, s): ds,
            (s, ds): ts,

            (ds, df): None,
            (ds, f): s,
            (ds, None): ds,
            (ds, s): ts,
            (ds, ds): qs
        }

        pitch.accidental = acc_amount_to_new_acc[(original_accidental, accidental)]
        if pitch.accidental in [tf, qf, ts, qs]:
            # warning... following call will turn "A###" into "C" instead of "B#" ...
            pitch.simplifyEnharmonic(inPlace=True)

        return pitch

    def calculate(self, from_fragment, from_scale, to_scale, reorder_notes=False, map_accidentals=True):
        """
        :param from_fragment: list of pitches
        :param from_scale: scale in which the above pitches are to be interpreted
        :param to_scale: scale into which the pitches should be (modally) transposed
        :param reorder_notes: reorder notes in resulting fragment to minimize voice leading distance
        :param map_accidentals: keep to map the notes that fall outside the scale as well
        :return: to_fragment: new fragment with minimal voice leading distance to from_fragment
        """
        degrees_accidentals = [from_scale.getScaleDegreeAndAccidentalFromPitch(n) for n in from_fragment]
        target_pitches_without_accidentals = [to_scale.pitchFromDegree(d[0]) for d in degrees_accidentals]
        target_pitches = []
        if map_accidentals:
            for p, d in zip(target_pitches_without_accidentals, degrees_accidentals):
                target_pitches.append(self.add_accidental_to_pitch_accidental(p, d[1]))
        else:
            target_pitches = target_pitches_without_accidentals

        src2target = {}
        if not reorder_notes:
            for srcpitch, targetpitch in zip(from_fragment, target_pitches):
                src2target[srcpitch] = targetpitch
        elif reorder_notes == NAIVE_VOICELEADING:
            src2target_helper = defaultdict(lambda: tuple((None, 1e10, 1e10)))
            for srcpitch in from_fragment:
                for targetpitch in target_pitches:
                    st = min(music21.interval.notesToChromatic(srcpitch, targetpitch).semitones % 12,
                             music21.interval.notesToChromatic(targetpitch, srcpitch).semitones % 12)
                    namediff = min(music21.interval.notesToChromatic(music21.pitch.Pitch(srcpitch.step),
                                                                     music21.pitch.Pitch(
                                                                         targetpitch.step)).semitones % 12,
                                   music21.interval.notesToChromatic(music21.pitch.Pitch(targetpitch.step),
                                                                     music21.pitch.Pitch(srcpitch.step)).semitones % 12)
                    if (st < src2target_helper[srcpitch][2]) or \
                            (st == src2target_helper[srcpitch][2] and namediff < src2target_helper[srcpitch][1]):
                        tp = copy.deepcopy(targetpitch)
                        tp.octave = srcpitch.octave
                        src2target_helper[srcpitch] = (tp, namediff, st)
            for p in src2target_helper:
                src2target[p] = src2target_helper[p][0]
        elif reorder_notes == TYMOCZKO_VOICELEADING:
            vl = voicelead(from_fragment, target_pitches, top_n=2)
            for srcpitch, targetpitch in zip(from_fragment, vl):
                src2target[srcpitch] = targetpitch
        elif reorder_notes == SHIIHS_VOICELEADING:
            ###
            # algorithm:
            #
            # we have pitches in the original or from_fragment, e.g. [C, E, G]
            # we have target pitches, which are the orignal pitches modally transposed in the new key, e.g. [F, A, C]
            #
            # we try to find a mapping from pitches in the from_fragment, to pitches in the to_fragment
            # where midi distance between original pitch and new pitch is minimal
            #
            # we also try to avoid repeating pitches in time
            # the result in this example should be the mapping:
            # from [C, E, G] => [C, F, A]
            ###

            # first calculate the cost from every srcpitch to every targetpitch
            # store the resulting mapping ( (srcpitch,targetpitch) => cost ) in matrix
            matrix = {}
            for srcpitch in from_fragment:
                for targetpitch in target_pitches:
                    # enlarge the possibilities by transposing the target pitches
                    # an octave up and down
                    tlower = copy.deepcopy(targetpitch)
                    tlower.octave -= 1
                    tupper = copy.deepcopy(targetpitch)
                    tupper.octave += 1
                    expanded_target_pitch = [ targetpitch, tlower, tupper]
                    for t in expanded_target_pitch:
                        matrix[(srcpitch, t)] = self.calculate_cost(srcpitch, t)

            # now reverse the mapping: from cost to map(src->target)
            inv_matrix = defaultdict(list)
            for (s, t) in matrix:
                inv_matrix[matrix[(s, t)]].append((s, t))

            # now investigate which (src -> target) to select
            max_distance = max(inv_matrix.keys())
            previous_note = None
            # we need to map every note in the from_fragment to a new note in the resulting fragment
            for p in from_fragment:
                # map every note only once
                while p not in src2target:
                    # start with lowest cost first
                    for i in range(max_distance):
                        # if a solution with this cost exists...
                        if i in inv_matrix:
                            # select all mappings (src->target) with this cost
                            possible_notes = inv_matrix[i]
                            list_of_notes = []
                            for n in possible_notes:
                                # select from all these mappings only the ones that start with the fromFragment pitch
                                if n[0] == p:
                                    note = n[1]
                                    list_of_notes.append(note)
                            if list_of_notes:
                                # if multiple candidate mappings, select the one with smallest
                                # difference to the previous note
                                if previous_note:
                                    distance_to_prev_note = defaultdict(list)
                                    for note in list_of_notes:
                                        distance_to_prev_note[self.calculate_cost(previous_note, note)].append(note)
                                    keys = distance_to_prev_note.keys()
                                    if len(keys) > 1 and 0 in keys:
                                        del distance_to_prev_note[0] # avoid repeating the same note if feasible
                                    best_note_key = min(distance_to_prev_note.keys())
                                    note = random.choice(distance_to_prev_note[best_note_key])
                                    if note == previous_note:
                                        continue # search for another note with higher cost (TODO: guaranteed to exist?)
                                else:
                                    note = random.choice(list_of_notes)
                                    if note == previous_note:
                                        continue # search for another note with higher cost (TODO: guaranteed to exist?)
                                src2target[p] = note
                                previous_note = note
                                break

        target_pitches_with_accidentals = [src2target[p] for p in from_fragment]
        return target_pitches_with_accidentals

    def calculate_cost(self, srcpitch, targetpitch):
        # src2target_semitones = music21.interval.notesToChromatic(srcpitch, targetpitch).semitones % 12
        # target2src_semitones = music21.interval.notesToChromatic(targetpitch, srcpitch).semitones % 12
        # src2target_namediff = music21.interval.notesToChromatic(music21.pitch.Pitch(srcpitch.step),
        #                                                music21.pitch.Pitch(targetpitch.step)).semitones % 12
        # target2src_namediff = music21.interval.notesToChromatic(music21.pitch.Pitch(targetpitch.step),
        #                                                music21.pitch.Pitch(srcpitch.step)).semitones % 12
        src2target_diff = abs(srcpitch.midi - targetpitch.midi)

        return src2target_diff
         #   src2target_diff \
         # + min(src2target_namediff, target2src_namediff) \
         # + min(src2target_semitones,target2src_semitones)
