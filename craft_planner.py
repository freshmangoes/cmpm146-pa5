import json
from collections import namedtuple, defaultdict, OrderedDict
from timeit import default_timer as time
from heapq import heappop, heappush

Recipe = namedtuple('Recipe', ['name', 'check', 'effect', 'cost'])


class State(OrderedDict):
    """ This class is a thin wrapper around an OrderedDict, which is simply a
        dictionary which keeps the order in which elements are added (for
        consistent key-value pair comparisons). Here, we have provided
        functionality for hashing, should you need to use a state as a
        key in another dictionary, e.g. distance[state] = 5. By default,
        dictionaries are not hashable. Additionally, when the state is
        converted to a string, it removes all items with quantity 0.

        Use of this state representation is optional, should you prefer
        another.
    """

    def __key(self):
        return tuple(self.items())

    def __hash__(self):
        return hash(self.__key())

    def __lt__(self, other):
        return self.__key() < other.__key()

    def copy(self):
        new_state = State()
        new_state.update(self)
        return new_state

    def __str__(self):
        return str(dict(item for item in self.items() if item[1] > 0))


def make_checker(rule):
    # Returns a function to determine whether a state meets a
    # rule's requirements.
    # This code runs once, when the rules are constructed before the search
    # is attempted.

    consume = {}
    reqs = {}

    for item_name in Crafting['Items']:
        if 'Consumes' in rule:
            if item_name in rule['Consumes']:
                consume[item_name] = rule['Consumes'][item_name]
        if 'Requires' in rule:
            if item_name in rule['Requires']:
                reqs[item_name] = rule['Requires'][item_name]
    # print("In make_checker")
    # print("Consumes:: " + str(consume))
    # print("Requires:: " + str(reqs))

    def check(state):
        # This code is called by graph(state) and runs millions of times.
        # Tip: Do something with rule['Consumes'] and rule['Requires'].
        inventory = state.items()

        for i_name, i_amount in inventory:
            if i_name in reqs:
                if i_amount < 1:
                    return False
            if i_name in consume:
                if i_amount < consume[i_name]:
                    return False
        return True

    return check


def make_effector(rule):
    # Returns a function which transitions from state to new_state
    # given the rule.
    # This code runs once, when the rules are constructed before the
    # search is attempted.

    consume = {}
    produce = {}
    for item_name in Crafting['Items']:
        if 'Consumes' in rule:
            if item_name in rule['Consumes']:
                consume[item_name] = rule['Consumes'][item_name]
        if 'Produces' in rule:
            if item_name in rule['Produces']:
                produce[item_name] = rule['Produces'][item_name]
    # print("In make_effector")
    # print("Consumes:: " + str(consume))
    # if len(consume) > 0:
    #     print(consume[0][1])
    #     if len(consume) > 1:
    #         print(consume[1][1])
    # print("Produces:: " + str(produce))

    def effect(state):
        # This code is called by graph(state) and runs millions of times
        # Tip: Do something with rule['Produces'] and rule['Consumes'].
        temp_state = state.copy()
        inventory = {}

        for i_name, i_amount in temp_state.items():
            inventory[i_name] = i_amount

        for consumed_items in consume:
            inventory[consumed_items] -= consume[consumed_items]
        for produced_items in produce:
            inventory[produced_items] += produce[produced_items]
        # print(temp_state.__str__())
        temp_state.update(inventory)
        # print(temp_state.__str__())
        return temp_state

    return effect


def make_goal_checker(goal):
    # Returns a function which checks if the state has met the goal criteria.
    # This code runs once, before the search is attempted.

    def is_goal(state):
        # This code is used in the search process and may be called
        # millions of times.
        inventory = state.items()
        for i_name, i_amount in inventory:
            if i_name in goal:
                if i_amount < goal[i_name]:
                    return False

        return True

    return is_goal


def graph(state, all_recipes):
    # Iterates through all recipes/rules, checking which are valid in the
    # given state.
    # If a rule is valid, it returns the rule's name, the resulting state
    # after application to the given state, and the cost for the rule.
    for r in all_recipes:
        # print(r)
        if r.check(state):
            # print(r.name, r.effect(state), r.cost)
            yield (r.name, r.effect(state), r.cost)


