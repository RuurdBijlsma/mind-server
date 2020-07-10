from timer import Timer
import time as tm
import numpy as np
from cogmodel import CognitiveModel
from enums import Success, Actor
import temporal


# Written by: I.D.M. Akrum and R. Bijlsma
# Source code: https://github.com/RuurdBijlsma/mind-server


class Model(CognitiveModel):
    def __init__(self, sio=None):
        super().__init__()
        # game-state
        self.shurikens_left = -1
        self.lives_left = -1
        self.hand = []
        self.player_hand_size = -1
        self.deck_top_card = -1
        self.reset_game()
        if sio is not None:
            self.sio = sio
        # timers
        self.timer = None   # for playing a card
        self.check_in = None    # for checking in after some time
        self.discard_timer = None   # for discarding a card
        self.wait_time = 0  # keep track of how long the model's waited real-time
        self.pause = None   # keep track of how long the model still has to wait in a pause

    # the "main" function of the model which decides all model action
    def deliberate(self):
        self.check_goal()
        goal = self.goal

        if self.lives_left <= 0:
            raise ValueError("Unfortunately, we have no lives left.")

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

        # process feedback from last play
        if success is not None and success[0] != Success.pending:
            print(f"Processing feedback from {success}...")
            self.process_feedback(success, gap, wait)
            self.reset_goal(partial=True)
            self.deliberate()
            return

        # if player's hand is empty, model plays all its left-over cards
        if self.get_player_hand_size() == 0:
            print("Player's hand is empty.")
            # if model's hand "exists", i.e. it is not empty
            if self.hand:
                # if player isn't already in the process of playing a card
                if self.timer is None:
                    self.timer = Timer(self.get_movement_time(), self.play_lowest_card)
                return

        # if hand is empty (and latest feedback has been processed), there is nothing left to do
        if len(self.hand) == 0:
            print("our hand is empty, no actions left to do")
            return

        # refrain from doing anything with a 100 card if player still has cards
        if hand == 100 and self.get_player_hand_size() != 0:
            print("Waiting indefinitely, model card = 100")
            return

        # if you were playing a card, but paused for any reason, continue waiting
        if self.pause is not None:
            lowest_card = self.get_lowest_card()
            print(f"Still waiting {self.pause:.2f} seconds before playing {lowest_card}")
            self.timer = Timer(self.pause, self.play_lowest_card)
            self.pause = None
            return

        # if a higher card was played than in the model's hand, play those lower cards first
        if hand is not None and hand < pile:
            print("I've got cards lower than the pile... I should discard those first.")
            if self.discard_timer is None:
                self.discard_timer = Timer(self.get_movement_time(), self.discard_lowest_card)
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
            print(f"Waiting {seconds:.2f} seconds before playing {lowest_card}")
            # time it takes for the model to perform a movement
            mt = self.get_movement_time()
            timeout = seconds + mt
            # set wait time as starting time (minus movement time)
            self.wait_time = tm.time() - mt
            self.timer = Timer(timeout, self.play_lowest_card)
            if timeout > 20:
                self.check_in = Timer(20, self.check_time)
            return

        print("I don't know what to do...")

    # model plays its lowest card
    async def play_lowest_card(self):
        lowest_card = self.get_lowest_card()
        await self.play_card(lowest_card)

    # model plays a card
    async def play_card(self, card):
        print("play_card", card)
        self.hand.remove(card)
        # model "sees" change in game-state
        self.set_hand(self.get_lowest_card())
        await self.sio.emit('play_card', card)
        self.update_top_card(card, Actor.model)

    # model discards lowest card
    async def discard_lowest_card(self):
        lowest_card = self.get_lowest_card()
        await self.discard_card(lowest_card)

    # model discards a card (removed from hand but not added to pile)
    async def discard_card(self, card):
        if card not in self.hand:
            print("Cannot discard card that is not in models hand!")
            return
        self.hand.remove(card)
        self.update_model_hand(self.hand)
        await self.sio.emit('discard_card', card)
        print("Discard event sent to client")

    # function to process a change in the top card of the pile
    def update_top_card(self, new_top_card, actor):
        print("update_top_card", new_top_card)
        current_top_card = self.get_top_card()
        # only update the top card if the new card is higher
        if new_top_card > current_top_card:
            self.deck_top_card = new_top_card
            # model "sees" change in game-state
            self.set_pile(new_top_card)
            # flag that a change in top card means a change in model success
            self.set_pending(actor)
        else:
            print("New card is lower can previous top card, retaining previous top card, but still deliberating",
                  current_top_card)
            # if actor plays a lower card after model just played a card, we lose a life
            if actor == Actor.player and self.goal.slots["success"] is not None \
                    and self.goal.slots["success"][0] == Success.pending:
                self.life_lost(caused_by_human=True)
        self.reset_timer()
        self.deliberate()

    def get_top_card(self):
        print("get_top_card", self.deck_top_card)
        return self.deck_top_card

    # remember who played the last card and set success of that play to pending
    def set_pending(self, actor):
        if self.goal.slots["success"] is None:
            if actor == Actor.model and self.get_player_hand_size() > 0:
                self.goal.slots["success"] = (Success.pending, Actor.model)
                self.wait_time = tm.time() - self.wait_time
                print(f"We waited {self.wait_time:.2f} s to play the card.")
            if actor == Actor.player and self.hand:
                self.goal.slots["success"] = (Success.pending, Actor.player)
                self.wait_time = tm.time() - self.wait_time
                print(f"We were waiting {self.wait_time:.2f} s when player played a card.")
            tm.sleep(0.05)
            self.time += 0.05
        elif self.goal.slots["success"] == (Success.pending, Actor.model) \
                and self.timer is not None:
            self.timer.cancel()
            self.goal.slots["success"] = Success.success, Actor.model
            tm.sleep(0.05)
            self.time += 0.05

    # determine whether the last play was successful
    def determine_success(self, success, hand, pile):
        # if the model played last
        if success[1] == Actor.model:
            if self.timer is None:
                wait = 5 + 0.05
                print(f"Giving player {wait} seconds to object to my card.")
                self.timer = Timer(wait, self.set_success)
            else:
                return
        # if the player played last
        if success[1] == Actor.player:
            # we lose a life if we still had a lower card than the last played card in hand
            if hand is not None and hand < pile:
                self.life_lost(caused_by_human=False)
            else:
                # we only have cards higher than the last played card, but the gap has changed
                print("The situation's changed. Recalculating...")
                self.reset_goal(partial=True)

    # model decides its card was played successfully
    async def set_success(self):
        self.check_goal()
        print("My card was played successfully.")
        self.goal.slots["success"] = (Success.success, Actor.model)
        self.time += 0.05
        self.deliberate()

    # process when a life is lost
    def life_lost(self, caused_by_human):
        print("life_lost")
        self.lives_left -= 1
        self.check_goal()
        # update the model with to the correct situation
        if caused_by_human:
            # model played a card too early
            self.goal.slots["success"] = Success.early, Actor.player
        else:
            # model played a card too late
            self.goal.slots["success"] = Success.late, Actor.model
        tm.sleep(0.05)
        self.time += 0.05

    # process the feedback from the last card play
    def process_feedback(self, success, gap, time):
        self.check_goal()
        if success is None:
            raise ValueError("No feedback to process...")

        print(f"Processing feedback for waiting {time} pulses for gap {gap}...")

        # model played a card too early
        if success[0] == Success.early:
            # set new time as 15% later than the model played (and a life was lost)
            new_time = time + (time * 0.15)
            new_time = temporal.time_to_pulses(new_time)
            self.add_wait_fact(gap, new_time)
            print(f"I should have waited longer; I will try waiting {new_time} for gap {gap}.")

        # model played a card too late
        if success[0] == Success.late:
            # set new time as 15% earlier than that the player played (and a life was lost)
            new_time = self.wait_time - (self.wait_time * 0.15)
            new_time = temporal.time_to_pulses(new_time)
            self.add_wait_fact(gap, new_time)
            print(f"I should have played sooner; I will try waiting {new_time} for gap {gap}.")

        # model played a card just right
        if success[0] == Success.success:
            # add new encounter of the successful wait fact
            self.add_wait_fact(gap, time, add_to_csv=True)
            print(f"Waiting {time} worked out; I will wait that long again next time I see gap {gap}.")
        self.wait_time = 0

    async def check_time(self, long_time=15):
        if self.timer is not None:
            print("How long should I still wait?")
            temp_time = tm.time() - self.wait_time
            time_diff = self.timer.get_timeout() - temp_time
            print(f"I've waited {temp_time:.2f} s and still need to wait {time_diff:.2f} s.")
            if time_diff >= long_time:
                print("Should I propose a shuriken?")
                proposed = await self.propose_shuriken()
                if not proposed:
                    print("I'll keep waiting.")
                    self.check_in = Timer(long_time, self.check_time)
                else:
                    print("Waiting on shuriken response from player...")
            else:
                print("I'll play my card soon.")

    # propose to use a shuriken
    async def propose_shuriken(self):
        if self.timer is None or self.wait_time == 0:
            raise ValueError("We aren't waiting to play a card.")
        propose = self.get_shuriken_response()
        if propose:
            print("I'll propose a shuriken.")
            await self.sio.emit('propose_shuriken')
            self.pause_timer(self.timer)
            self.reset_timer()
            return True
        else:
            print("I won't propose a shuriken.")
            return False

    def pause_timer(self, timer):
        temp_time = tm.time() - self.wait_time
        time_diff = timer.get_timeout() - temp_time
        self.pause = time_diff

    def get_lowest_card(self):
        if len(self.hand) == 1:
            return self.hand[0]
        if len(self.hand) == 0:
            return None
        return min(*self.hand)

    # function to determine if model accepts a shuriken proposal or not
    def get_shuriken_response(self, gap_threshold=20):
        print("get_shuriken_response")
        # model's hand is 100 card (always played last)
        if self.get_lowest_card() == 100:
            print("The card in my hand is 100, so I don't want to use a shuriken.")
            return False
        self.check_goal()
        gap = self.goal.slots["gap"]
        choices = [True, False]
        p = [0.5, 0.5]  # default 50/50 chance of rejecting or accepting
        # if gap is None, the lowest card hasn't been processed properly
        if gap is None:
            return False
        # you have more than 1 lives, but only 1 shuriken
        if self.lives_left > 1 == self.shurikens_left:
            print(f"I have only 1 shuriken and {self.lives_left} lives.")
            # the gap is small
            if gap <= gap_threshold:
                print(f"The gap is {gap}, which I consider small.")
                p = [0.1, 0.9]  # high probability of rejecting
            else:
                print(f"The gap is {gap}, which I consider big.")
                p = [0.3, 0.7]  # probability biased towards rejecting
        # you have 1 (or more) shuriken, but only 1 life
        if self.lives_left == 1 <= self.shurikens_left:
            print(f"I have only 1 life and {self.shurikens_left} shuriken.")
            # the gap is large
            if gap > gap_threshold:
                print(f"The gap is {gap}, which I consider big.")
                p = [0.9, 0.1]  # high probability of accepting
            else:
                print(f"The gap is {gap}, which I consider small.")
                p = [0.7, 0.3]  # probability biased towards accepting
        print(f"The chance I'll propose or accept a shuriken is {p[0]}.")
        return np.random.choice(choices, p=p)

    # noinspection PyMethodMayBeStatic
    def set_player_shuriken_response(self, response):
        print("set_player_shuriken_response")
        pass

    # noinspection PyMethodMayBeStatic
    def reveal_player_lowest_card(self, card):
        print("Shuriken reveal player's lowest card", card)
        # Add model stuff here
        pass

    def add_life(self, amount):
        print("add life")
        self.lives_left += amount

    def add_shuriken(self, amount):
        print("add shuriken")
        self.shurikens_left += amount

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
        self.deliberate()

    def new_game(self):
        print("new_game")
        self.reset_game()

    def new_round(self, new_hand):
        print("new_round")
        self.append_learned_memory()
        self.reset_timer()
        self.reset_round()
        self.update_player_hand_size(len(new_hand))
        self.update_model_hand(new_hand)

    def reset_timer(self):
        print("reset_timer")
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
        if self.check_in is not None:
            self.check_in.cancel()
            self.check_in = None
        if self.discard_timer is not None:
            self.discard_timer.cancel()
            self.discard_timer = None
        if self.pause is not None:
            self.pause = None

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
