'''
Input class
'''

# Import Python packages
import os, sys, cv2, json
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import time
from .DescriptorFactory import DescriptorFactory
#from sklearn.decomposition import PCA

class Input(DescriptorFactory):
    def __init__(self, input_file, crop, scale, base64_string=None):
        self.target_height = scale
        self.get_image(input_file, crop, scale, base64_string)
        self.create_image_crops()
        self.set_active_image()

    def get_image(self, input_file, crop, scale, base64_string=None):
        if input_file is not None:
            # Read in image from input file
            img = cv2.imread(input_file)
        else:
            print('read from base64')
            binary_data = base64.b64decode(base64_string)
            bytes_io = BytesIO(binary_data)
            image = Image.open(bytes_io)
            image_array = np.array(image)
            img = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)

        self.image = Input.crop_and_scale(img, crop, scale)

        if input_file is not None:
            #cv2.imwrite(input_file+'crop.jpg',img_crop)
            cv2.imwrite(input_file+'resized.jpg',self.image)

    def crop_and_scale(img, crop=None, scale=150):
        if ( crop is None or ( crop is not None and crop[0]==-1 ) ):
            height, width, channels = img.shape 
            crop_height, crop_width, start_width, start_height = height, width, 0, 0
        else:
            crop_height, crop_width, start_width, start_height = crop[0], crop[1], crop[2], crop[3]

        img_crop = np.zeros((crop_height, crop_width, 3), np.uint8)
        img_crop[:,:, :] = img[start_height:start_height+crop_height,start_width:start_width+crop_width,:]

        # Scale image
        height, width, channels = img_crop.shape 

        #scale will be defined by the target height of the image to analyze
        target_height = scale
        if height > target_height:
            scale = target_height/height
        else:
            scale = 1
        scaled_height = int(height*scale)
        scaled_width = int(width*scale)
        return cv2.resize(img_crop, (scaled_width, scaled_height), interpolation= cv2.INTER_LINEAR)

    # Set active image to match to database
    # image = 0 will set the active image to the entire image
    def set_active_image(self, image=0):
        if type(image) == str:
            if not hasattr(self, 'image_crops'):
                sys.exist('image_crops attribute does not exist')
            else:
                self.active_image = self.image_crops[image]
        else:
            self.active_image = self.image
        self.keypoints, self.descriptors = Input.generate_descriptors(self.active_image, target_height=self.target_height)

        reduce_dimensionality = False
        if reduce_dimensionality:
            self.descriptors = self.reduce_dimensionality()

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

        descriptor = self.descriptors

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

        print(f"normalized_descriptor: {normalized_descriptor.shape}")

        print('Dimensionality reduction took {} seconds'.format(time.time() - start_time))
        return reduced_descriptors

    def get_keypoints_and_descriptors(self):
        if not hasattr(self, 'image'):
            sys.exist('image attribute does not exist')
        self.keypoints, self.descriptors = Input.generate_descriptors(self.image, target_height=self.target_height)

    def create_image_crops(self):
        if not hasattr(self, 'image_crops'):
            self.image_crops = {}

    # height_offset, crop_height, and crop_width are in percentages of the height of the image
    # assumes that crop_name is a string
    def create_image_crop(self, crop_name, height_offset, crop_height, crop_width):
        if not hasattr(self, 'image'):
            sys.exist('image attribute does not exist')
        if not hasattr(self, 'image_crops'):
            sys.exist('image_crops attribute does not exist')
        height, width = self.image.shape[0], self.image.shape[1]
        cropped_height_start = int(height*height_offset)
        cropped_height_end = cropped_height_start + int(crop_height*height)
        cropped_width_start = int((width - int(crop_width*width))/2)
        cropped_width_end = cropped_width_start + int(crop_width*width)
        cropped_image = self.image[cropped_height_start:cropped_height_end,cropped_width_start:cropped_width_end]
        self.image_crops[crop_name] = cropped_image
