'''
Matcher class
'''

# Import Python packages
import os, sys, cv2, json
import numpy as np
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime
from multiprocessing import Pool, cpu_count

# Import local modules
from DatabaseImageMatching.Database import Database
from DatabaseImageMatching.Input import Input

class Matcher:
    def __init__(self, matcher_type):
        self.get_matcher(matcher_type)

    def get_matcher(self, matcher_type):
        self.matcher_type = matcher_type
        self.matchers = ['bf', 'flann']
        if matcher_type not in self.matchers: 
            sys.exit('Matcher not supported')
        if matcher_type == 'bf':
            self.matcher = cv2.BFMatcher(cv2.NORM_L1, crossCheck=True)
        if matcher_type == 'flann':
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
            search_params = dict(checks=50)   # or pass empty dictionary
            self.matcher = cv2.FlannBasedMatcher(index_params,search_params)

    def get_distance_distribution(self, input, database):
        #print('get_distance_distribution')
        self.distance_distribution = {}
        database_descriptors = database.descriptors
        input_descriptors = input.descriptors

        if input.image_range[1] == -1:
            input.image_range[1] = len(database_descriptors) + database.descriptors_offset
        self.image_range = input.image_range
        image_range = self.image_range
        lower_bound = image_range[0]
        upper_bound = image_range[1] + 1 
        if upper_bound > len(database_descriptors) + database.descriptors_offset:
            upper_bound = len(database_descriptors) + database.descriptors_offset
        if lower_bound > len(database_descriptors) + database.descriptors_offset:
            return
        lower_bound = lower_bound - database.descriptors_offset
        upper_bound = upper_bound - database.descriptors_offset
        keys = list(database_descriptors.keys())
        #print ("running matching algorithm")
        #total=upper_bound-lower_bound
        for i, img in enumerate(keys[lower_bound:upper_bound]):
            #print (f"image: {i} of {total}  {img}                \r",end="")
            j = i + database.descriptors_offset + lower_bound
            db_descriptors = database_descriptors[img]
            reduce_dimensionality = False
            if reduce_dimensionality:
                input_descriptors_uint8 = np.uint8(input_descriptors * 255) # Scale the float values to [0, 255]
                db_descriptors_uint8 = np.uint8(db_descriptors * 255)
                matches = self.matcher.match(input_descriptors_uint8,db_descriptors_uint8)
            else:
                matches = self.matcher.match(input_descriptors,db_descriptors)#features in both cards that match of a total possible 128
            for match in matches:
                row = self.distance_distribution.get(match.queryIdx)
                if row is None:
                    self.distance_distribution[match.queryIdx] = row = {}
                row[img] = match.distance

    def _match_input_to_database(self, database):
        database_image_votes = {}

        if len(self.distance_distribution)==0:
            return None, None

        for d in self.distance_distribution:
            distances = self.distance_distribution[d]
            distances_sorted = sorted(distances.items(), key=lambda x: x[1])
            idx_best_distance = distances_sorted[0][0]
            if idx_best_distance not in database_image_votes:
                database_image_votes[idx_best_distance] = 0
            database_image_votes[idx_best_distance] += 1

        max_matches_index = max(database_image_votes, key=lambda k: database_image_votes[k])

        match_distances=[]
        for d in self.distance_distribution:
            distances = self.distance_distribution[d]
            distance = [ x[1] for x in distances.items() if x[0] == max_matches_index ]
            if len(distance)>0:
                match_distances.append(distance[0])
            else:
                match_distances.append(10000)#penalize when there's no match

        selected_match_distance = sum([x for x in match_distances if x != None])/len(match_distances)

        return max_matches_index, selected_match_distance

    def match_input_to_database(self, input, database):
        self.get_distance_distribution(input, database)
        match = self._match_input_to_database(database)
        return match 

    def get_match_attributes(self, match, database):
        return database.database[match]
