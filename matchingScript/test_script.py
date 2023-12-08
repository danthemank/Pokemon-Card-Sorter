'''
Match query image to database
'''

# Import Python packages
import os
import sys

# Import local packages
#from DatabaseImageMatching.Database import Database
#from DatabaseImageMatching.Input import Input
#from DatabaseImageMatching.Matcher import Matcher

# Paths to Database Variables
DESCRIPTOR_NPZ_FILE = r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\Pokemon\Info_Dataset_4\SIFT4_2.npz"
DESCRIPTOR_LENGTH_NPZ_FILE = r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\Pokemon\Info_Dataset_4\Database_Descriptors.npy"
DATABASE_DICT_FILE = r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\Pokemon\Info_Dataset_4\Database_Dict.json"
DATABASE_FILE = r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\Pokemon\Info_Dataset_4\Database.json"

# Construct database from pre-stored files
#database = Database(DESCRIPTOR_NPZ_FILE, DESCRIPTOR_LENGTH_NPZ_FILE, DATABASE_DICT_FILE, DATABASE_FILE)

# Generate query input from image file
input_file = r"C:\Users\rickl\OneDrive\Documents\Simerse\Clients\Goodwill\York\Event\Samples300\2022-05-10 14.28.10.jpg"
input_file = sys.argv[1]#image got from camera feed

initial_crop = (1144, 1016, 716, 992) # Crop input image to card - (crop_height, crop_width, start_width, start_height)
initial_scale = 0.5 # Scale cropped input image to reduce run-time
#query = Input(input_file, initial_crop, initial_scale)
#query.create_image_crop('FullCard',0.0,1.0,1.0) # Feed all of card into image matcher
#query.set_active_image('FullCard')

# Match query image to database
#matcher = Matcher('bf')
#match = matcher.match_input_to_database(query, database)
#print(f'Match = {match}')
match = '2022-05-10 14.16.08.jpg'#assuming above line returns the file name as stated

#throw error

sys.stdout.write('\nScriptParameters:'+str(sys.argv))
sys.stdout.write('\nScriptResults:'+match)
sys.exit(0)