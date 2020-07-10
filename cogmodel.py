from actrmodel import ACTRModel
from chunkCog import Chunk
import temporal
import time as tm
import pandas as pd
import numpy as np
from os import path
import os


# The cognitive part of the game's model

class CognitiveModel(ACTRModel):
    def __init__(self):
        super().__init__()
        self.rt = -2.0
        # initialise memory
        self._init_memory()
        self.learned_memory = []
        self.mem_index = 0

    # Initialise declarative memory with gap facts and pulse durations
    def _init_memory(self):
        self._add_gap_facts()
        self._add_wait_facts()
        self.load_learned_memory()

    # add gap, pulses from the init_memory file
    def _add_wait_facts(self):
        # Get initial times to wait from timing_data csv
        data = pd.read_csv('data/init_memory.csv', usecols=['Gap', 'Pulses'])
        array = data.to_numpy()  # data is type numpy.int64 (compatible with int)
        for gap, time in array:
            self.add_wait_fact(gap, time)

    # add gap, pulses from learned_memory file
    def load_learned_memory(self):
        if not path.isfile('data/learned_memory.csv'):
            return
        data = pd.read_csv('data/learned_memory.csv', usecols=['Gap', 'Pulses'])
        array = data.to_numpy()
        self.learned_memory = [(gap, pulses) for [gap, pulses] in array]
        self.mem_index = len(self.learned_memory)
        print("loaded learned memory")
        # for gap, time in array:
        #     self.add_wait_fact(gap, time)

    # Generate chunks for the gap facts and add them to memory
    def _add_gap_facts(self):
        for n1 in range(0, 10):
            for n2 in range(0, 10):
                chunk_name = "gf-" + str(n1) + str(n2)
                gap_fact = Chunk(name=chunk_name, slots={"type": "gap-fact",
                                                         "num1": n1, "num2": n2, "gap": (n1 - n2)}, blc=10)
                self.add_encounter(gap_fact)

    # Takes gap and time in pulses as arguments then creates a new wait fact in memory
    def add_wait_fact(self, gap, time, add_to_csv=False):
        if gap is not None and time is not None:
            chunk_name = "g" + str(gap) + "-w" + str(time)
            wait_fact = Chunk(name=chunk_name, slots={"type": "wait-fact",
                                                      "gap": gap, "wait": time}, blc=5)
            # add new fact to memory (or add encounter to already existing memory)
            self.add_encounter(wait_fact)
            if add_to_csv and (gap, time) not in self.learned_memory:
                self.learned_memory.append((gap, time))

    # append the learned_memory csv
    def append_learned_memory(self):
        if len(self.learned_memory) <= self.mem_index:
            print("No new memories to add.")
            return
        print("Adding new memories to the learned memories data file.")
        # only add the memories that weren't in csv yet
        for i, new_memory in enumerate(self.learned_memory, self.mem_index):
            gap, pulses = new_memory
            seconds = temporal.pulses_to_time(pulses)
            # initialise new row for csv
            row = [gap, round(seconds, 3), int(pulses)]
            # Create DataFrame of new row
            df = pd.DataFrame(row).transpose()
            df.columns = ['Gap', 'Time (s)', "Pulses"]
            # add new df to csv
            with open('data/learned_memory.csv', 'a') as f:
                df.to_csv(f, mode='a', header=f.tell() == 0, index=False)
        added = len(self.learned_memory) - self.mem_index
        print(f"We added {added} new memories.")
        # update the memory index so that the newly-added memories will only be added once
        self.mem_index = len(self.learned_memory)

    # generates time for the model to perform a movement + randomness
    # t can be generated with Fitt's Law but is set as 0.1 as minimum-time, n = 3 by default
    def get_movement_time(self, t=0.1, n=3):
        low = t * ((n - 1) / n)
        high = t * ((n + 1) / n)
        # time the actual movement takes
        mt = np.random.uniform(low, high)
        # time for initiation, preparation, and execution of movement
        mt += 0.15
        self.time += mt
        return mt

    # model retrieves how long it has to wait with a given gap
    def get_wait_time(self, gap):
        blend_pattern = Chunk(name="blend-pattern", slots={"type": "wait-fact", "gap": gap})
        tm.sleep(0.05)
        wait_time, latency = self.retrieve_blended_trace(blend_pattern, "wait")
        tm.sleep(latency)
        # add time for retrieval request
        self.time += 0.05 + latency
        # if model has seen this gap before, return wait time
        if wait_time is not None:
            return wait_time
        # if model has not seen this gap before, return wait time of most similar gap
        else:
            partial_pattern = Chunk(name="partial-pattern", slots={"type": "wait-fact", "gap": gap})
            tm.sleep(0.05)
            wait_fact, latency = self.retrieve_partial(partial_pattern)
            tm.sleep(latency)
            # add time for second retrieval request
            self.time += 0.05 + latency
            wait_time = wait_fact.slots["wait"]
            if wait_time is None:
                raise LookupError("Model couldn't figure out how long to wait.")
            return wait_time

    # separate a number into tens and ones
    @staticmethod
    def sep_number(n):
        tens = int(n / 10)
        ones = n % 10
        return tens, ones

    # model calculates the difference between hand and pile
    def determine_gap(self, hand, pile):
        if hand == 100:
            # treat 100 as a gap of 1 (play "instantly")
            return 1

        # model hasn't started gap calculation yet
        if self.imaginal is None:
            tens_hand, ones_hand = self.sep_number(hand)
            tens_pile, ones_pile = self.sep_number(pile)
            calc_gap = Chunk(name="calc-gap",
                             slots={"ones1": ones_hand, "ones2": ones_pile, "tens1": tens_hand, "tens2": tens_pile,
                                    "gap-tens": None, "gap-ones": None, "gap-tot": None})
            tm.sleep(0.2)
            self.imaginal = calc_gap
            # imaginal request takes 200 ms
            self.time += 0.2
            self.determine_gap(hand, pile)

        if self.imaginal.slots["gap-tens"] is None and (hand >= 10 or pile >= 10):
            # time for production firing
            tm.sleep(0.05)
            self.time += 0.05
            tens_hand = self.imaginal.slots["tens1"]
            tens_pile = self.imaginal.slots["tens2"]
            # get gap fact for tens
            pattern = Chunk(name="retrieve", slots={"type": "gap-fact", "num1": tens_hand, "num2": tens_pile})
            tm.sleep(0.05)
            chunk, latency = self.retrieve(pattern)
            tm.sleep(latency)
            # add time for retrieval request and time it takes to get chunk
            self.time += 0.05 + latency
            tm.sleep(0.2)
            self.imaginal.slots["gap-tens"] = chunk.slots["gap"]
            # modifying imaginal buffer takes time
            self.time += 0.2
            self.determine_gap(hand, pile)

        if self.imaginal.slots["gap-ones"] is None:
            # time for production firing
            tm.sleep(0.05)
            self.time += 0.05
            ones_hand = self.imaginal.slots["ones1"]
            ones_pile = self.imaginal.slots["ones2"]
            pattern = Chunk(name="retrieve", slots={"type": "gap-fact", "num1": ones_hand, "num2": ones_pile})
            tm.sleep(0.05)
            chunk, latency = self.retrieve(pattern)
            tm.sleep(latency)
            # add time for retrieval request and time it takes to get chunk
            self.time += 0.05 + latency
            tm.sleep(0.2)
            self.imaginal.slots["gap-ones"] = chunk.slots["gap"]
            # modifying imaginal buffer takes time
            self.time += 0.2
            self.determine_gap(hand, pile)

        if self.imaginal.slots["gap-tot"] is None:
            # time for production firing
            tm.sleep(0.05)
            self.time += 0.05
            if self.imaginal.slots["gap-tens"] is not None:
                gap_tens = self.imaginal.slots["gap-tens"]
            else:
                gap_tens = 0
            gap_ones = self.imaginal.slots["gap-ones"]
            gap_tot = gap_tens * 10 + gap_ones
            tm.sleep(0.2)
            self.imaginal.slots["gap_tot"] = gap_tot
            # modifying imaginal buffer takes time
            self.time += 0.2
            return gap_tot

        return None

    # add goal to model's goal buffer
    def _add_goal(self):
        goal_0 = Chunk(name="goal", slots={"type": "game-state", "hand": None, "pile": 0,
                                           "gap": None, "wait": None, "success": None})
        tm.sleep(0.05)
        self.goal = goal_0
        # setting a goal takes 50 ms
        self.time += 0.05

    # process change in pile in goal buffer
    def set_pile(self, top_card):
        self.check_goal()
        tm.sleep(0.05)
        self.goal.slots["pile"] = top_card
        self.time += 0.05

    # process change in hand in goal buffer
    def set_hand(self, lowest_card):
        self.check_goal()
        tm.sleep(0.05)
        self.goal.slots["hand"] = lowest_card
        self.time += 0.05

    # check goal is not None
    def check_goal(self):
        if self.goal is None:
            raise ValueError("Model has lost track of the game-state.")

    # reset goal entirely or partially
    def reset_goal(self, partial=False):
        print("model goal reset")
        # If goal has already been created, reset its slots
        if self.goal is not None:
            tm.sleep(0.05)
            # also reset the hand and pile
            if not partial:
                self.goal.slots["hand"] = None
                self.goal.slots["pile"] = 0
            self.goal.slots["gap"] = None
            self.goal.slots["wait"] = None
            self.goal.slots["success"] = None
            self.time += 0.05
        else:
            # if goal chunk does not yet exist, create it
            self._add_goal()

    # reset imaginal buffer
    def reset_imaginal(self):
        if self.imaginal is not None:
            self.imaginal = None
