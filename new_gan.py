# -*- coding: utf-8 -*-
"""NEW_GAN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1U9raAjsiqDt6pGAOKXUk6KAsbogxEvj0
"""

import numpy as np
import PIL.Image
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
import matplotlib.pyplot as plt
import os 
from IPython.display import Image
import glob
import time
import tqdm
import random

def hms_string(sec_elapsed):
    h = int(sec_elapsed / (60 * 60))
    m = int((sec_elapsed % (60 * 60)) / 60)
    s = sec_elapsed % 60
    return "{}:{:>02}:{:>05.2f}".format(h, m, s)

BUFFER_SIZE = 60000
BATCH_SIZE = 32
NUM_IM = 3000
DIMS = 64
IM_DIR = '/content/drive/My Drive/Colab_Files/1m_faces_91'
SEED_SIZE = 100
EPOCHS = 700
PREVIEW_ROWS = 3
PREVIEW_COLS = 3
PREVIEW_MARGIN = 16
OUT_PATH = '/content/drive/My Drive/Colab_Files/out'
DATA_NAME = ('data_'+str(NUM_IM)+'IMG_'+str(DIMS))
DATA_PATH = os.path.join(OUT_PATH,'data',DATA_NAME)
filelist = glob.glob('/content/drive/My Drive/Colab_Files/1m_faces_91/*.jpg')

isFile = os.path.isdir('/content/drive/My Drive/')  
if isFile:
  print('Drive mounted:')
else:
  print('Drive not mounted')
  from google.colab import drive
  drive.mount('/content/drive')

if os.path.isfile(DATA_PATH+'.npy'):
  print('Loading data from .npy file..')
  data = np.load(DATA_PATH+'.npy')
else:
  print('Loading images into array..')
  data = np.array([np.array(PIL.Image.open(fname).resize((DIMS, DIMS))) for fname in filelist if filelist.index(fname) < NUM_IM])
  # data = np.array([np.array(PIL.Image.open(fname).resize((DIMS, DIMS))) for fname in filelist]) #No limit
  np.save(DATA_PATH, data)

print(np.shape(data))

def normalize(data):
    normalized_data = (data.astype(float)-128) / 128
    return normalized_data

data_norm = normalize(data)
#print(data_norm)
print(np.shape(data_norm))

train_dataset = tf.data.Dataset.from_tensor_slices(data_norm).shuffle(BUFFER_SIZE).batch(BATCH_SIZE)

def make_generator_model():
  model = models.Sequential()

  model.add(layers.Dense(4*4*1024, use_bias=False, input_shape=(SEED_SIZE,)))
  model.add(layers.BatchNormalization())
  model.add(layers.LeakyReLU())
  model.add(layers.Reshape((4, 4, 1024)))
  assert model.output_shape == (None, 4, 4, 1024)

  model.add(layers.Conv2DTranspose(512, (5,5), strides=(2,2), padding='same', use_bias=False))
  assert model.output_shape == (None, 8, 8, 512)
  model.add(layers.BatchNormalization())
  model.add(layers.LeakyReLU())

  model.add(layers.Conv2DTranspose(256, (5,5), strides=(2,2), padding='same', use_bias=False))
  assert model.output_shape == (None, 16, 16, 256)
  model.add(layers.BatchNormalization())
  model.add(layers.LeakyReLU())

  model.add(layers.Conv2DTranspose(128, (5,5), strides=(2,2), padding='same', use_bias=False))
  assert model.output_shape == (None, 32, 32, 128)
  model.add(layers.BatchNormalization())
  model.add(layers.LeakyReLU())

  model.add(layers.Conv2DTranspose(3, (5,5), strides = (2,2), padding ='same', use_bias = False, activation='tanh'))
  assert model.output_shape == (None, 64, 64, 3)

  return model

generator = make_generator_model()
noise = tf.random.normal([1,SEED_SIZE]) # shape is 1, 100
plt.imshow(noise)
generated_image = generator(noise, training = False)
print(tf.shape(generated_image))
plt.imshow(generated_image[0, :, :, 0])

generator.summary()

def make_discriminator_model(image_shape):
    model = models.Sequential()

    model.add(layers.Conv2D(32, kernel_size=3, strides=2, input_shape=image_shape, 
                     padding="same"))
    model.add(layers.LeakyReLU(alpha=0.2))

    model.add(layers.Dropout(0.25))
    model.add(layers.Conv2D(64, kernel_size=3, strides=2, padding="same"))
    model.add(layers.ZeroPadding2D(padding=((0,1),(0,1))))
    model.add(layers.BatchNormalization(momentum=0.8))
    model.add(layers.LeakyReLU(alpha=0.2))

    model.add(layers.Dropout(0.25))
    model.add(layers.Conv2D(128, kernel_size=3, strides=2, padding="same"))
    model.add(layers.BatchNormalization(momentum=0.8))
    model.add(layers.LeakyReLU(alpha=0.2))

    model.add(layers.Dropout(0.25))
    model.add(layers.Conv2D(256, kernel_size=3, strides=1, padding="same"))
    model.add(layers.BatchNormalization(momentum=0.8))
    model.add(layers.LeakyReLU(alpha=0.2))

    model.add(layers.Dropout(0.25))
    model.add(layers.Conv2D(512, kernel_size=3, strides=1, padding="same"))
    model.add(layers.BatchNormalization(momentum=0.8))
    model.add(layers.LeakyReLU(alpha=0.2))

    model.add(layers.Dropout(0.25))
    model.add(layers.Flatten())
    model.add(layers.Dense(1, activation='sigmoid'))
    return model

