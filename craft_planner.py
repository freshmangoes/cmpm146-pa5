import json
from collections import namedtuple, defaultdict, OrderedDict
from timeit import default_timer as time
from heapq import heappop, heappush
from math import ceil

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
        temp_state.update(inventory)
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
        if r.check(state):
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

        cost["plank"] = 1 + ceil(cost["wood"]/4)
        cost["stick"] = 1 + ceil(cost["plank"]/2)

        tool_base = 100

        cost["bench"] = tool_base + cost["plank"]*(4 - inventory["plank"])
        cost["furnace"] =  tool_base + cost["bench"]*(1 - inventory["bench"]) + cost["cobble"]*(8 - inventory["cobble"])
        cost["ingot"] = 5 + cost["coal"] + cost["ore"] + cost["furnace"]*(1 - inventory["furnace"])
        cost["wooden_axe"] = tool_base + cost["bench"]*(1 - inventory["bench"]) + cost["plank"]*(3 - inventory["plank"]) + cost["stick"]*(2 - inventory["stick"])
        cost["wooden_pickaxe"] = cost["wooden_axe"]
        cost["stone_axe"] = tool_base + cost["bench"]*(1 - inventory["bench"]) + cost["cobble"]*(3 - inventory["cobble"]) + cost["stick"]*(2 - inventory["stick"])
        cost["stone_pickaxe"] = cost["stone_axe"]
        cost["iron_axe"] = tool_base + cost["bench"]*(1 - inventory["bench"]) + cost["ingot"]*(3 - inventory["ingot"]) + cost["stick"]*(2 - inventory["stick"])
        cost["iron_pickaxe"] = cost["iron_axe"]

        cost["cart"] = 1 + cost["bench"]*(1 - inventory["bench"]) + cost["ingot"]*(5 - inventory["ingot"])
        # cost["rail"] = 1 + cost["bench"]*(1 - inventory["bench"]) + ceil(6*(cost["ingot"]*(5 - inventory["ingot"]))/16 + (cost["stick"]*(1 - inventory["stick"]))/16)
        # cost["rail"] = 1 + cost["bench"]*(1 - inventory["bench"]) + ceil(6*(cost["ingot"]*(5 - inventory["ingot"])) + (cost["stick"]*(1 - inventory["stick"])))
        cost["rail"] = 1 + cost["bench"]*(1 - inventory["bench"]) + cost["ingot"]*(6 - inventory["ingot"])


        tools = ["wooden_axe", "wooden_pickaxe", "stone_axe", "stone_pickaxe", "bench", "furnace"]

        for key in inventory:
            if key in goal:
                if inventory[key] < goal[key]:
                    if key in cost:
                        hue_val += cost[key] * (goal[key] - inventory[key])
                    else:
                        hue_val += goal[key] - inventory[key]
                elif key in tools:
                    if inventory[key] > 1:
                        hue_val = float('inf')
                elif inventory[key] > 8:
                    if key == "rail":
                        hue_val += 0
                    else:
                        hue_val = float('inf')
            elif key in tools:
                if inventory[key] > 1:
                    hue_val = float('inf')
            elif inventory[key] > 8:
                hue_val = float('inf')
        return hue_val
    return get_hue


def search(state, is_goal, limit, get_hue, all_recipes):
    start_time = time()
    temp_state = state.copy()

    prio_q = []
    # visited = set()
    distance = {}
    prev = {}

    initial = (get_hue(temp_state), temp_state, "Start", 0)
    distance[initial] = 0
    heappush(prio_q, initial)

    # Search
    while time() - start_time < limit:
        if len(prio_q) > 0:
            node = heappop(prio_q)

            if is_goal(node[1]):
                print("Path found in "+str(time() - start_time)+" seconds!")
                path = []
                while node[1] in prev:
                    path.append([node[3], node[2], node[1]])
                    node = prev[node[1]]
                path.append([node[3], node[2], node[1]])
                path.reverse()
                return path
            neighbors = graph(node[1], all_recipes)
            # n[0] - name
            # n[1] - state
            # n[2] - cost
            print(node)
            for n in neighbors:
                distance_through_node = node[0] - get_hue(node[1]) + n[2]
                if n[1] not in distance or distance_through_node < distance[n[1]]:
                    distance[n[1]] = distance_through_node
                    prev[n[1]] = node
                    new_node = (get_hue(n[1]) + distance[n[1]], n[1], n[0], n[2])
                    heappush(prio_q, new_node)

    # Failed to find a path
    print("Failed to find a path from", state, 'within time limit.')
    return []

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
    goal = Crafting['Goal']
    # goal = {"cart": 1}
    # goal = {"iron_axe": 1}
    is_goal = make_goal_checker(goal)
    get_hue = make_heuristic(goal)
    # Initialize first state from initial inventory
    state = State({key: 0 for key in Crafting['Items']})
    state.update(Crafting['Initial'])
    # Search - This is you!
    path = search(state, is_goal, 30, get_hue, all_recipes)
    total_cost = 0
    for action in path:
        total_cost += action[0]
        inventory = {}
        for i_name, i_amount in action[2].items():
            if i_amount > 0:
                inventory[i_name] = i_amount
        print(str(action[0])+', '+action[1]+', '+str(inventory))
    totals = {"total_cost": total_cost, "length": len(path)-1}
    print("\n"+str(totals))
