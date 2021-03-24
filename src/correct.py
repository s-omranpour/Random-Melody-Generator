from miditoolkit.midi.containers import Note
from miditoolkit.midi.parser import MidiFile
from copy import deepcopy
import numpy as np
from src.events import EventSeq, Bar, Note

class Corrector:
    def __init__(self):
        self.major_scale = [1,0,1,0,1,1,0,1,0,1,0,1]
        self.minor_scale = [1,0,1,1,0,1,0,1,1,0,1,0]
        self.dominant_scale = [1,0,1,0,1,1,0,1,0,1,1,0]
        self.diminished_scale = [1,0,1,1,0,1,1,0,1,1,0,1]
        self.half_diminished_scale = [1,0,1,1,0,1,1,0,1,0,1,0]
        self.augmented_scale = [1,0,0,1,1,0,0,1,1,0,0,1]
        self.scale_map = {
            'M' : self.major_scale,
            'M7' : self.major_scale,
            'sus2' : self.major_scale,
            'sus4' : self.major_scale,
            'm' : self.minor_scale,
            'm7': self.minor_scale,
            'o' : self.diminished_scale,
            'o7': self.diminished_scale,
            '/o7': self.half_diminished_scale,
            '+' : self.augmented_scale,
            '7' : self.dominant_scale
        }
        self.pitch_map = {
            'C' : 0,
            'C#' : 1,
            'D' : 2,
            'D#' : 3,
            'E' : 4,
            'F' : 5,
            'F#' : 6,
            'G' : 7,
            'G#' : 8,
            'A' : 9,
            'A#' : 10,
            'B' : 11
        }

    def make_whole_scale(self, chord):
        root, type = chord.split('_')
        root = self.pitch_map[root]
        scale = self.scale_map[type]
        mask = scale[:root] + scale*11
        mask = np.array(mask[:128])
        return np.where(mask > 0)[0]
    
    def correct_pitches(self, notes, chord):
        assert chord is not None
        scale = self.make_whole_scale(chord)
        res = []
        for n in notes:
            note = deepcopy(n)
            note.pitch = scale[np.argmin(np.abs(note.pitch - scale))]
            res += [note]
        return res


    def correct_seq(self, seq, chords=None):
        def get_bars_chords(seq):
            events = seq.events
            bars = []
            chords = []
            prev_chord = None
            for e in seq.events:
                if isinstance(e, Bar):
                    bars += [[]]
                    chords += [e.chord if e.chord else prev_chord]
                    prev_chord = chords[-1]
                else:
                    bars[-1] += [e]
            return bars, chords

        bars, chords_t = get_bars_chords(seq)
        if chords is None:
            chords = chords_t
        
        events = []
        for bar, chord in zip(bars, chords):
            events += [Bar(chord=chord)]
            bar = self.correct_pitches(bar, chord)
            events += bar
        return EventSeq(events)


        