image_shape = (DIMS, DIMS, 3)
discriminator = make_discriminator_model(image_shape)
decision = discriminator(generated_image)
print(np.shape(generated_image))
print (decision)

# test_image = np.array([np.array(PIL.Image.open(filelist[random.randint(1, NUM_IM)]).resize((DIMS, DIMS))) for fname in filelist if filelist.index(fname) < 1])
# print(np.shape(test_image))
# test_decision = discriminator(test_image)
# print(test_decision)

cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits=True)

def discriminator_loss(real_output, fake_output):
    real_loss = cross_entropy(tf.ones_like(real_output), real_output)
    fake_loss = cross_entropy(tf.zeros_like(fake_output), fake_output)
    total_loss = real_loss + fake_loss
    return total_loss

def generator_loss(fake_output):
    return cross_entropy(tf.ones_like(fake_output), fake_output)

@tf.function
def train_step(images):
  seed = tf.random.normal([BATCH_SIZE, SEED_SIZE])

  with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
    generated_images = generator(seed, training=True)

    real_output = discriminator(images, training=True)
    fake_output = discriminator(generated_images, training=True)

    gen_loss = generator_loss(fake_output)
    disc_loss = discriminator_loss(real_output, fake_output)
    

    gradients_of_generator = gen_tape.gradient(gen_loss, generator.trainable_variables)
    gradients_of_discriminator = disc_tape.gradient(disc_loss, discriminator.trainable_variables)

    generator_optimizer.apply_gradients(zip(gradients_of_generator, generator.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(gradients_of_discriminator, discriminator.trainable_variables))
  return gen_loss,disc_loss

def train(dataset, epochs):
  fixed_seed = np.random.normal(0, 1, (PREVIEW_ROWS * PREVIEW_COLS, SEED_SIZE))
  start = time.time()

  for epoch in range(epochs):
    epoch_start = time.time()

    gen_loss_list = []
    disc_loss_list = []

    for image_batch in dataset:
      t = train_step(image_batch)
      gen_loss_list.append(t[0])
      disc_loss_list.append(t[1])

    g_loss = sum(gen_loss_list) / len(gen_loss_list)
    d_loss = sum(disc_loss_list) / len(disc_loss_list)

    epoch_elapsed = time.time()-epoch_start
    time_elapsed = hms_string(epoch_elapsed)
    print (f'Epoch {epoch+1}, gen loss={g_loss},disc loss={d_loss}, time={time_elapsed}')
    save_images(epoch,fixed_seed)

  elapsed = time.time()-start
  print (f'Training time: {hms_string(elapsed)}')

def save_images(cnt,noise):
  image_array = np.full(( 
      PREVIEW_MARGIN + (PREVIEW_ROWS * (DIMS+PREVIEW_MARGIN)), 
      PREVIEW_MARGIN + (PREVIEW_COLS * (DIMS+PREVIEW_MARGIN)), 3), 
      255, dtype=np.uint8)
  
  generated_images = generator.predict(noise)

  generated_images = 0.5 * generated_images + 0.5

  image_count = 0
  for row in range(PREVIEW_ROWS):
      for col in range(PREVIEW_COLS):
        r = row * (DIMS+16) + PREVIEW_MARGIN
        c = col * (DIMS+16) + PREVIEW_MARGIN
        image_array[r:r+DIMS,c:c+DIMS] = generated_images[image_count] * 255
        image_count += 1

          
  output_path = os.path.join(OUT_PATH,'output')
  if not os.path.exists(output_path):
    os.makedirs(output_path)
  
  filename = os.path.join(output_path,f"train-{cnt}.png")
  im = PIL.Image.fromarray(image_array)
  im.save(filename)

generator_optimizer = tf.keras.optimizers.Adam(1.5e-5, 0.5)
discriminator_optimizer = tf.keras.optimizers.Adam(3e-5, 0.5)

train(train_dataset, EPOCHS)

outlist = glob.glob('/content/drive/My Drive/Colab_Files/out/output_v27/*.png')
gif = np.array([np.array(PIL.Image.open(image)) for image in outlist])
gif = []

for image in outlist:
    frame = PIL.Image.open(image)
    gif.append(frame)

# Save the frames as an animated GIF
gif[0].save(os.path.join(OUT_PATH,'out_v27.gif'),
               save_all=True,
               append_images=gif[1:],
               duration=100,
               loop=0)

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard
# %tensorboard --logdir logs