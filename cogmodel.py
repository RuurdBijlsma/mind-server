from actrmodel import ACTRModel
from chunkCog import Chunk


# The cognitive part of the game's model

class CognitiveModel(ACTRModel):
    def __init__(self, sio):
    	super.__init__(self)
    	_init_memory(self)

	# Initialise declarative memory with gap facts and pulse durations        
    def _init_memory(self):
    	_add_gap_facts(self)

	# Generate chunks for the gap facts and add them to memory    	
    def _add_gap_facts(self):
    	for n1 in range(0, 10):
    		for n2 in range(0, 10):
    			gap_fact = Chunk(name = "gf-" + n1 + n2, slots = {"type": "gap-fact",
    				"num1":n1, "num2": n2, "gap":abs(n1-n2)})
    			self.add_encounter(gap_fact)