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
					"num1":n1, "num2": n2, "gap":(n1-n2)})
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

	def _add_goal(self):
		goal_0 = Chunk(name = "goal", slots = {"type": "game-state", "hand": None, "pile": 0,
			"gap": None, "wait": None, "success": None})
		self.goal = goal_0
		# setting a goal takes 50 ms
		self.time += 0.05

	def reset_goal(self):
		# If goal has already been created, reset its slots
		if self.goal != None:
			self.goal.slots["hand"] = None
			self.goal.slots["pile"] = 0
			self.goal.slots["gap"] = None
			self.goal.slots["wait"] = None
			self.goal.slots["success"] = None
		else:
			# if goal chunk does not yet exist, create it
			self._add_goal()

	def set_pile(self, top_card):
		# goal should always exist, but check to avoid errors
		if self.goal != None:
			self.goal.slots["pile"] = top_card
		else:
			print("ERROR: Goal does not exist thus cannot be adjusted.")

	def set_hand(self, lowest_card):
		# goal should always exist, but check to avoid errors
		if self.goal != None:
			self.goal.slots["hand"] = lowest_card
		else:
			print("ERROR: Goal does not exist thus cannot be adjusted.")
			