import requests
import socketio
import eventlet
from aiohttp import web
from model import Model

# create a Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*', logger=False)
app = web.Application()
sio.attach(app)
# app = socketio.WSGIApp(sio)
model = Model(sio)


@sio.event
def cards_played(sid, numbers):
    print(f"Player played card(s) {numbers}")
    model.update_player_hand_size(model.get_player_hand_size() - len(numbers))
    # player can play more than one card when shuriken is played for example, or when they have consecutive cards
    # In this card only regard the top card
    # Tell model here (only need to update top card if the new card is higher than the current top card)
    last_number_played = numbers[len(numbers) - 1]
    if last_number_played > model.get_top_card():
        model.update_top_card(last_number_played)


@sio.event
async def shuriken_proposed(sid):
    print(f"Player proposed shuriken")
    # Ask model for response here
    response = model.get_shuriken_response()
    await sio.emit('shuriken_vote', response)


@sio.event
def shuriken_vote(sid, vote, player_lowest_card):
    if vote == 'no':
        print(f"Player vetoed and denied our shuriken proposal: {vote}")
        model.set_player_shuriken_response(False, None)
    else:
        # Also update shuriken amount left = shurikens_left - 1 in the next function
        model.set_player_shuriken_response(True, player_lowest_card)
        print(f"Player voted yes on our shuriken proposal, their lowest card = {player_lowest_card}")


@sio.event
def life_lost(sid):
    print(f"Oh now we lost a life")
    model.life_lost()


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
    model.update_player_hand_size(len(new_hand))
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
