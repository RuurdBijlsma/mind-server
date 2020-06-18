from actrmodel import ACTRModel
from chunkCog import Chunk
import pandas as pd
import numpy as np

# The cognitive part of the game's model

class CognitiveModel(ACTRModel):
	def __init__(self):
		super().__init__()
		self.rt = -10.0	# high retrieval threshold because number knowledge is well-known and game state is readily available
		self._init_memory()

	# Initialise declarative memory with gap facts and pulse durations        
	def _init_memory(self):
		self._add_gap_facts()
		self._add_wait_facts()

	# Generate chunks for the gap facts and add them to memory    	
	def _add_gap_facts(self):
		for n1 in range(0, 10):
			for n2 in range(0, 10):
				chunk_name = "gf-" + str(n1) + str(n2)
				gap_fact = Chunk(name = chunk_name, slots = {"type": "gap-fact",
					"num1":n1, "num2": n2, "gap":abs(n1-n2)})
				self.add_encounter(gap_fact)

	# Generate chunks forthe wait facts and add them to memory
	def _add_wait_facts(self):
		# Get initial times to wait from timing_data csv
		data = pd.read_csv("timing_data.csv", usecols=['Gap','Pulses'])
		array = data.to_numpy() # data is type numpy.int64 (compatible with int)
		for gap, time in array:
			chunk_name = "g" + str(gap) + "-w" + str(time)
			wait_fact = Chunk(name = chunk_name, slots = {"type": "wait-fact",
				"gap": gap, "wait": time})
			self.add_encounter(wait_fact)
