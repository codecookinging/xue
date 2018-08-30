import random
import numpy as np
import pandas as pd
from collections import Counter
import cv2 as cv
from tqdm import tqdm
import multiprocessing
import datetime
import keras.backend as K
import tensorflow as tf

from keras.layers import *
from keras.models import *
from keras.optimizers import *
from keras.applications import *
from keras.regularizers import l2
from keras.preprocessing.image import *
from keras import backend as K
from keras.utils import multi_gpu_model

import os
os.environ['CUDA_VISIBLE_DEVICES'] = '6'
n_gpus = len(os.environ['CUDA_VISIBLE_DEVICES'].split(','))

#毛斑擦洞扎洞毛洞缺经跳花油／污渍

train_path=['../round1_answer_a','../round1_answer_b','../round1_train_part1','../round1_train_part2','../round1_train_part3']
img_path=[]
lbl_list=[]
class_list=[]

for part_index in train_path:
    class_path_list=os.listdir(part_index)
    for class_index in class_path_list:
        img_path_list=os.listdir(os.path.join(part_index,class_index))
        for img_index in img_path_list:
            if img_index[-3:]=='jpg':
                img_path.append(os.path.join(part_index,class_index,img_index))
                if class_index=='正常':
                    lbl_list.append([1,0,0,0,0,0,0,0,0,0,0])
                    class_list.append(0)
                if class_index=='扎洞':
                    lbl_list.append([0,1,0,0,0,0,0,0,0,0,0])
                    class_list.append(1)
                if class_index=='毛斑':
                    lbl_list.append([0,0,1,0,0,0,0,0,0,0,0])
                    class_list.append(2)
                if class_index=='擦洞':
                    lbl_list.append([0,0,0,1,0,0,0,0,0,0,0])
                    class_list.append(3)
                if class_index=='毛洞':
                    lbl_list.append([0,0,0,0,1,0,0,0,0,0,0])
                    class_list.append(4)
                if class_index=='织稀':
                    lbl_list.append([0,0,0,0,0,1,0,0,0,0,0])
                    class_list.append(5)
                if class_index=='吊经':
                    lbl_list.append([0,0,0,0,0,0,1,0,0,0,0])
                    class_list.append(6)
                if class_index=='缺经':
                    lbl_list.append([0,0,0,0,0,0,0,1,0,0,0])
                    class_list.append(7)
                if class_index == '跳花':
                    lbl_list.append([0, 0, 0, 0, 0, 0, 0, 0, 1,0,0])
                    class_list.append(8)
                if class_index == '油渍' or class_index == '污渍':
                    lbl_list.append([0, 0, 0, 0, 0, 0, 0, 0, 0,1,0])
                    class_list.append(9)
                elif class_index not in ['正常', '扎洞', '毛斑', '擦洞', '织稀', '吊经', '缺经', '跳花', '油渍', '污渍', '毛洞']:
                    lbl_list.append([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])
                    class_list.append(10)
print('positive number:',class_list.count(0))

print(' number:',class_list.count(1))
print(' number:',class_list.count(2))
print(' number:',class_list.count(3))
print(' number:',class_list.count(4))
print(' number:',class_list.count(5))
print(' number:',class_list.count(6))
print(' number:',class_list.count(7))
print(' number:',class_list.count(8))
print(' number:',class_list.count(9))
print(' number:',class_list.count(10))

print('image number:',len(img_path))
print('label number:',len(lbl_list))

n=len(img_path)
width=331

index_list=list(range(n))
random.shuffle(index_list)
img_path_shuf=[]
lbl_list_shuf=[]
class_list_shuf=[]
for i,index in enumerate(index_list):
    img_path_shuf.append(img_path[index])
    lbl_list_shuf.append(lbl_list[index])
    class_list_shuf.append(class_list[index])
img_path=img_path_shuf
lbl_list=lbl_list_shuf
class_list=class_list_shuf
lbl_list=np.array(lbl_list)

def read_img(index):
    return index, cv.resize(cv.imread(img_path[index]),(width,width),interpolation=cv.INTER_AREA)
img_list = np.zeros((n, width, width, 3), dtype=np.uint8)
with multiprocessing.Pool(16) as pool:
    with tqdm(pool.imap_unordered(read_img, range(n)), total=n) as pbar:
        for i, img in pbar:
            img_list[i] = img[:,:,::-1]

n_train = int(n*0.95)

X_train = img_list[:n_train]
X_valid = img_list[n_train:]
y_train = lbl_list[:n_train]
y_valid = lbl_list[n_train:]
print(len(X_train),len(X_valid))
print(len(y_train),len(y_valid))


