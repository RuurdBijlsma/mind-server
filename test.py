from model import Model
from cogmodel import CognitiveModel
import temporal

m = Model()
m.new_game()

# Test whether model can process new hands
def testcase_newround():
	# m = Model()
	# m.new_game()

	print(m.goal)

	test_hand = [1, 2, 3]
	m.new_round(test_hand)

	print(m.goal)

# Test whether model can process new top card
def testcase_cardplayed():
	m.update_top_card(4)
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


testcase_newround()
testcase_cardplayed()
testcase_waitfacts()