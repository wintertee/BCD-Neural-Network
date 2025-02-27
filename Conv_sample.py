from Re0_neural_network import activations, initializers, layers, losses, models, optimizers, metrics

import numpy as np
import matplotlib.pyplot as plt

# load dataset
mnist = np.load('datasets/mnist.npz')
train_images = mnist['train_images']
train_labels = mnist['train_labels']
test_images = mnist['test_images']
test_labels = mnist['test_labels']

# add 1 dim to the last axis of the image
train_images = train_images.reshape(*(train_images.shape), 1).astype(float)
test_images = test_images.reshape(*(test_images.shape), 1).astype(float)

# normalisation
train_images /= 255
test_images /= 255

# one-hot encode
targets = train_labels.reshape(-1)
train_labels = np.eye(10)[targets].reshape(60000, 10, 1)

targets = test_labels.reshape(-1)
test_labels = np.eye(10)[targets].reshape(10000, 10, 1)

# model

batch_size = 60

model = models.Sequential()
model.append(layers.Conv2d(train_images.shape, 2, 3, 1, batch_size, activations.relu()))
model.append(layers.MaxPool2d(26, 2, 2, 2, batch_size))
model.append(layers.Flatten())
model.append(layers.Dense(338, 64, activations.relu, initializers.He))
model.append(layers.Dense(64, 10, activations.softmax, initializers.He))
model.build()

model.config(optimizer=optimizers.SGD, loss=losses.Crossentropy, lr=0.01, metric=metrics.categorical_accuracy)

epoch = 10

train_losses, train_metrics, val_losses, val_metrics = model.fit(train_images, train_labels, test_images, test_labels, epoch, batch_size, verbose=2, freq=1)

# visualize
plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.plot(range(epoch), train_losses, label='train')
plt.plot(range(epoch), val_losses, label='val')
plt.title('Training and validation loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(range(epoch), train_metrics, label='train')
plt.plot(range(epoch), val_metrics, label='val')
plt.title('Training and validation accuracy')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.legend()
plt.grid(True)

plt.show()
