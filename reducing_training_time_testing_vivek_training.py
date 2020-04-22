# -*- coding: utf-8 -*-
"""reducing_training_time_testing_vivek_training.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1zWrS3ag-69ygFmaSS35bHb47v7LGRtIY

<a href="https://colab.research.google.com/github/Jeff-AB/ECE542FinalProject/blob/jeff-development/ECE542FinalProject.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# ECE 542 Final Project

## Model Summary

<img src=https://ronjian.github.io/assets/Mask-RCNN/mask-rcnn.png width="500">

# References

# Mask R CNN
1. https://www.analyticsvidhya.com/blog/2019/07/computer-vision-implementing-mask-r-cnn-image-segmentation/

2. https://machinelearningmastery.com/how-to-perform-object-detection-in-photographs-with-mask-r-cnn-in-keras/

3. https://engineering.matterport.com/splash-of-color-instance-segmentation-with-mask-r-cnn-and-tensorflow-7c761e238b46 (Best)
"""
# Commented out IPython magic to ensure Python compatibility.
# %tensorflow_version 1.x
import tensorflow
import os
import sys
import random
import math
import numpy as np
import skimage.io
import matplotlib
import matplotlib.pyplot as plt

# Google Colab or Local Notebook Settings
colab_notebook = False

data_dir = None
aug_data_dir = None


data_dir = '/content/drive/My Drive/ECE 542 Final Project/gtFine'

train_dir = '/content/drive/My Drive/ECE 542 Final Project/gtFine/train'
val_dir = '/content/drive/My Drive/ECE 542 Final Project/gtFine/val'

CITI_ROOT = os.path.abspath('/content/drive/My Drive/ECE 542 Final Project/cityscapesScripts/')
MASK_ROOT = os.path.abspath('/content/drive/My Drive/ECE 542 Final Project/Mask_RCNN/')


sys.path.append(MASK_ROOT)
sys.path.append(CITI_ROOT)

# Commented out IPython magic to ensure Python compatibility.
# Root directory of the project
ROOT_DIR = os.path.abspath('/content/drive/My Drive/ECE 542 Final Project/Mask_RCNN/')

print(ROOT_DIR)

# Import Mask RCNN
sys.path.append(ROOT_DIR)  # To find local version of the library
from mrcnn import utils
import mrcnn.model as modellib
from mrcnn import visualize
# Import COCO config
sys.path.append(os.path.join(ROOT_DIR, 'samples/coco/'))  # To find local version
import coco


# Directory to save logs and trained model
MODEL_DIR = os.path.join(ROOT_DIR, 'logs')

# Local path to trained weights file
COCO_MODEL_PATH = os.path.join(ROOT_DIR, 'mask_rcnn_coco.h5')
# Download COCO trained weights from Releases if needed
if not os.path.exists(COCO_MODEL_PATH):
    utils.download_trained_weights(COCO_MODEL_PATH)

# Directory of images to run detection on
IMAGE_DIR = os.path.abspath('/content/drive/My Drive/ECE 542 Final Project/cityscapes-data/leftImg8bit_trainvaltest/leftImg8bit')

from mrcnn.config import Config

GPU_COUNT = 1
IMAGES_PER_GPU = 2
LEARNING_RATE = 0.0001
NAME = 'cityscape'
NUM_CLASSES = 35 #1+34 # Background (inherited from utils.Dataset) + FG classes (listed below)
WEIGHT_DECAY = 0.0001

class TrainingConfig(Config):
    # TO-OPT: Set batch size to 20 by default.
    GPU_COUNT = GPU_COUNT
    IMAGES_PER_GPU = IMAGES_PER_GPU
    LEARNING_RATE = LEARNING_RATE
    NAME = NAME
    NUM_CLASSES = NUM_CLASSES
    WEIGHT_DECAY = WEIGHT_DECAY
    IMAGE_MIN_DIM = 256
    IMAGE_MAX_DIM = 256

