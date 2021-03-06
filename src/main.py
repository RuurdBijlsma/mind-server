import socketio
from aiohttp import web
from model import Model
from enums import Actor

# create a Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*', logger=False)
app = web.Application()
sio.attach(app)
# app = socketio.WSGIApp(sio)
model = Model(sio)


@sio.event
def card_played(sid, number):
    print(f"Player played card(s) {number}.")
    model.update_player_hand_size(model.get_player_hand_size() - 1)
    # player can play more than one card when shuriken is played for example, or when they have consecutive cards
    # In this card only regard the top card
    # Tell model here (only need to update top card if the new card is higher than the current top card)
    model.update_top_card(number, Actor.player)


@sio.event
def update_top_card(sid, number):
    model.update_top_card(number, Actor.model)


@sio.event
async def shuriken_proposed(sid):
    print(f"Player proposed shuriken.")
    model.pause_timer(model.timer)
    model.reset_timers()
    # Ask model for response here
    response = model.get_shuriken_response()
    # if model accepts, lower amount of shurikens_left in model
    if response:
        model.shurikens_left -= 1
        print("I accept the player's shuriken proposal.")
        model.pause = None
    else:
        print("I reject the player's shuriken proposal.")
        model.deliberate()
    await sio.emit('shuriken_vote', 'true' if response else 'false')


@sio.event
def shuriken_vote(sid, vote):
    if vote == 'no':
        print(f"Player vetoed and denied my shuriken proposal: {vote}.")
        model.set_player_shuriken_response(False)
    else:
        model.set_player_shuriken_response(True)
        print(f"Player voted yes on my shuriken proposal.")


@sio.event
def end_round(sid, round):
    model.end_round(round)


@sio.event
def discard_card(sid):
    print(f"player discarded a card!")
    model.update_player_hand_size(model.get_player_hand_size() - 1)
    model.discard_player_card()


@sio.event
def reveal_lowest_card(sid, card):
    model.reveal_player_lowest_card(card)


@sio.event
def get_life(sid, amount):
    print("Bonus life!", amount)
    model.add_life(amount)


@sio.event
def get_shuriken(sid, amount):
    print("Bonus shuriken!", amount)
    model.add_shuriken(amount)


@sio.event
def update_model_hand(sid, new_hand):
    print(f"Update model hand! Model's hand contains the cards: {new_hand}")
    # This function is needed because the model hand can change (for example shuriken is played, 
    # player shows lowest card, which is higher than cards in models hand.
    # Then all cards in the models hand which are lower than the players lowest card are removed)
    # It's also called at the start of each round
    model.update_model_hand(new_hand)


@sio.event  # Not sure this event is needed yet
def update_player_hand_size(sid, player_hand_size):
    print(f"Update player hand size: {player_hand_size}")
    model.update_player_hand_size(player_hand_size)


@sio.event
def new_round(sid, new_hand):
    print(f"New round: {len(new_hand)} reset model time and update hand to {new_hand}")
    # Reset timer in new_round
    model.new_round(new_hand)


@sio.event
def new_game(sid):
    print(f"New Game! reset everything")
    # reset life count, etc.
    model.new_game()


@sio.event
def connect(sid, environ):
    print('connect sid:', sid)


@sio.event
def disconnect(sid):
    print('disconnect sid:', sid)


if __name__ == '__main__':
    web.run_app(app, port=5000)
