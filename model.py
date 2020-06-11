from timer import Timer
from actrmodel import ACTRModel


# None of this is final, the actual cognitive model needs to also be updated in all these functions


class Model(ACTRModel):
    def __init__(self, sio):
    	super.__init__(self)
        self.shurikens_left = -1
        self.lives_left = -1
        self.hand = []
        self.player_hand_size = -1
        self.deck_top_card = -1
        self.reset_game()
        self.sio = sio

        # Temp
        self.timer = None

    def get_top_card(self):
        print("get_top_card", self.deck_top_card)
        return self.deck_top_card

    def update_top_card(self, new_top_card):
        print("update_top_card", new_top_card)
        self.deck_top_card = new_top_card
        # Played played a card, wait for some seconds to maybe play model card?
        self.temp_play_card_smart()

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
        print("get_lowest_card")
        if len(self.hand) == 1:
            return self.hand[0]
        if len(self.hand) == 0:
            return False
        return min(*self.hand)

    async def play_lowest_card(self):
        print("play_lowest_card")
        lowest_card = self.get_lowest_card()
        await self.play_card(lowest_card)

    async def play_card(self, card):
        print("play_card", card)
        self.hand.remove(card)
        await self.sio.emit('play_card', card)
        self.update_top_card(card)

    # noinspection PyMethodMayBeStatic
    def get_shuriken_response(self):
        print("get_shuriken_response")
        return True

    # noinspection PyMethodMayBeStatic
    def set_player_shuriken_response(self, response, lowest_card):
        print("set_player_shuriken_response")
        pass

    def life_lost(self):
        print("life_lost")
        self.lives_left -= 1

    def get_player_hand_size(self):
        print("get_player_hand_size")
        return self.player_hand_size

    def update_player_hand_size(self, new_hand_size):
        print("update_player_hand_size")
        self.player_hand_size = new_hand_size

    def update_model_hand(self, new_hand):
        print("update_model_hand", new_hand)
        self.hand = new_hand
        # Lowest card probably changed, to rethink our decisions
        self.temp_play_card_smart()

    def new_game(self):
        print("new_game")
        self.reset_game()

    def new_round(self, new_hand):
        print("new_round")
        self.reset_timer()
        self.reset_round()
        self.update_model_hand(new_hand)

    def reset_timer(self):
        print("reset_timer")
        pass

    def reset_game(self):
        print("reset_game")
        self.shurikens_left = 3
        self.lives_left = 3
        self.reset_round()

    def reset_round(self):
        print("reset_round")
        self.deck_top_card = 0
        self.player_hand_size = 0
        self.hand = []
