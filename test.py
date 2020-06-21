from cogmodel import CognitiveModel

def test():
	m  = CognitiveModel()
	# print(m)
	if m.goal.slots["pile"] == None:
		print("This works!")
		m.goal.slots["pile"] = 2

	print(m.goal)
	
	if m.goal.slots["pile"] != None:
		print("This works too!")

test()