class Generator():
    def __init__(self, X, y, batch_size=8, aug=False):
        def generator():
            idg = ImageDataGenerator(horizontal_flip=True,
                                     vertical_flip=True,
                                     rotation_range=20,
                                     zoom_range=0.1,
                                     shear_range = 0.3
                                    )
            while True:
                for i in range(0, len(X), batch_size):
                    X_batch = X[i:i+batch_size].copy()
                    y_barch = y[i:i+batch_size].copy()
                    if aug:
                        for j in range(len(X_batch)):
                            X_batch[j] = idg.random_transform(X_batch[j])
                    yield X_batch, y_barch
        self.generator = generator()
        self.steps = len(X) // batch_size + 1

gen_train = Generator(X_train, y_train, batch_size=8, aug=True)

def acc(y_true, y_pred):
    index = tf.reduce_any(y_true > 0.5, axis=-1)
    res = tf.equal(tf.argmax(y_true, axis=-1), tf.argmax(y_pred, axis=-1))
    index = tf.cast(index, tf.float32)
    res = tf.cast(res, tf.float32)
    return tf.reduce_sum(res * index) / (tf.reduce_sum(index) + 1e-7)


base_model = NASNetLarge(weights='imagenet', input_shape=(width, width, 3), include_top=False, pooling='avg')

input_tensor = Input((width, width, 3))
x = input_tensor
x = Lambda(nasnet.preprocess_input)(x)
x = base_model(x)
x = Dropout(0.5)(x)
x = Dense(11, activation='softmax', name='softmax')(x)

model = Model(input_tensor, x)




model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['acc'])

model.compile(optimizer=Adam(1e-4), loss='categorical_crossentropy', metrics=[acc])
model.fit_generator(gen_train.generator, steps_per_epoch=gen_train.steps, epochs=1, validation_data=(X_valid, y_valid))
model.compile(optimizer=Adam(1e-5), loss='categorical_crossentropy', metrics=[acc])
model.fit_generator(gen_train.generator, steps_per_epoch=gen_train.steps, epochs=1, validation_data=(X_valid, y_valid))
model.compile(optimizer=Adam(1e-6), loss='categorical_crossentropy', metrics=[acc])
model.fit_generator(gen_train.generator, steps_per_epoch=gen_train.steps, epochs=10, validation_data=(X_valid, y_valid))
model.compile(optimizer=Adam(1e-7), loss='categorical_crossentropy', metrics=[acc])
model.fit_generator(gen_train.generator, steps_per_epoch=gen_train.steps, epochs=5, validation_data=(X_valid, y_valid))
#model.compile(optimizer=Adam(1e-8), loss='categorical_crossentropy', metrics=[acc])
#model.fit_generator(gen_train.generator, steps_per_epoch=gen_train.steps, epochs=5, validation_data=(X_valid, y_valid))

y_pred = model.predict(X_valid, batch_size=32, verbose=1)


import csv


print(y_pred)

pred=y_pred.argmax(axis=-1)
label=y_valid.argmax(axis=-1)


cnt=0
for i,lbl in enumerate(label):
    if lbl==pred[i]:
        cnt=cnt+1
acc=cnt/len(label)
print('Valid acc:',acc)

test_path='../round2_test_a_20180809'
test_img_name=os.listdir(test_path)
n_test=len(test_img_name)

def read_img_test(index):
    return index, cv.resize(cv.imread(os.path.join(test_path,test_img_name[index])),(width,width),interpolation=cv.INTER_AREA)

test_img_list = np.zeros((n_test, width, width, 3), dtype=np.uint8)

with multiprocessing.Pool(12) as pool:
    with tqdm(pool.imap_unordered(read_img_test, range(n_test)), total=n_test) as pbar:
        for i, img in pbar:
            test_img_list[i] = img[:,:,::-1]



y_pred = model.predict(test_img_list, batch_size=32, verbose=1)



#pred=y_pred.argmax(axis=-1)
print(y_pred)
#y_pred=max(y_pred)

classes =['norm','defect_1','defect_2','defect_3','defect_4','defect_5','defect_6','defect_7','defect_8','defect_9','defect_10']

class_to_id=dict(zip(list(range(11)),classes))




fileHeader = ['filename|defect','probability']

with open('round2/full4.csv','w') as f:

    writer=csv.writer(f)
    writer.writerow(fileHeader)

    for i in range(len(test_img_name)):
        for j in range(len(y_pred[i])):
            writer.writerow(['{}|{}'.format(test_img_name[i],class_to_id[j]), y_pred[i][j]])







print('csv saved!')

model.save('round2/model_nasnet2.h5')




print('model saved!')
