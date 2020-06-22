from model import Model
from cogmodel import CognitiveModel

# Tests whether adjusting the goal slot works effectively. It does.
def testcase_goal():
	m  = Model()
	m.new_game()

	# print(m)

	if m.goal.slots["pile"] == None:
		print("This works!")
		m1.goal.slots["pile"] = 2

	print(m.goal)
	
	if m.goal.slots["pile"] != None:
		print("This works too!")

testcase_goal()