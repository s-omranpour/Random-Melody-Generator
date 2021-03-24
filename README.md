# Random-Melody-Generator

This is a simple project to generate random melody with respect to a chord progression.


### Classes
1. Generator  :    Generates random notes (random in the sense of pitch and timing)

2. Corrector  :    Corrects the pitches with respect to a given chord progression. Basically it changes each pitch to the nearest pitch existing in the given scale (if it isn't in the scale already).

3. EventSeq   :    A unified class for the event-based music representation which can be converted to MIDI, REMI, and Compound Word representation. There are two types of events in this representation:

 - Bar which represents begining of a new bar and has tempo and chord attributes.
 - Note which represents midi note with position, duration, pitch, instrument family, and velocity attributes.
 
 
 ### Audio output
 Fluidsynth is used to convert midi to wav file. Required soundfonts are provided too.
 
 
 ### Todos
 1. support more time signatures (currently only 4/4 is supported)
 2. support rhythmic patterns
 3. support rule-based generation (for pitch and timing)
 4. add chord progression generator
 5. packaging