config = TrainingConfig()
config.display()

class_names = ['ego vehicle', 'rectification border', 'out of roi', 'static', 'dynamic', 'ground', 'road', 'sidewalk', 'parking', 'rail track', 'building', 'wall', 'fence',
               'guard rail', 'bridge', 'tunnel', 'pole', 'polegroup', 'traffic light', 'traffic sign', 'vegetation', 'terrain', 'sky', 'person', 'rider', 'car', 'truck', 'bus', 'caravan',
               'trailer', 'train', 'motorcycle', 'bicycle', 'license plate']

import numpy as np
import json
import cv2
import matplotlib.pyplot as plt
import PIL.ImageDraw as ImageDraw
import PIL.Image as Image
import os
import random

from tqdm import tqdm    
from mrcnn.utils import Dataset
from cityscapesscripts.helpers.csHelpers import getCoreImageFileName

class CityscapesSegmentationDataset(Dataset):
    
    def load_cityscapes(self, root_directory, subset):

        # add class names
        class_names = ['ego vehicle', 'rectification border', 'out of roi', 'static', 'dynamic', 'ground', 'road', 'sidewalk', 'parking', 'rail track', 'building', 'wall', 'fence',
               'guard rail', 'bridge', 'tunnel', 'pole', 'polegroup', 'traffic light', 'traffic sign', 'vegetation', 'terrain', 'sky', 'person', 'rider', 'car', 'truck', 'bus', 'caravan',
               'trailer', 'train', 'motorcycle', 'bicycle', 'license plate']
        
        for i, name in enumerate(class_names[:-1]):
            self.add_class('cityscape', i, name)
        
        # license plate has id as -1
        self.add_class('cityscape',-1,class_names[-1])

        # Write out locations for annotations and images
        # self.data_dir: location for json annotations
        # image_dir: location for image path assignment
        if subset == 'train':
            self.data_dir = os.path.join(root_directory, 'train')
            image_dir = os.path.join(IMAGE_DIR, 'train')
        elif subset == 'val':
            self.data_dir = os.path.join(root_directory, 'val')
            image_dir = os.path.join(IMAGE_DIR, 'val')
        elif subset == 'test':
            self.data_dir = os.path.join(root_directory, 'test')
            image_dir = os.path.join(IMAGE_DIR, 'test')
        else:
            raise Exception('No valid subset provided')

        # Create set to prevent redundant image_id's (string, partial file name)
        image_id_set = set()
        for root, dirs, filenames in os.walk(self.data_dir):
          for filename in filenames:
              image_id = getCoreImageFileName(filename)
              image_id_set.add(image_id)
        
        # Add unique image id's to dataset
        for image_id in image_id_set:
          city = image_id.split('_')[0] # First element in list should be city
          path = os.path.join(image_dir, city, image_id + '_leftImg8bit.png')
          self.add_image(source = "cityscape", 
          image_id=image_id,
          path=path)
            
        #print('---------------')
        #print(self._image_ids)
        #print('---------------')
        #print(len(self._image_ids))
        # return self._image_ids
        #image_id = random.choice(self._image_ids)
        #print("Sample image: %s" % image_id)

    def load_mask(self, image_id):
        '''
        Loads mask corresponding to an image id
        
        image_id: the unique id of the form city_sequenceNb_frame_Nb
        
        returns a bool array of masks and a list of class ids
        The polygons are extracted from the json files and constructed into a binary image
        using PIL. 
        '''
        
        # Retrieve available image metadata from dataset
        image_info = self.image_info[image_id]
        image_name = image_info['id']

        # Fetch and process the required metadata for the mask 
        city = image_name.split('_')[0] # First element in list should be city
        annotation_path = os.path.join(os.path.join(self.data_dir, city), image_name + '_gtFine_polygons.json')
        ann_dict = {}
        
        with open(annotation_path) as annotation:
            ann_dict = json.load(annotation)
        masks = []
        class_ids = []
        
        for obj in tqdm(ann_dict['objects']):
            # Must search list of dictionaries to find class_id (int) assosciated with class_name (string)
            class_name = obj['label']
            if class_name.endswith('group'):  # Some classes can be grouped if no clear boundary can be seen
              class_name = class_name[:-5]    # Remove group from the class name and continue as if one object
              #print('\nGroup removed from class %s\n' % class_name)
              
            #class_dict = next(item for item in self.class_info if item["name"] == class_name)
            class_dict = list(filter(lambda class_info_item: class_info_item['name'] == class_name, self.class_info))
            if (len(class_dict) == 0):
              print('Class %s not handled by current software\n' % class_name)
            else:
              class_ids.append(class_dict[0]['id'])

            # Generate bitmask skeleton for polygon drawing
            mask = Image.new(mode = '1', size = (ann_dict['imgWidth'], ann_dict['imgHeight']))
            draw = ImageDraw.Draw(mask)
            
            # Retrieve bitmask polygon info from JSON
            try:
                points = obj['polygon']
            except:
                print('no polygons for {}'.format(obj['label']))
            
            # PIL expects a tuple of tuples for points
            points = [tuple(coords) for coords in points]
            points = tuple(points)
            
            # Draw bitmask polygon from points
            draw.polygon((points), fill=1)
            masks.append(mask)

        if (class_ids):
          # Stack masks and class_ids
          masks = np.stack(masks, axis=2).astype(np.bool)
          class_ids = np.array(class_ids, dtype=np.int32)
          return masks, class_ids
        else:
          # Return empty mask
          return super(CityscapesSegmentationDataset, self).load_mask(image_id)

