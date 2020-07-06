from timer import Timer
import time as tm
from cogmodel import CognitiveModel
from chunkCog import Chunk
from success import Success
import temporal


# None of this is final, the actual cognitive model needs to also be updated in all these functions


class Model(CognitiveModel):
    def __init__(self, sio=None):
        super().__init__()
        self.shurikens_left = -1
        self.lives_left = -1
        self.hand = []
        self.player_hand_size = -1
        self.deck_top_card = -1
        self.reset_game()
        if sio is not None:
            self.sio = sio
        # Temp
        self.timer = None
        self.wait_time = None

    def get_top_card(self):
        print("get_top_card", self.deck_top_card)
        return self.deck_top_card

    def update_top_card(self, new_top_card):
        print("update_top_card", new_top_card)
        current_top_card = self.get_top_card()
        if new_top_card > current_top_card:
            self.deck_top_card = new_top_card
        else:
            print("New card is lower can previous top card, retaining previous top card, but still deliberating", current_top_card)
        # model "sees" change in game-state
        self.set_pile(new_top_card)
        # Played played a card, wait for some seconds to maybe play model card?
        # self.temp_play_card_smart()
        self.deliberate()

    def deliberate(self):
        print("Start model deliberate")
        # Cancel current action because game-state changed
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

        # determine what step model should take next
        if self.goal is not None:
            # copy variables for easier use
            hand = self.goal.slots["hand"]
            pile = self.goal.slots["pile"]
            gap = self.goal.slots["gap"]
            wait = self.goal.slots["wait"]
            success = self.goal.slots["success"]

            # add time for production to fire
            self.time += 0.05

            # process last play if it exists
            # if success is not None:
            #     print(f"Processing feedback from success {success}")
            #     self.process_feedback()
            #     self.reset_goal(partial = True)
            #     # self.deliberate()
            #     return

            # hand is empty (and latest feedback has been processed)
            if len(self.hand) == 0:
                print("our hand is empty, no actions left to do")
                return

            # refrain from doing anything with a 100 card if player still has cards
            if hand == 100 and self.get_player_hand_size() != 0:
                print("Waiting indefinitely, model card = 100")
                return

            # Model knows its hand and the deck top card, but does not yet know the gap
            if hand is not None and gap is None:
                new_gap = self.determine_gap(hand, pile)
                self.goal.slots["gap"] = new_gap
                print(f"calculating difference between {hand} and {pile}...", "calculated gap is", new_gap)
                # add time for modifying goal buffer
                self.time += 0.05
                self.reset_imaginal()
                self.deliberate()
                return

            # Model knows the gap but does not know how long to wait
            if gap is not None and wait is None:
                print(f"deciding how long to wait with a gap of {gap}")
                pulses = self.get_wait_time(gap)
                self.goal.slots["wait"] = pulses
                # add time for modifying goal buffer
                self.time += 0.05
                self.deliberate()
                return

            # Model knows how long to wait and hasn't started waiting yet
            if wait is not None and success is None:
                seconds = temporal.pulses_to_time(wait)
                lowest_card = self.get_lowest_card()
                print(f"Waiting {seconds} seconds before playing {lowest_card}")
                # time it takes for the model to perform a movement
                mt = self.get_movement_time()
                self.timer = Timer((seconds + mt), self.play_lowest_card)
                # set wait time as starting time (minus movement time)
                self.wait_time = tm.time() - mt

        else:
            print("Model has lost track of the game state...")

    def temp_play_card_smart(self):
        print("temp_play_card_smart")
        # TEMPORARY (This just waits n seconds where n is the gap before playing lowest card)
        if self.timer is not None:
            self.timer.cancel()
        if len(self.hand) == 0:
            print("our hand is empty, no actions left to do")
            return
        lowest_card = self.get_lowest_card()
        gap = lowest_card - self.get_top_card()
        print(f"Waiting {gap} seconds before playing {lowest_card}")
        self.timer = Timer(gap, self.play_lowest_card)

    def get_lowest_card(self):
        if len(self.hand) == 1:
            return self.hand[0]
        if len(self.hand) == 0:
            return False
        return min(*self.hand)

    async def play_lowest_card(self):
        lowest_card = self.get_lowest_card()
        await self.play_card(lowest_card)

    async def play_card(self, card):
        print("play_card", card)
        self.hand.remove(card)
        # model "sees" change in game-state
        self.set_hand(self.get_lowest_card())
        await self.sio.emit('play_card', card)
        # self.time += timer.timeout
        self.update_top_card(card)

    # noinspection PyMethodMayBeStatic
    def get_shuriken_response(self):
        print("get_shuriken_response")
        return True

    # noinspection PyMethodMayBeStatic
    def set_player_shuriken_response(self, response, lowest_card):
        print("set_player_shuriken_response")
        pass

    def life_lost(self, caused_by_human):
        # If it's caused by a human the model played a card too early
        # Else it played a card too late
        print("life_lost")
        # wait time becomes current time minus old wait_time
        self.wait_time = tm.time() - self.wait_time
        print(f"I'd been waiting for {self.wait_time} seconds when I lost a life.")
        self.lives_left -= 1
        self.update_state()
        if self.goal is not None:
            if caused_by_human:
                # model played a card too early
                self.goal.slots["success"] = Success.early
            else:
                # modedl played a card too late
                self.goal.slots["success"] = Success.late
            self.time += 0.05
        self.deliberate()

    def add_life(self, amount):
        print("add life")
        self.lives_left += amount
        self.update_state()

    def add_shuriken(self, amount):
        print("add shuriken")
        self.shurikens_left += amount
        self.update_state()

    def update_state(self):
        print('[Updating model state]')
        lives = self.lives_left
        shuriken = self.shurikens_left
        game_state_new = Chunk(name="stats" + str(lives) + str(shuriken),
                               slots={"type": "game-state", "lives": lives, "shuriken": shuriken})
        self.add_encounter(game_state_new)
        self.time += 0.05

    # function to process whether a card play was successful or not
    def process_feedback(self):
        if self.goal is not None:
            if self.goal.slots["success"] is not None:
                success = self.goal.slots["success"]
                gap = self.goal.slots["gap"]
                time = self.goal.slots["wait"]
                print(f"Proccessing feedback for waiting {time} pulses for gap {gap}...")
                # model played a card too early
                if success == Success.early:
                    # set new time as 10% later than that the model played (and a life was lost)
                    new_time = self.wait_time + (self.wait_time * 0.1)
                    new_time = temporal.time_to_pulses(new_time)
                    self.add_wait_fact(gap, new_time, in_csv=False)
                    print(f"I should have waited longer; I will try waiting {new_time} for gap {gap}.")
                # model played a card too late
                if success == Success.late:
                    # set new time as 10% earlier than that the player played (and a life was lost)
                    new_time = self.wait_time - (self.wait_time * 0.1)
                    new_time = temporal.time_to_pulses(new_time)
                    self.add_wait_fact(gap, new_time, in_csv=False)
                    print(f"I should have played sooner; I will try waiting {new_time} for gap {gap}.")
                # model played a card just right
                if success == Success.success:
                    # add new encounter of the successful wait fact
                    self.add_wait_fact(gap, time)
                    print(f"Waiting {time} worked out; I will wait that long again next time I see gap {gap}.")

    def get_player_hand_size(self):
        print("get_player_hand_size", self.player_hand_size)
        return self.player_hand_size

    def update_player_hand_size(self, new_hand_size):
        print("update_player_hand_size", new_hand_size)
        self.player_hand_size = new_hand_size

    def update_model_hand(self, new_hand):
        print("update_model_hand", new_hand)
        self.hand = new_hand
        # model "sees" change in game-state
        self.set_hand(self.get_lowest_card())
        # Lowest card probably changed, to rethink our decisions
        # self.temp_play_card_smart()
        self.deliberate()

    def new_game(self):
        print("new_game")
        self.reset_game()
        self.update_state()

    def new_round(self, new_hand):
        print("new_round")
        self.reset_timer()
        self.reset_round()
        self.update_model_hand(new_hand)
        self.update_player_hand_size(len(new_hand))

    def reset_timer(self):
        print("reset_timer")
        pass

    def reset_game(self):
        print("reset_game")
        self.shurikens_left = 1
        self.lives_left = 2
        self.reset_round()

    def reset_round(self):
        print("reset_round")
        self.deck_top_card = 0
        self.player_hand_size = 0
        self.hand = []
        self.reset_goal()
