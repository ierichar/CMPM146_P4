from os import stat
from sys import settrace
import pyhop
import json

def check_enough (state, ID, item, num):
	if getattr(state,item)[ID] >= num: return []
	return False

def produce_enough (state, ID, item, num):
	return [('produce', ID, item), ('have_enough', ID, item, num)]

pyhop.declare_methods ('have_enough', check_enough, produce_enough)

def produce (state, ID, item):
	return [('produce_{}'.format(item), ID)]

pyhop.declare_methods ('produce', produce)

def make_method (name, rule):
	def method (state, ID):
		# your code here
		subTasks = []
		for prereq in rule["Recipes"][name]:
			if prereq == "Requires":
				reqItem = next(iter(rule["Recipes"][name][prereq]))
				subTasks.append(('have_enough', ID, reqItem, rule["Recipes"][name][prereq][reqItem]))
				
			if prereq == "Consumes":
				for item in rule["Recipes"][name][prereq]:
					subTasks.append(('have_enough', ID, item, rule["Recipes"][name][prereq][item]))
			
		subTasks.append(('op_'+name, ID))
		return subTasks
	return method

def declare_methods (data):
	# some recipes are faster than others for the same product even though they might require extra tools
	# sort the recipes so that faster recipes go first

	# your code here
	# hint: call make_method, then declare the method to pyhop using pyhop.declare_methods('foo', m1, m2, ..., mk)
	#all_recipes = dict() # key=timevalue, val=methodlist
	methods = []
	for item in data["Items"]:
		name = None
		for recipe in data["Recipes"]:
			newMethod = None
			for category in data["Recipes"][recipe]:
				if category == "Produces":
					if item == next(iter(data["Recipes"][recipe][category])):
						newMethod = make_method(recipe, data)
						newMethod.__name__ = recipe
						if methods == []:
							methods.append(newMethod)
						else:
							for method in methods:
								if (data["Recipes"][method.__name__]["Time"] >= data["Recipes"][recipe]["Time"]) and newMethod not in methods:
									methods.insert(methods.index(method), newMethod)
							if newMethod not in methods:
								methods.append(newMethod)
		name = "produce_" + item
		pyhop.declare_methods(name, *methods)
		methods.clear()
	
	for tool in data["Tools"]:
		name = None
		for recipe in data["Recipes"]:
			newMethod = None
			for category in data["Recipes"][recipe]:
				if category == "Produces":
					if tool == next(iter(data["Recipes"][recipe][category])):
						newMethod = make_method(recipe, data)
						newMethod.__name__ = recipe
						if methods == []:
							methods.append(newMethod)
						else:
							for method in methods:
								if (data["Recipes"][method.__name__]["Time"] >= data["Recipes"][recipe]["Time"]) and newMethod not in methods:
									methods.insert(methods.index(method.__name__), newMethod)
							if newMethod not in methods:
								methods.append(newMethod)
		name = "produce_" + tool
		pyhop.declare_methods(name, *methods)
		methods.clear()

	return

def make_operator (rule):
	def operator (state, ID):
		# your code here
		for element in rule:
			if element == 'Produces':
				item = rule[element]
				item_name = next(iter(rule[element]))
				value = rule[element][item_name]
				setattr(state, item_name, {ID: getattr(state, item_name)[ID] + value})

			elif element == 'Requires':
				for item in rule[element]:
					value = rule[element][item]
					if getattr(state, item)[ID] >= value:
						setattr(state, item, {ID: value})
					else:
						return False

			elif element == 'Consumes':
				for item in rule[element]:
					value = rule[element][item]
					if getattr(state, item)[ID] >= value:
						setattr(state, item, {ID: getattr(state, item)[ID] - value})
					else:
						return False

			elif element == "Time":
				value = rule[element]
				if getattr(state, "time")[ID] >= value:
					setattr(state, "time", {ID: getattr(state, "time")[ID] - value})
				else:
					return False
		return state
	return operator

def declare_operators (data):
	# your code here
	# hint: call make_operator, then declare the operator to pyhop using pyhop.declare_operators(o1, o2, ..., ok)
	ops = []
	for element in data["Recipes"]:
		holder = make_operator(data["Recipes"][element])
		holder.__name__ = "op_" + element
		ops.append(holder)
	pyhop.declare_operators(*ops)
	return

def add_heuristic (data, ID):
	# prune search branch if heuristic() returns True
	# do not change parameters to heuristic(), but can add more heuristic functions with the same parameters: 
	# e.g. def heuristic2(...); pyhop.add_check(heuristic2)

	# Heuristic determines whether or not we want to cut off an operator before
	# going to the following method

	def heuristic (state, curr_task, tasks, plan, depth, calling_stack):
		# can only ever consume 8 items in a given recipe (9 in Minecraft)
		for item in data["Items"]:
			if item != "rail":
				if getattr(state, item)[ID] > 18:
					return True
		return False


	def heuristic2 (state, curr_task, tasks, plan, depth, calling_stack):
		if depth == 0:
			for tool in data["Tools"]:
				made_tool = "made_"+tool
				setattr(state, made_tool, {ID: 0})
		return False
	
	def heuristic3 (state, curr_task, tasks, plan, depth, calling_stack):
		if curr_task[0] == 'produce':
			item = curr_task[2]
			for tool in data["Tools"]:
				if item == tool:
					made_check = "made_"+tool
					if (getattr(state, made_check)[ID] != 0):
						return True
					else:
						setattr(state, made_check, {ID: getattr(state,made_check)[ID] + 1})
						return False
		return False

	pyhop.add_check(heuristic)
	pyhop.add_check(heuristic2)
	pyhop.add_check(heuristic3)

def set_up_state (data, ID, time=0):
	state = pyhop.State('state')
	state.time = {ID: time}

	for item in data['Items']:
		setattr(state, item, {ID: 0})

	for item in data['Tools']:
		setattr(state, item, {ID: 0})

	for item, num in data['Initial'].items():
		setattr(state, item, {ID: num})

	return state

def set_up_goals (data, ID):
	goals = []
	for item, num in data['Goal'].items():
		goals.append(('have_enough', ID, item, num))

	return goals

if __name__ == '__main__':
	rules_filename = 'crafting.json'

	with open(rules_filename) as f:
		data = json.load(f)
	#print(data)
	state = set_up_state(data, 'agent', time=300) # allot time here
	goals = set_up_goals(data, 'agent')

	declare_operators(data)
	declare_methods(data)
	add_heuristic(data, 'agent')

	pyhop.print_operators()
	pyhop.print_methods()

	# Hint: verbose output can take a long time even if the solution is correct; 
	# try verbose=1 if it is taking too long
	pyhop.pyhop(state, goals, verbose=3)
	#pyhop.pyhop(state, ('have_enough', 'agent', 'wood', 1), verbose=3)
	#pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 20)], verbose=3)
