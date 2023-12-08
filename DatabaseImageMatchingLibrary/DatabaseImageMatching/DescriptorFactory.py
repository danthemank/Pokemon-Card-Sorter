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


debug = False

class DescriptorFactory:
    @classmethod
    def generate_descriptors(cls, image, target_height=-1):
        if target_height>0:
            height, width, channels = image.shape 
            scale = target_height/height
            scaled_height = int(height*scale)
            scaled_width = int(width*scale)
            image = cv2.resize(image, (scaled_width, scaled_height), interpolation= cv2.INTER_LINEAR)
                
            # Resize the image using the calculated dimensions
            image = cv2.resize(image, (scaled_width, scaled_height), interpolation=cv2.INTER_LINEAR)

            if False:
                output_path = 'resized_image'+str(i)+'.png'  # Modify this to your desired output path
                cv2.imwrite(output_path, image)


        mode = 1
        if mode==1:
            keypoints, descriptors = cv2.SIFT_create().detectAndCompute(image, None)
        elif mode==2:
            lab_image =cls.preprocess_image(image)
            keypoints, descriptors = cv2.SIFT_create(sigma=2.6, nfeatures=100).detectAndCompute(lab_image,None)

        if debug:
            image_with_keypoints = cv2.drawKeypoints(image, keypoints, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
            cv2.imshow('Image with Keypoints', image_with_keypoints)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return keypoints, descriptors


    @classmethod
    def preprocess_image(cls, image):
        # Apply gamma correction
        gamma = 1.5
        gamma_corrected_image = np.power(image / 255.0, gamma)
        gamma_corrected_image = np.uint8(gamma_corrected_image * 255)
        
        # Apply Canny edge detection
        edges = cv2.Canny(image, threshold1=100, threshold2=200)
        edges_3channel = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
        
        # Combine edges and gamma-corrected image using bitwise OR
        combined_image = cv2.bitwise_or(gamma_corrected_image, edges_3channel)
        
        #cv2.imshow('Edges', combined_image)

        return combined_image
 

    @staticmethod
    def preprocess_image_options(cls, image):

        # Convert image to Lab color space
        lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2Lab)
        
        # Apply histogram equalization to the L channel
        l_channel, a_channel, b_channel = cv2.split(lab_image)
        l_eq = cv2.equalizeHist(l_channel)
        equalized_lab_image = cv2.merge((l_eq, a_channel, b_channel))
        
        # Apply CLAHE to the L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_clahe = clahe.apply(l_channel)
        clahe_lab_image = cv2.merge((l_clahe, a_channel, b_channel))
        
        # Apply Gaussian blur
        blurred_image = cv2.GaussianBlur(image, (5, 5), 0)
        
        # Apply Canny edge detection
        edges = cv2.Canny(image, threshold1=100, threshold2=200)
        
        # Apply adaptive bilateral filter
        bilateral_filtered_image = cv2.bilateralFilter(image, 5, 75, 75)
        
        # Apply gamma correction
        gamma = 1.5
        gamma_corrected_image = np.power(image / 255.0, gamma)
        gamma_corrected_image = np.uint8(gamma_corrected_image * 255)
        
        return equalized_lab_image, clahe_lab_image, blurred_image, edges, bilateral_filtered_image, gamma_corrected_image

   
    @classmethod
    def show_preprocess_image_options(cls, input_image):
        # Preprocess the image using the defined function
        equalized_lab, clahe_lab, blurred, edges, bilateral, gamma_corrected = cls.preprocess_image_options(input_image)
        
        # Display the preprocessed images
        cv2.imshow('Equalized Lab', equalized_lab)
        cv2.imshow('CLAHE Lab', clahe_lab)
        cv2.imshow('Blurred Image', blurred)
        cv2.imshow('Edges', edges)
        cv2.imshow('Bilateral Filter', bilateral)
        cv2.imshow('Gamma Corrected', gamma_corrected)
        
        cv2.waitKey(0)
        cv2.destroyAllWindows()