def make_heuristic(goal):
    # This heuristic function should guide your search.
    def get_hue(state):
        hue_val = 0
        temp_state = state.copy()
        inventory = {}
        for i_name, i_amount in temp_state.items():
            inventory[i_name] = i_amount

        cost = {}

        if inventory["stone_axe"] >= 1:
            cost["wood"] = 2
        elif inventory["wooden_axe"] >= 1:
            cost["wood"] = 4
        else:
            cost["wood"] = 8

        if inventory["iron_pickaxe"] >= 1:
            cost["cobble"] = 2
            cost["coal"] = 2
            cost["ore"] = 4
        elif inventory["stone_pickaxe"] >= 1:
            cost["cobble"] = 4
            cost["coal"] = 4
            cost["ore"] = 8
        elif inventory["wooden_pickaxe"] >= 1:
            cost["cobble"] = 8
            cost["coal"] = 8
            cost["ore"] = 16
        else:
            cost["cobble"] = 16
            cost["coal"] = 16
            cost["ore"] = 32

        # cost["iron_axe"] = 200
        # cost["iron_pickaxe"] = 200
        # cost["stone_axe"] = 200
        # cost["stone_pickaxe"] = 200
        # cost["wooden_axe"] = 200
        # cost["wooden_pickaxe"] = 200
        # cost["bench"] = 200
        # cost["furnace"] = 200

        for key in goal:
            if inventory[key] < goal[key]:
                if key in cost:
                    hue_val += cost[key] * (goal[key] - inventory[key])
                else:
                    hue_val += goal[key] - inventory[key]
        return hue_val
    return get_hue


def search(state, is_goal, limit, get_hue, all_recipes):
    start_time = time()
    temp_state = state.copy()

    prio_q = []
    visited = set()
    distance = {}
    prev = {}

    initial = (get_hue(temp_state), temp_state)
    distance[initial] = 0

    heappush(prio_q, initial)

    # Search
    while time() - start_time < limit:
        if len(prio_q) > 0:
            node = heappop(prio_q)

            if is_goal(node[1]):
                print("Path found!")
                path = []
                while node[1] in prev:
                    path.append(node[1])
                    node = prev[node]
                path.append(node[1])
                path.reverse()
                return path
            # print(node[0], node[1])
            neighbors = graph(node[1], all_recipes)
            # print(neighbors)

            action = None
            # print(str(node[0]) + ", " + action + ", " + str(node[1]))

            for n in neighbors:
                # print(n.__str__())
                # distance_through_node = node[0] - get_hue(node[1]) + n[2]
                distance_through_node = node[0] + n[2]
                if n[1] in distance:
                    if distance_through_node < distance[n[1]]:
                        distance[n[1]] = distance_through_node
                        prev[n[1]] = node
                else:
                    distance[n[1]] = distance_through_node
                    prev[n[1]] = node
                new_node = (get_hue(n[1]) + distance[n[1]], n[1])
                heappush(prio_q, new_node)
                action = n[0]
            visited.add(node)
            # Printing stuff
            print(str(node[0]) + ", " + action + ", " + str(node[1]))

    # Failed to find a path
    print("Failed to find a path from", state, 'within time limit.')
    return None

if __name__ == '__main__':
    with open('Crafting.json') as f:
        Crafting = json.load(f)

    # List of items that can be in your inventory:
    print('All items:', Crafting['Items'])

    # List of items in your initial inventory with amounts:
    print('Initial inventory:', Crafting['Initial'])

    # List of items needed to be in your inventory at the end of the plan:
    print('Goal:', Crafting['Goal'])

    # Dict of crafting recipes (each is a dict):
    print('Example recipe:', 'craft stone_pickaxe at bench ->',
          Crafting['Recipes']['craft stone_pickaxe at bench'])

    # Build rules
    all_recipes = []
    for name, rule in Crafting['Recipes'].items():
        # print("Name:: " + str(name))
        checker = make_checker(rule)
        effector = make_effector(rule)
        recipe = Recipe(name, checker, effector, rule['Time'])
        all_recipes.append(recipe)

    # Create a function which checks for the goal
    # goal = {"wooden_axe": 10, "bench": 10, "wood": 90, "wooden_pickaxe": 5, "cobble": 100}
    goal = Crafting['Goal']
    is_goal = make_goal_checker(goal)
    get_hue = make_heuristic(goal)
    # Initialize first state from initial inventory
    state = State({key: 0 for key in Crafting['Items']})
    state.update(Crafting['Initial'])
    # Search - This is you!
    search(state, is_goal, 30, get_hue, all_recipes)
