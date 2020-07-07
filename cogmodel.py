from actrmodel import ACTRModel
from chunkCog import Chunk
import temporal
import time as tm
import pandas as pd
import numpy as np


# The cognitive part of the game's model

class CognitiveModel(ACTRModel):
    def __init__(self):
        super().__init__()
        self.rt = -2.0
        # initialise memory
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
                gap_fact = Chunk(name=chunk_name, slots={"type": "gap-fact",
                                                         "num1": n1, "num2": n2, "gap": (n1 - n2)}, blc=10)
                self.add_encounter(gap_fact)

    # Generate chunks forthe wait facts and add them to memory
    def _add_wait_facts(self):
        # Get initial times to wait from timing_data csv
        data = pd.read_csv('data/init_memory.csv', usecols=['Gap', 'Pulses'])
        array = data.to_numpy()  # data is type numpy.int64 (compatible with int)
        for gap, time in array:
            self.add_wait_fact(gap, time)

    # Takes gap and time in pulse as arguments then creates a new wait fact in memory
    def add_wait_fact(self, gap, time, in_csv=True):
        if gap is not None and time is not None:
            chunk_name = "g" + str(gap) + "-w" + str(time)
            wait_fact = Chunk(name=chunk_name, slots={"type": "wait-fact",
                                                      "gap": gap, "wait": time}, blc=5)
            # fact is not in csv yet
            if not in_csv:
                # is fact new (i.e. not already in memory?)
                if chunk_name not in [chunk.name for chunk in self.dm]:
                    # add new fact to csv
                    self._add_to_csv(gap, time)
            # add new fact to memory (or add encounter to already existing memory)
            self.add_encounter(wait_fact)

    def _add_to_csv(self, gap, pulses):
        seconds = temporal.pulses_to_time(pulses)
        # intialise new row for csv
        row = [gap, seconds, pulses]
        # Create DataFrame of new row
        df = pd.DataFrame(row).transpose()
        df.columns = ['Gap', 'Time (s)', "Pulses"]
        # add new df to csv
        with open('data/learned_memory.csv', 'a') as f:
            df.to_csv(f, mode='a', header=f.tell() == 0, index=False)

    def _add_goal(self):
        goal_0 = Chunk(name="goal", slots={"type": "game-state", "hand": None, "pile": 0,
                                           "gap": None, "wait": None, "success": None})
        tm.sleep(0.05)
        self.goal = goal_0
        # setting a goal takes 50 ms
        self.time += 0.05

    def set_pile(self, top_card):
        # goal should always exist, but check to avoid errors
        if self.goal is not None:
            tm.sleep(0.05)
            self.goal.slots["pile"] = top_card
            self.time += 0.05
        else:
            raise ValueError("Goal does not exist thus cannot be adjusted.")

    def set_hand(self, lowest_card):
        # goal should always exist, but check to avoid errors
        if self.goal is not None:
            tm.sleep(0.05)
            self.goal.slots["hand"] = lowest_card
            self.time += 0.05
        else:
            raise ValueError("Goal does not exist thus cannot be adjusted.")

    # generates time for the model to perform a movement + randomness
    # t can be generated with Fitt's Law by is set as 0.1 as mimimum-time, n = 3 by default
    def get_movement_time(self, t=0.1, n=3):
        low = t * ((n - 1) / n)
        high = t * ((n + 1) / n)
        # time the actual movement takes
        mt = np.random.uniform(low, high)
        # time for initiation, preperation, and execution of movement
        mt += 0.15
        self.time += mt
        return mt

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
            return wait_fact.slots["wait"]
        return None

    def sep_number(self, n):
        tens = int(n / 10)
        ones = n % 10
        return tens, ones

    def determine_gap(self, hand, pile):
        if (hand == 100):
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

        if self.imaginal.slots["gap-tens"] is None and (hand > 10 or pile > 10):
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

    def reset_goal(self, partial=False):
        print("model goal reset")
        # If goal has already been created, reset its slots
        if self.goal is not None:
            tm.sleep(0.05)
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

    def reset_imaginal(self):
        if self.imaginal is not None:
            self.imaginal = None
