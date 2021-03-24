from miditoolkit.midi.parser import MidiFile
from miditoolkit.midi import containers as ct
import random

from src.events import EventSeq

class Generator:
    def __init__(self, tpb=96, tempo=120, unit=12, program=0, velocity=60):
        self.tpb = tpb
        self.tempo = tempo
        self.unit = unit
        self.time_unit = tpb // unit
        self.program = program
        self.velocity = velocity

    def __repr__(self):
        return 'Generator(tpb={}, tempo={}, unit={}, program={}, velocity={})'.format(self.tpb, self.tempo, self.unit, self.program, self.velocity)

    def _random_pitch(self, n=100, min_pitch=0, max_pitch=127):
        return [random.randint(min_pitch, max_pitch) for i in range(n)]

    def _random_time(self, n=100, min_dur=1, max_dur=48, min_gap=0, max_gap=48):
        durs = [random.randint(min_dur, max_dur) for i in range(n)]
        gaps = [random.randint(min_gap, max_gap) for i in range(n)]
        positions = [0]
        for i in range(n-1):
            positions += [positions[i] + gaps[i]]
        return durs, positions

    def generate_midi(self, n=100, chords=None,
                      min_pitch=0, max_pitch=127, 
                      min_dur=1, max_dur=48, 
                      min_gap=0, max_gap=48):

        pitchs = self._random_pitch(n, min_pitch, max_pitch)
        durs, positions = self._random_time(n, min_dur, max_dur, min_gap, max_gap)
        notes = []

        for i in range(n):
            notes += [ct.Note(velocity=self.velocity, 
                            pitch=pitchs[i], 
                            start=positions[i]*self.time_unit, 
                            end=(positions[i]+durs[i])*self.time_unit)]


        inst = ct.Instrument(self.program, is_drum=False, name='Piano')
        inst.notes = notes
        mid = MidiFile()
        mid.ticks_per_beat = self.tpb
        mid.instruments = [inst]
        mid.tempo_changes = [ct.TempoChange(self.tempo, 0)]
        return mid

    def generate_seq(self, n=100,
                     min_pitch=0, max_pitch=127, 
                     min_dur=1, max_dur=48, 
                     min_gap=0, max_gap=47):

        return EventSeq.from_midi(self.generate_midi(n, min_pitch, max_pitch, min_dur, max_dur, min_gap, max_gap))
