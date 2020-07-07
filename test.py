from model import Model
from cogmodel import CognitiveModel
import temporal
import time as tm
from enums import Actor

m = Model()
m.new_game()


# Test whether model can process new hands
def testcase_newround():
    # m = Model()
    # m.new_game()

    print(m.goal)

    test_hand = [13, 24, 30]
    m.new_round(test_hand)

    print(m.goal)


# Test whether model can process new top card
def testcase_cardplayed():
    m.update_top_card(4, Actor.player)
    print(m.goal)


def testcase_waitfacts():
    # wait fact in memory
    pulses1 = m.get_wait_time(10)
    seconds1 = temporal.pulses_to_time(pulses1)
    print(f"We have to wait {pulses1} pulses, which is {seconds1} s.")
    # no wait fact for this gap, partial retrieval
    pulses2 = m.get_wait_time(22)
    seconds2 = temporal.pulses_to_time(pulses2)
    print(f"We have to wait {pulses2} pulses, which is {seconds2} s.")


def testcase_calcgap():
    # an expected gap of hand > pile
    gap1 = m.determine_gap(14, 10)
    m.imaginal = None
    # special case hand is 100
    gap2 = m.determine_gap(100, 10)
    m.imaginal = None
    # anomoly case hand > pile
    gap3 = m.determine_gap(10, 14)
    print(gap1, gap2, gap3)


def testcase_deliberate():
    m.deliberate()


# Test the different success types
def testcase_success_late():
    # success.late
    tm.sleep(2)
    m.update_top_card(14, Actor.player)


testcase_newround()
# testcase_cardplayed()
# testcase_waitfacts()
# testcase_calcgap()
# testcase_deliberate()
testcase_success_late()
