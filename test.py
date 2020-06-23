from model import Model
from cogmodel import CognitiveModel

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

# testcase_goal()
testcase_newround()
testcase_cardplayed()
