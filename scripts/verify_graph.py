import argparse
import json
import os
import sys

graph_path = "graph"
raw_path = "raw"

class Conditions:

    def __init__(self):
        self.items = []
        self.tasks = []

    def extend(self, items, tasks):
        self.items.extend(items)
        self.tasks.extend(tasks)

    def can_fulfill(self, task_key):
        task_is_complted = task_key in self.tasks
        if task_is_complted:
            return True
        
        task = raw_data["tasks"][task_key]
        task_can_be_completed = ((task["task_obstacle"] is None or task["task_obstacle"] in self.tasks) and all([item in self.items for item in task["items_needed"]]))
        
        return task_can_be_completed
                
        

def check_edge_lengths(graph_data, raw_data, warning_prefix):
    all_good = True

    edges = graph_data["edges"]
    vertices = graph_data["vertices"]
    
    for edge in edges:
        from_vertex_key = edge["from"]
        to_vertex_key = edge["to"]
        
        from_vertex = vertices[str(from_vertex_key)]
        to_vertex = vertices[str(to_vertex_key)]
        
        from_scene = from_vertex["furthest_scene"]
        to_scene = to_vertex["furthest_scene"]

        expected_length = edge["length"]

        conditions = Conditions()
        for condition_vertex in edge["conditions"]:
            vertex = vertices[str(condition_vertex)]
            conditions.extend(vertex["items"], vertex["tasks"])

        alternative_conditions = Conditions()
        for alternative_edge in edges:
            if alternative_edge["from"] == to_vertex_key and alternative_edge["to"] == from_vertex_key:
                for condition_vertex in alternative_edge["conditions"]:
                    vertex = vertices[str(condition_vertex)]
                    alternative_conditions.extend(vertex["items"], vertex["tasks"])

        post_scene = None
        for task in from_vertex["tasks"]:
            if raw_data["tasks"][task]["post_scene"] is not None:
                post_scene = raw_data["tasks"][task]["post_scene"]

        start_scene = from_scene
        additional_length = 0
        if post_scene is not None:
            start_scene = post_scene
            additional_length = 1
            
        actual_length = calculate_minimum_distance(raw_data, start_scene, to_scene, [], conditions)

        if actual_length is None:
            actual_length = calculate_minimum_distance(raw_data, start_scene, to_scene, [], alternative_conditions)
            
        
        if actual_length is not None:
            actual_length += additional_length

        if expected_length != actual_length:
            all_good = False
            print(warning_prefix + "Exptected length for edge from vertex", edge["from"], "(scene \"" + str(from_scene) + "\") to vertex", edge["to"], "(scene \"" + str(to_scene) + "\")",
                  "to be", expected_length, "but actual length is calculated to be", actual_length)

    return all_good


def calculate_minimum_distance(raw_data, from_scene, to_scene, visited_scenes, conditions):
    if from_scene == to_scene:
        return 0

    minimum_distance_for_next_scenes = None

    for next_scene_key in raw_data["scenes"][from_scene]["connected_scenes"]:
        if next_scene_key in visited_scenes:
            continue

        next_scene = raw_data["scenes"][next_scene_key]

        task_obstacle_key = next_scene["task_obstacle"]
        if task_obstacle_key is not None:
            if not conditions.can_fulfill(task_obstacle_key):
                continue
                
        next_visited_scenes = visited_scenes.copy()
        next_visited_scenes.append(next_scene_key)

        distance = calculate_minimum_distance(raw_data, next_scene_key, to_scene, next_visited_scenes, conditions)
        if distance is None:
            continue

        if minimum_distance_for_next_scenes is None or distance < minimum_distance_for_next_scenes:
            minimum_distance_for_next_scenes = distance

    if minimum_distance_for_next_scenes is None:
        return None

    return minimum_distance_for_next_scenes + 1

def fetch_graph_ids():
    graph_ids = []
    for file in os.listdir(graph_path):
        if os.path.isfile(os.path.join(graph_path, file)):
            graph_ids.append(file.split("_")[1])

    return graph_ids

parser = argparse.ArgumentParser(description='Verify graph data up against raw data')
parser.add_argument('--warning-prefix', dest='warning_prefix', default=" - ",
                    help='Prefix printed before warning messages')

args = parser.parse_args()
warning_prefix = args.warning_prefix

exit_code = 0
for game_version in fetch_graph_ids():
    print("Check edge lenghts for game version " + game_version + ":")
    with open(os.path.join(graph_path, "ss_" + game_version + "_graph.json")) as graph_file:
        graph_data = json.load(graph_file)
    
    with open(os.path.join(raw_path, "ss_" + game_version + "_raw.json")) as graph_file:
        raw_data = json.load(graph_file)

    if check_edge_lengths(graph_data, raw_data, warning_prefix):
        print(" - OK")
    else:
        exit_code = 1

sys.exit(exit_code)
