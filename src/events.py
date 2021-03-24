import os
from miditoolkit.midi import parser
from miditoolkit.midi import containers as ct
from collections import defaultdict
import numpy as np
import itertools


pitch_classes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
chord_qualities = ['M', 'm', 'o', '+', '7', 'M7', 'm7', 'o7', '/o7', 'sus2', 'sus4']

SCALE = 12
DEFAULT_TICK_RESOL = 120
DEFAULT_STEP = DEFAULT_TICK_RESOL // SCALE
DEFAULT_BAR_RESOL = DEFAULT_TICK_RESOL * 4
DEFAULT_BPM_BINS = np.linspace(42, 296, 64, dtype=np.int)
DEFAULT_VEL_BINS = np.linspace(9, 127, 30, dtype=np.int)
DEFAULT_CHORDS = ['_'.join(e) for e in itertools.product(pitch_classes, chord_qualities)]
ALL_TOKENS = ['EOS', 'Bar'] +\
     ['Tempo_'+str(i) for i in range(len(DEFAULT_BPM_BINS))]+ \
         ['Chord_'+str(i) for i in range(len(DEFAULT_CHORDS))] + \
             ['NotePosition_'+str(i) for i in range(96)]+ \
                 ['NotePitch_'+str(i) for i in range(128)] + \
                     ['NoteDuration_'+str(i) for i in range(96)] + \
                        ['NoteInstFamily_'+str(i) for i in range(17)] + \
                            ['NoteVelocity_'+str(i)for i in range(len(DEFAULT_VEL_BINS))]
#                         ['NoteProgram_'+str(i) for i in range(256)] + \

"""
compund word:
    type :  0 = bar
            1 = note
            2 = eos
    
    tempo : 1~64   (index of default bpm bins)
    chord : 1~132  (index of default chords)

    note position : 1~48
    note pitch: 1~128
    note duration: 1~48  (+1)
    note instrument family: 1~17  (17 is drum)
    note velocity : 1~30  (index of default vel bins)

    **all attributes accept 0 as ignore**
"""


class REMIEvent:
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __repr__(self):
        res = 'type=' + self.type
        if self.value:
            res += ', value=' + str(self.value)
        return "REMIEvent({})".format(res)

    def to_token(self):
        return self.type+'_'+str(self.value) if self.value is not None else self.type

class Note:
    def __init__(self, position, pitch, duration, inst_family, velocity):
        self.position = position
        self.pitch = pitch
        self.duration = min(duration, 4*SCALE)
        self.inst_family = inst_family
        self.velocity = velocity

    def __repr__(self):
        return "NoteEvent(position={}, pitch={}, duration={}, inst_family={}, velocity={})".format(self.position, self.pitch, self.duration, self.inst_family, self.velocity) 

    def to_remi(self):
        return [
            REMIEvent('NotePosition', self.position),
            REMIEvent('NotePitch', self.pitch),
            REMIEvent('NoteDuration', self.duration-1),
            REMIEvent('NoteInstFamily', self.inst_family),
            REMIEvent('NoteVelocity', self.velocity)
        ]

    def to_cp(self):
        return [1, 0, 0, self.position+1, self.pitch+1, self.duration, self.inst_family+1,
                np.where(DEFAULT_VEL_BINS == self.velocity)[0][0]+1]
    
    def to_midi(self, bar_offset, tpb):
        step = tpb // SCALE
        offset = bar_offset*48
        return ct.Note(velocity=self.velocity, 
                       pitch=self.pitch, 
                       start=(self.position + offset)*step, 
                       end=(self.position + self.duration + offset)*step)


class Bar:
    def __init__(self, tempo=None, chord=None):
        self.tempo = tempo
        self.chord = chord

    def __repr__(self):
        res = []
        if self.tempo:
            res += ['tempo='+str(self.tempo)]
        if self.chord:
            res += ['chord='+self.chord]
        return "BarEvent({})".format(','.join(res))

    def to_remi(self):
        res = [REMIEvent('Bar', None)]
        if self.tempo:
            res += [REMIEvent('Tempo', np.where(DEFAULT_BPM_BINS == self.tempo)[0][0])]
        if self.chord:
            res += [REMIEvent('Chord', DEFAULT_CHORDS.index(self.chord))]
        return res

    def to_cp(self):
        return [0, 
                np.where(DEFAULT_BPM_BINS == self.tempo)[0][0]+1 if self.tempo else 0, 
                DEFAULT_CHORDS.index(self.chord)+1 if self.chord else 0, 0, 0, 0, 0, 0]

