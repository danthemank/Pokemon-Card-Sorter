'''
Database class
'''

# Import Python packages
import os, cv2, json
import numpy as np
import boto3
import io
import re
import numpy as np
#from sklearn.decomposition import PCA
import time
from .DescriptorFactory import DescriptorFactory

debug = False

class Database(DescriptorFactory): 
    def __init__(self, descriptors_file, use_s3=False, image_range=None, subset=None):
        #use_s3 = True
        self.use_s3 = use_s3
        if self.use_s3:
            if False:
                # Set the AWS credentials
                aws_access_key_id = 'AKIAQWFWTPPZJ7WAVQXY'
                aws_secret_access_key = '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'
                
                # Set the AWS credentials for Boto3
                session = boto3.Session(
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key
                        )
                self.s3_client = session.client('s3')
            else:    
                self.s3_client = boto3.client('s3')

        self.descriptors_offset = 0

        #print ('loading database')
        #start_time=time.time()
        if image_range is not None:
            self.get_descriptors_offset(descriptors_file, image_range)
        else:
            self.get_descriptors(descriptors_file)
        #print(f'database loaded: {time.time()-start_time}')

        #self.reduce_dimensionality()
        reduce_dimensionality = False
        if reduce_dimensionality:
            self.read_reduced_descriptors()

        if subset is not None:
            selected_descriptors = {}
            cards = set( os.path.join(item['set_code'], item['code']) for item in subset )

            for file, descriptors in self.descriptors.items():
                parts = file.split('/')
                set_name = parts[-2]
                card_name = parts[-1].split('.')[0]
                full_name = os.path.join(set_name, card_name)
                if full_name in cards:
                    selected_descriptors[full_name] = descriptors

            self.descriptors = selected_descriptors
            print('high value cards:', len(self.descriptors))

    def read_reduced_descriptors(self):
        self.descriptors = np.load(os.path.join("matchingScript", "reduced_descriptors_dict.npz"), allow_pickle=True)
        #for key, value in self.descriptors.items():
        #    print(f'key: {key}')
        #    print(f'value: {value}')
        #    print(f'value.shape: {value.shape}')

    def reduce_dimensionality(self):
        start_time = time.time()
        print('Reducing dimensionality...')

        # Extract the descriptors from the dictionary
        descriptors = []
        image_names = []
        common_shape = (250, 128)  # Replace n and m with desired shape
        i= 0

        # Step 4: Apply PCA
        num_reduced_dimensions = 40  # Specify the desired number of reduced dimensions
        pca = PCA(n_components=num_reduced_dimensions)

        reduced_descriptor_dict = {}

        for file, descriptor in self.descriptors.items():
            i += 1
            if i>100:
                pass
                #break
            print(f"\rReducing dimensionality for image {i} of {len(self.descriptors)} {file}", end="")
            image_names.append(file)

            # Pad or truncate the descriptor to a common shape (e.g., (n, m))
            if descriptor.shape != common_shape:
                # Pad or truncate the descriptor to the common shape
                if descriptor.shape[0] > common_shape[0]:
                    descriptor = descriptor[:common_shape[0]]
                else:
                    padding = np.zeros(common_shape)
                    padding[:descriptor.shape[0]] = descriptor
                    descriptor = padding

            # Step 3: Normalize data
            mean_vector = np.mean(descriptor, axis=0)
            std_vector = np.std(descriptor, axis=0)
            normalized_descriptor = (descriptor - mean_vector) / std_vector

            # Step 5: Fit PCA on the data and transform it
            reduced_descriptors = pca.fit_transform(normalized_descriptor)

            reduced_descriptor_dict[file] = reduced_descriptors

        print(f"image_names: {len(image_names)}")
        print(f"descriptors: {len(reduced_descriptor_dict.keys())}")

        # Save the reduced descriptor dictionary and the reduced descriptors to the .npy file
        np.savez(os.path.join("matchingScript", "reduced_descriptors_dict.npz"), **reduced_descriptor_dict)

        # Now 'reduced_descriptors' contains the descriptors with reduced dimensionality
        self.descriptors = reduced_descriptor_dict

        print('Dimensionality reduction took {} seconds'.format(time.time() - start_time))

    def get_descriptors_offset(self, descriptors_file, image_range):
        start_num, end_num = image_range
        if self.use_s3:
            bucket_name, prefix = descriptors_file.split('/')
            prefix="SIFT_"
            response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            print(response)
            object_keys = [obj['Key'] for obj in response['Contents']]
            print(object_keys)
        else:
            #get the path of the folder containing the descriptors
            folder_path = os.path.dirname(descriptors_file)
            #print(folder_path)
            prefix="SIFT_"
            object_keys = [f for f in os.listdir(folder_path) if f.startswith(prefix)]

        # Filter the object keys to include only the keys that have numbers within the specified range in their names
        selected_keys = []
        start, end = image_range
        if end == -1:
            selected_keys = object_keys
        else:
            offset = []
            for key in object_keys:
                # Extract the numbers from the object key using regular expressions
                matches = re.search(r'SIFT_(\d+)_(\d+)\.npz', key)
                if matches:
                    start_num = int(matches.group(1))
                    end_num = int(matches.group(2))
                    #print(start_num, end_num)
                    if not (start>end_num or end<start_num):
                        #if start_num <= start <= end_num or start_num <= end <= end_num:
                        selected_keys.append(key)
                        offset.append(start_num)
            if len(offset) > 0:
                self.descriptors_offset = min(offset)
            print(f"offset: {self.descriptors_offset}")

        self.descriptors = {}
        # Load the JSON data from each selected file and merge it into a single dictionary

        selected_keys = list(sorted(selected_keys, key=lambda filename: int(filename.split('_')[1])))
        print(selected_keys)
        for key in selected_keys:
            if self.use_s3:
                response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
                s3_object_data = response['Body'].read()
                in_memory_buffer = io.BytesIO(s3_object_data)
            else:
                path= os.path.join(folder_path, key)
                in_memory_buffer = open(path, 'rb')

            descriptors = np.load(in_memory_buffer)
            # Update the 'all_descriptors' dictionary with the descriptors from the current file
            self.descriptors.update(descriptors)

        print('\nLoaded {} descriptors'.format(len(self.descriptors)))
        #for key in self.descriptors:
        #    print(key)
        #    print(self.descriptors[key].shape)
        #    print(self.descriptors[key])
        #    break

    def get_descriptors(self, descriptors_file):
        if self.use_s3:
            bucket=descriptors_file.split('/')
            response = self.s3_client.get_object(Bucket=bucket[0], Key=bucket[1])
            s3_object_data = response['Body'].read()
            in_memory_buffer = io.BytesIO(s3_object_data)

            self.descriptors = np.load(in_memory_buffer)
        else:
            self.descriptors = np.load(descriptors_file)
        #print(self.descriptors)


    @staticmethod
    def generate_database_descriptor_files(database_dir, descriptors_file, descriptors_length_file, db_dict_file, target_height=-1):
        db_descriptors = {}
        all_files=[]
        for root, dirs, files in os.walk(database_dir):
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)
        total_files = len(all_files)
        i=0
        print()
        for img in sorted(all_files, key=lambda e: e.split('.')[0].split('_')[-1]):
            i+=1
            print (f'\ranalysing file: {i}/{total_files}  {img}',end="")
            image = cv2.imread(img)
            if image is None: continue

            keypoints, descriptors = Database.generate_descriptors(image, target_height)

            db_descriptors[img] = descriptors
            if debug:
                print('descriptors for image '+str(img)+' extracted\n')
                print(descriptors)
        np.savez(descriptors_file, **db_descriptors)
        db_dict = {}
        descriptors_len = []
        for i,img in enumerate(db_descriptors): 
            db_dict[i] = img
            descriptors = db_descriptors[img]
            if descriptors is None:
                raise Exception('no descriptors for image '+str(img))
            else:
                descriptors_len.append(descriptors.shape[0])
        with open(db_dict_file, 'w') as f:
            json.dump(db_dict, f, indent=4)
        f.close()
        np.save(descriptors_length_file,np.array(descriptors_len))

    @staticmethod
    def crop_database_images(database_dir, cropped_database_dir, height_offset, crop_height, crop_width, special_images=([],None,None,None)):
        '''
        special_images in the form (image_indexes: list, height_offset: float, crop_height: float, crop_width: float)
        '''
        def crop_image(img, height_offset, crop_height, crop_width):
            height, width = img.shape[0], img.shape[1]
            cropped_height_start = int(height*height_offset)
            cropped_height_end = cropped_height_start + int(crop_height*height)
            cropped_width_start = int((width - int(crop_width*width))/2)
            cropped_width_end = cropped_width_start + int(crop_width*width)
            cropped_img = img[cropped_height_start:cropped_height_end,cropped_width_start:cropped_width_end,:]
            return cropped_img
        _height_offset = None; _crop_height = None; _crop_width = None
        for img in sorted(os.listdir(database_dir)):
            img_cv = cv2.imread(os.path.join(database_dir,img))
            if int(img.split('.')[0]) in special_images[0]:
                _height_offset = special_images[1]; _crop_height = special_images[2]; _crop_width = special_images[3]
            else:
                _height_offset = height_offset; _crop_height = crop_height; _crop_width = crop_width
            cropped_img = crop_image(img_cv,height_offset,crop_height,crop_width)
            cv2.imwrite(os.path.join(cropped_database_dir,img),cropped_img)

        