# csds = CityscapesSegmentationDataset()
# csds.load_cityscapes(data_dir, 'val')
# masks, class_ids = csds.load_mask('frankfurt_000000_000294')
# num_instances = len(class_ids)
# select = random.randint(0,num_instances - 1)

# print(class_ids[select])
# fig=plt.figure(figsize=(9, 8), dpi= 80, facecolor='w', edgecolor='k')
# plt.imshow(np.asarray(masks[select]), cmap=plt.cm.gray)

#Training dataset.
dataset_train = CityscapesSegmentationDataset()
dataset_train.load_cityscapes(data_dir, 'train')
dataset_train.prepare()


# Validation dataset

dataset_val = CityscapesSegmentationDataset()
dataset_val.load_cityscapes(data_dir, 'val')
dataset_val.prepare()

print(len(dataset_train.image_ids))
print(dataset_train.class_info)

print("Image IDs: {}".format(dataset_train.image_ids))
print("Image Count: {}".format(len(dataset_train._image_ids)))
print("Class Count: {}".format(dataset_train.num_classes))

# Create model object in training mode.
model = modellib.MaskRCNN(mode="training", model_dir=MODEL_DIR, config=config)

# Load weights trained on MS-COCO, excepting areas for training
# We can exclude the bounding box layers for now, but they will
# be useful for interpreting our images for now
model.load_weights(COCO_MODEL_PATH, by_name=True, exclude=["mrcnn_bbox_fc",
                                                           "mrcnn_bbox",
                                                           "mrcnn_mask",
                                                           "mrcnn_class_logits"])

import keras
keras.__version__

model.keras_model.metrics_tensors = []

model.train(dataset_train, 
            dataset_train,
            learning_rate=LEARNING_RATE,
            epochs=5,
            layers='heads')

"""# Model Setup

Run this cell in order to setup the file structure that Mask R-CNN will expect to use. This includes MODEL_DIR for saving models, 

*   `MODEL_DIR`: directory to write trained models to
*   `COCO_MODEL_PATH`: directory to read trained models in from
*   `IMAGE_DIR`: directory root for image data (training and testing)

create config class based on application.
"""

# Create model object in training mode.
model = modellib.MaskRCNN(mode="training", model_dir=MODEL_DIR, config=config)

