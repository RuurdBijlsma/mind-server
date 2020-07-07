from timer import Timer
import time as tm
from cogmodel import CognitiveModel
from chunkCog import Chunk
from enums import Success, Actor
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
        self.wait_time = 0

    def get_top_card(self):
        print("get_top_card", self.deck_top_card)
        return self.deck_top_card

    def update_top_card(self, new_top_card, actor):
        print("update_top_card", new_top_card)
        current_top_card = self.get_top_card()
        if new_top_card > current_top_card:
            self.deck_top_card = new_top_card
            # model "sees" change in game-state
            self.set_pile(new_top_card)
            self.set_pending(actor)
        else:
            print("New card is lower can previous top card, retaining previous top card, but still deliberating",
                  current_top_card)
            if actor == Actor.player and self.goal.slots["success"] is not None \
                    and self.goal.slots["success"][0] == Success.pending:
                self.goal.slots["success"] = (Success.early, Actor.player)
            tm.sleep(0.05)
            self.time += 0.05
        # Played played a card, wait for some seconds to maybe play model card?
        # self.temp_play_card_smart()
        # temporarily always reset after 
        if self.wait_time > 0:
            self.wait_time = tm.time() - self.wait_time
        self.reset_timer()
        # self.reset_goal(partial = True)
        self.deliberate()

    def set_pending(self, actor):
        if self.goal.slots["success"] is None:
            if actor == Actor.model and self.get_player_hand_size() > 0:
                self.goal.slots["success"] = (Success.pending, Actor.model)
            if actor == Actor.player and self.hand:
                self.goal.slots["success"] = (Success.pending, Actor.player)
            tm.sleep(0.05)
            self.time += 0.05

    def determine_success(self, success, hand, pile):
        if success[1] == Actor.model:
            if self.timer is None:
                wait = 5 + 0.05
                print(f"Giving player {wait} seconds to object to my card.")
                self.timer = Timer(wait, self.set_success)
            else:
                return
        if success[1] == Actor.player:
            if hand < pile:
                self.goal.slots["success"] = Success.late, Actor.model
            else:
                print("The situation's changed. Recalculating...")
                self.reset_goal(partial=True)

    async def set_success(self):
        if self.goal is None:
            raise ValueError("Model has lost track of the game state...")
            return
        print("My card was played succesfully.")
        self.goal.slots["success"] = (Success.success, Actor.model)
        self.time += 0.05
        self.deliberate()

    async def propose_shuriken(self):
        await self.sio.emit('propose_shuriken')

    def deliberate(self):
        # self.propose_shuriken()

        goal = self.goal

        if goal is None:
            raise ValueError("Model has lost track of the game state...")
            return

        if self.lives_left <= 0:
            print("We are dead.")
            return

        print(f"Start model deliberate with goal:\n {goal}")

        # add time for production to fire
        tm.sleep(0.05)
        self.time += 0.05

        # copy variables for easier use
        hand = goal.slots["hand"]
        pile = goal.slots["pile"]
        gap = goal.slots["gap"]
        wait = goal.slots["wait"]
        success = goal.slots["success"]

        # process last play 
        if success is not None and success[0] == Success.pending:
            print("Evaluating last card played...")
            self.determine_success(success, hand, pile)
            if self.timer is None:
                self.deliberate()
            return

        # process feedback 
        if success is not None and success[0] != Success.pending:
            print(f"Processing feedback from {success}...")
            self.process_feedback(success, gap, wait)
            self.reset_goal(partial=True)
            self.deliberate()
            return

        # possibly, handle playing all cards when player's hand is empty here:
        if self.get_player_hand_size() == 0:
            print("Player's hand is empty.")
            if self.hand:
                if self.timer is None:
                    self.timer = Timer(self.get_movement_time(), self.play_lowest_card)
                return

        # hand is empty (and latest feedback has been processed)
        if len(self.hand) == 0:
            print("our hand is empty, no actions left to do")
            return

        # refrain from doing anything with a 100 card if player still has cards
        if hand == 100 and self.get_player_hand_size() != 0:
            print("Waiting indefinitely, model card = 100")
            return

        if hand is not None and hand < pile:
            print("I've got cards lower than the pile... I should play those first.")
            if self.timer is None:
                self.timer = Timer(self.get_movement_time(), self.play_lowest_card)
            return

        # Model knows its hand and the deck top card, but does not yet know the gap
        if hand is not None and gap is None:
            new_gap = self.determine_gap(hand, pile)
            self.goal.slots["gap"] = new_gap
            print(f"calculating difference between {hand} and {pile}...", "calculated gap is", new_gap)
            # add time for modifying goal buffer
            tm.sleep(0.05)
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
            tm.sleep(0.05)
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
            return None
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
        self.update_top_card(card, Actor.model)

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
        if self.goal is not None:
            if caused_by_human:
                # model played a card too early
                self.goal.slots["success"] = Success.early
            else:
                # modedl played a card too late
                self.goal.slots["success"] = Success.late
            tm.sleep(0.05)
            self.time += 0.05
        self.deliberate()

    def add_life(self, amount):
        print("add life")
        self.lives_left += amount

    def add_shuriken(self, amount):
        print("add shuriken")
        self.shurikens_left += amount

    # function to process whether a card play was successful or not
    def process_feedback(self, success, gap, time):
        if self.goal is None:
            raise ValueError("Lost track of game-state...")
        if success is None:
            raise ValueError("No feedback to process...")

        print(f"Proccessing feedback for waiting {time} pulses for gap {gap}...")
        # model played a card too early
        if success[0] == Success.early:
            # set new time as 15% later than the model played (and a life was lost)
            new_time = time + (time * 0.15)
            new_time = temporal.time_to_pulses(new_time)
            self.add_wait_fact(gap, new_time, in_csv=False)
            print(f"I should have waited longer; I will try waiting {new_time} for gap {gap}.")

        # model played a card too late
        if success[0] == Success.late:
            # set new time as 15% earlier than that the player played (and a life was lost)
            new_time = self.wait_time - (self.wait_time * 0.15)
            new_time = temporal.time_to_pulses(new_time)
            self.add_wait_fact(gap, new_time, in_csv=False)
            print(f"I should have played sooner; I will try waiting {new_time} for gap {gap}.")

        # model played a card just right
        if success[0] == Success.success:
            # add new encounter of the successful wait fact
            self.add_wait_fact(gap, time)
            print(f"Waiting {time} worked out; I will wait that long again next time I see gap {gap}.")

    def reveal_player_lowest_card(self, card):
        print("Shuriken reveal player's lowest card", card)
        # Add model stuff here
        pass

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

    def new_round(self, new_hand):
        print("new_round")
        self.reset_timer()
        self.reset_round()
        self.update_player_hand_size(len(new_hand))
        self.update_model_hand(new_hand)

    def reset_timer(self):
        print("reset_timer")
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

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