class EventSeq:
    def __init__(self, events=[]):
        self.events = events

    def __len__(self):
        return len(self.events)

    def __getitem__(self, index):
        return self.events[index]

    def find_time_index(self, beats):
        time = beats * SCALE
        for i, e in enumerate(self.events):
            if time < e.time:
                return i - 1

    def slice_by_index(self, start, end):
        return EventSeq(self.events[start:end])

    def slice_by_time(self, start, end):
        start = self.find_time_index(start)
        end = self.find_time_index(end)
        return EventSeq(self.events[start:end])

    def get_num_bars(self):
        return len(list(filter(lambda x: isinstance(x, Bar), self.events)))

    @staticmethod
    def from_midi(midi):
        end = midi.max_tick
        tick_resol = midi.ticks_per_beat
        bar_resol = tick_resol * 4
        step = tick_resol // SCALE
        n_bar_steps = SCALE * 4

        events = defaultdict(list)
        for inst in midi.instruments:
            inst_family = 16 if inst.is_drum else inst.program // 8
            for note in inst.notes:
                bar_idx = note.start // bar_resol
                if note.start % step != 0:
                    raise Exception("this file is not quantized")

                events[bar_idx] += [
                    Note(position=(note.start - bar_idx*bar_resol) // step, 
                         pitch=note.pitch, 
                         duration=(note.end - note.start) // step, 
                         inst_family=inst_family, 
                         velocity=DEFAULT_VEL_BINS[np.argmin(np.abs(DEFAULT_VEL_BINS - int(note.velocity)))])
                ]

        for tempo in midi.tempo_changes:
            tempo.tempo = DEFAULT_BPM_BINS[np.argmin(np.abs(DEFAULT_BPM_BINS - int(tempo.tempo)))]
            events[tempo.time // bar_resol] += [tempo]
        
        for marker in midi.markers:
            if marker.text.startswith('Chord'):
                marker.text = marker.text[6:]
                events[marker.time // bar_resol] += [marker]

        res = []
        for bar_idx in sorted(events.keys()):
            bar = Bar()
            notes = []
            if bar_idx in events:
                for e in events[bar_idx]:
                    if isinstance(e, Note):
                        notes += [e]
                    if isinstance(e, ct.Marker):
                        bar.chord = e.text
                    if isinstance(e, ct.TempoChange):
                        bar.tempo = e.tempo
            res += [bar] + sorted(notes, key=lambda x: x.position)
        return EventSeq(res)

    @staticmethod
    def from_cp(cp):
        events = []
        for c in cp:
            if c[0] == 0:
                events += [Bar(DEFAULT_BPM_BINS[c[1]-1] if c[1] != 0 else None, DEFAULT_CHORDS[c[2]-1] if c[2] != 0 else None)]
            elif c[0] == 1:
                events += [Note(max(c[3]-1, 0), max(c[4]-1, 0), c[5], max(c[6]-1, 0), DEFAULT_VEL_BINS[c[7]-1])]
        return EventSeq(events)


    @staticmethod
    def from_string(text):
        tokens = text.split()
        n = len(tokens)
        i = 0
        events = []
        while i < n:
            if tokens[i] == 'Bar':
                events += [Bar()]
            elif tokens[i].startswith('Tempo'):
                events[-1].tempo = DEFAULT_BPM_BINS[int(tokens[i].split('_')[1])]
            elif tokens[i].startswith('Chord'):
                events[-1].chord = DEFAULT_CHORDS[int(tokens[i].split('_')[1])]
            elif tokens[i].startswith('NotePosition'):
                events += [
                    Note(position=int(tokens[i].split('_')[1]),
                         pitch=int(tokens[i+1].split('_')[1]),
                         duration=int(tokens[i+2].split('_')[1])+1,
                         program=int(tokens[i+3].split('_')[1]),
                         velocity=int(tokens[i+4].split('_')[1])
                    )
                ]
                i += 4
            i += 1
        return EventSeq(events)

    def to_remi(self, indices=False):
        res = []
        for e in self.events:
            res += [r.to_token() for r in e.to_remi()]
        res += ['EOS']
        if indices:
            return [ALL_TOKENS.index(tok) for tok in res]
        return res

    def to_cp(self):
        res = []
        for e in self.events:
            res += [e.to_cp()]
        res += [[2]+[0]*7]
        return np.array(res)

    def to_midi(self, output_path=None):
        midi = parser.MidiFile()

        midi.ticks_per_beat = DEFAULT_TICK_RESOL
        tempos = []
        chords = []
        instr_notes = defaultdict(list)

        time = 0
        for e in self.events:
            if isinstance(e, Bar):
                if e.tempo:
                    tempos += [ct.TempoChange(e.tempo, time)]
                if e.chord:
                    chords += [ct.Marker(e.chord, time)]
                time += DEFAULT_BAR_RESOL
            if isinstance(e, Note):
                s = DEFAULT_STEP*e.position + time
                instr_notes[e.inst_family] += [ct.Note(e.velocity, e.pitch, s, s + e.duration*DEFAULT_STEP)]
        tempos.sort(key=lambda x: x.time)
        chords.sort(key=lambda x: x.time)
        
        instruments = []
        for k, v in instr_notes.items():
            inst = ct.Instrument(k * 8 if k < 16 else 0, k == 16)
            inst.notes = sorted(v, key=lambda x: x.start)
            instruments += [inst]

        midi.instruments = instruments
        midi.tempo_changes = tempos
        midi.key_signature_changes = []
        midi.time_signature_changes = []
        if output_path:
            midi.dump(output_path)
        return midi

        