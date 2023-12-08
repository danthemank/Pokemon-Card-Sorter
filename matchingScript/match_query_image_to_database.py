'''
Match query image to database
'''

# Import Python packages
import os

# Import local packages
from DatabaseImageMatching.Database import Database
from DatabaseImageMatching.Input import Input
from DatabaseImageMatching.Matcher import Matcher

# Paths to Database Variables
DESCRIPTOR_NPZ_FILE=r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\York\Event\DatabaseDescriptors300\SIFT.npz"
DESCRIPTOR_LENGTH_NPZ_FILE=r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\York\Event\DatabaseDescriptors300\Database_Descriptors.npy"
DATABASE_DICT_FILE=r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\York\Event\DatabaseDescriptors300\Database_Dict.json"
DATABASE_FILE = r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\Pokemon\Info_Dataset_4\Database.json"
DATABASE_FILE = r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\York\Event\DatabaseDescriptors300\Database300.json"

# Construct database from pre-stored files
database = Database(DESCRIPTOR_NPZ_FILE, DESCRIPTOR_LENGTH_NPZ_FILE, DATABASE_DICT_FILE, DATABASE_FILE)

# Generate query input from image file
input_file = r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\York\Event\PokemonCardsForEvent\2022-05-09 16.23.02.jpg"
initial_crop = (740, 1040, 1628, 988) # Crop input image to card - (crop_height, crop_width, start_width, start_height)
initial_scale = 0.5 # Scale cropped input image to reduce run-time
query = Input(input_file, initial_crop, initial_scale)
query.create_image_crop('FullCard',0.0,1.0,1.0) # Feed all of card into image matcher
query.set_active_image('FullCard')

# Match query image to database
matcher = Matcher('bf')
match = matcher.match_input_to_database(query, database)
match_attributes = matcher.get_match_attributes(match, database)
print(f'Match = {match}, Attributes = {match_attributes}')