# Load weights trained on MS-COCO, excepting areas for training
# We can exclude the bounding box layers for now, but they will
# be useful for interpreting our images for now
model.load_weights(COCO_MODEL_PATH, by_name=True, exclude=["mrcnn_bbox_fc",
                                                           "mrcnn_bbox",
                                                           "mrcnn_mask",
                                                           "mrcnn_class_logits"])

"""# Dataset organization

TODO: We read in data using the following structure. This will allow us to have annotations stored in a JSON format in one directory with images stored in another with train and val subset labels respectively. 

```
DATA_DIR
│
└───annotations
│   │   bdd100k_labels_images_<subset><year>.json
│   
└───<subset><year>
    │   image021.jpeg
    │   image022.jpeg
```

# Model Training

Run these cells in order to train the Mask R-CNN model's mask and ROI-related layers (excludes CNN backbone layers).
"""

# Training dataset.
dataset_train = DeepDriveDataset()
dataset_train.load_deep_drive(data_dir + 'images/train/')
dataset_train.prepare()

# Validation dataset
dataset_val = DeepDriveDataset()
dataset_val.load_deep_drive(data_dir + 'images/val/')
dataset_val.prepare()

model.train(dataset_train, 
            dataset_val,
            learning_rate=LEARNING_RATE,
            epochs=5,
            layers='heads',
            augmentation=None)

# Retrieve history for plotting loss and accuracy per epoch
history = model.keras_model.history.history

# Accuracy plot config
plt.subplot(1, 2, 1)
plt.plot(history.history['categorical_accuracy'])
plt.plot(history.history['val_categorical_accuracy'])
plt.title('Training and Validation Accuracy vs. Epoch')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend(('Training', 'Validation'))
plt.grid()

# Loss plot config
plt.subplot(1, 2, 2)
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('Training and Validation Loss vs. Epoch')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend(('Training', 'Validation'))
plt.grid()

# Display plot
plt.show()

"""# Model Evaluation

Run these cells in order to receive an evaluation on a test image. First, the new model is selected from among the saved checkpoint models. Then, a configuration is set for inference (the same as before). Then a sample image is labeled using the Berkeley Deep Drive classes.
"""

# select trained model 
dir_names = next(os.walk(model.model_dir))[1]
key = config.NAME.lower()
dir_names = filter(lambda f: f.startswith(key), dir_names)
dir_names = sorted(dir_names)

if not dir_names:
    import errno
    raise FileNotFoundError(
        errno.ENOENT,
        "Could not find model directory under {}".format(self.model_dir))
    
fps = []
# Pick last directory
for d in dir_names: 
    dir_name = os.path.join(model.model_dir, d)
    # Find the last checkpoint
    checkpoints = next(os.walk(dir_name))[2]
    checkpoints = filter(lambda f: f.startswith("mask_rcnn"), checkpoints)
    checkpoints = sorted(checkpoints)
    if not checkpoints:
        print('No weight files in {}'.format(dir_name))
    else:
        checkpoint = os.path.join(dir_name, checkpoints[best_epoch])
        fps.append(checkpoint)

model_path = sorted(fps)[-1]
print('Found model {}'.format(model_path))

# Recreate the model in inference mode
model = modellib.MaskRCNN(mode='inference', 
                          config=config,
                          model_dir=ROOT_DIR)

model.load_weights(COCO_MODEL_PATH, by_name=True)

# Load trained weights (fill in path to trained weights here)
assert model_path != "", "Provide path to trained weights"
print("Loading weights from ", model_path)
model.load_weights(model_path, by_name=True)

# Load a random image from the images folder
root, dirs, file_names = next(os.walk(IMAGE_DIR))
print(file_names)
image = skimage.io.imread(os.path.join(IMAGE_DIR, random.choice(file_names)))

# Run detection
results = model.detect([image], verbose=1)

# Visualize results
r = results[0]
visualize.display_instances(image, r['rois'], r['masks'], r['class_ids'], 
                            class_names, r['scores'])