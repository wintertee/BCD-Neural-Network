import numpy as np
from functools import reduce
import math


class Layer:
    def __init__(self):
        raise NotImplementedError

    def forward(self):
        raise NotImplementedError

    def backward(self):
        raise NotImplementedError


class Dense(Layer):
    def __init__(self, in_channels, out_channels, activation=None, initializer=None):

        # initialize properties
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.activation = activation

        # initialize parameters
        self.P = {}  # parameters
        self.G = {}  # gradients
        if initializer:
            self.P['w'] = initializer((out_channels, in_channels))
        else:
            self.P['w'] = np.ones((out_channels, in_channels))
        self.P['b'] = np.zeros((out_channels, 1))

    def forward(self, x):
        # 先把 x 分解成 batch_size 个矩阵 (in ,1)
        # 分别计算a
        # 最后通过 np.stack 把 a 堆叠成 (batch_size, out, 1)
        self.x = x
        self.batch_size = x.shape[0]
        a = []
        for i in range(self.batch_size):
            x_single = x[i]
            self.z = np.dot(self.P['w'], x_single) + self.P['b']
            if self.activation is None:
                a.append(self.z)
            else:
                a.append(self.activation.forward(self.z))
        self.a = np.stack(a)
        return self.a

    def backward(self, dL_da):
        if self.activation is None:
            da_dz = np.ones((self.batch_size, self.out_channels, 1))
        else:
            da_dz = self.activation.backward(self.a)

        dL_dz = []
        dL_dx = []
        G_w = []

        for i in range(self.batch_size):
            dL_dz.append(dL_da[i] * da_dz[i])  # NOTE * not np.dot here!
            G_w.append(np.dot(dL_dz[i], self.x[i].T))  # dL_dw
            dL_dx.append(np.dot(self.P['w'].T, dL_dz[i]))

        G_b = dL_dz
        self.G['w'] = np.mean(G_w, axis=0)
        self.G['b'] = np.mean(G_b, axis=0)

        return np.stack(dL_dx)  # NOTE x is the `a` in the last layer


class Flatten(Layer):
    def __init__(self):
        self.P = {}
        self.G = {}
        self.P['w'] = np.array([])
        self.P['b'] = np.array([])
        self.G['w'] = np.array([])
        self.G['b'] = np.array([])

    def forward(self, x):
        self.original_shape = x.shape
        size = x.size // x.shape[0]
        return x.reshape(x.shape[0], size, 1)

    def backward(self, dL_da):
        return dL_da.reshape(self.original_shape)


class Conv2d(Layer):
    def __init__(self, input_image, output_channels, kernel_size, padding, batchsize, activation=None):

        # initialize properties
        self.input_image = input_image
        self.input_channels = input_image[-1]
        self.output_channels = output_channels
        self.kernel_size = kernel_size
        self.padding = padding
        self.activation = activation
        self.batchsize = batchsize

        self.eta = np.zeros(
            (batchsize, input_image[1] - kernel_size + 1, input_image[1] - kernel_size + 1, self.output_channels))

        # initialize parameters
        self.P = {}
        self.G = {}

        weights_scale = math.sqrt(reduce(lambda x, y: x * y, input_image) / self.output_channels)
        self.P['w'] = np.random.standard_normal(
            (kernel_size, kernel_size, self.input_channels, self.output_channels)) / weights_scale
        self.P['b'] = np.random.standard_normal(self.output_channels) / weights_scale

        self.G['w'] = np.zeros(self.P['w'].shape)
        self.G['b'] = np.zeros(self.P['b'].shape)
        self.output_size = self.eta.shape

    def im2col(self, image, kernel_size):
        image_col = []
        for i in range(0, image.shape[1] - kernel_size + 1, 1):
            for j in range(0, image.shape[2] - kernel_size + 1, 1):
                col = image[:, i:i + kernel_size, j:j + kernel_size, :].reshape([-1])
                image_col.append(col)
        image_col = np.array(image_col)

        return image_col

    def forward(self, x):
        col_weights = self.P['w'].reshape([-1, self.output_channels])
        self.col_image = []
        conv_out = np.zeros(self.eta.shape)
        for i in range(self.batchsize):
            img_i = x[i][np.newaxis, :]
            self.col_image_i = self.im2col(img_i, self.kernel_size)
            conv_out[i] = np.reshape(np.dot(self.col_image_i, col_weights) + self.P['b'], self.eta[0].shape)
            self.col_image.append(self.col_image_i)
        self.col_image = np.array(self.col_image)
        if self.activation is None:
            return conv_out
        else:
            return self.activation.forward(conv_out)

    def backward(self, dL_da):

        col_delta = np.reshape(dL_da, [self.batchsize, -1, dL_da.shape[3]])
        for i in range(self.batchsize):
            self.G['w'] += np.dot(self.col_image[i].T, col_delta[i]).reshape(self.G['w'].shape)
        self.G['b'] += np.sum(col_delta, axis=(0, 1))

        pad_eta = np.pad(self.eta, ((0, 0), (self.kernel_size - 1, self.kernel_size - 1),
                                    (self.kernel_size - 1, self.kernel_size - 1), (0, 0)),
                         'constant',
                         constant_values=0)

        flip_weights = np.flipud(np.fliplr(self.P['w']))
        flip_weights = flip_weights.swapaxes(2, 3)
        col_flip_weights = flip_weights.reshape([-1, self.input_channels])
        col_pad_eta = np.array(
            [self.im2col(pad_eta[i][np.newaxis, :], self.kernel_size) for i in range(self.batchsize)])
        next_eta = np.dot(col_pad_eta, col_flip_weights)
        next_eta = np.reshape(next_eta, (self.batchsize, self.input_image[1], self.input_image[2], self.input_image[3]))
        return next_eta


class MaxPool2d(Layer):
    def __init__(self, input_size, input_channel, channel_number, kernel_size, batchsize, stride=-1):  # 默认步长为池化核尺寸
        self.input_size = input_size
        self.channel_number = channel_number
        self.kernel_size = kernel_size
        self.index = np.zeros((input_channel))
        if stride == -1:
            self.stride = kernel_size
        else:
            self.stride = stride
        self.output_size = (input_size - kernel_size) // self.stride + 1
        self.batchsize = batchsize
        self.output_matrix = np.zeros((self.batchsize, self.output_size, self.output_size, self.channel_number))
        self.input_channel = input_channel

        self.P = {}
        self.G = {}
        self.P['w'] = np.array([])
        self.P['b'] = np.array([])
        self.G['w'] = np.array([])
        self.G['b'] = np.array([])
        self.delta_matrix = []

    def forward(self, input_image):
        self.input_image = input_image
        for k in range(self.batchsize):
            for d in range(self.channel_number):
                for i in range(self.output_size):
                    for j in range(self.output_size):
                        self.output_matrix[k, i, j, d] = self.get_patch(input_image[k, :, :, d], i, j, self.kernel_size,
                                                                        self.kernel_size, self.stride).max()
        return self.output_matrix

    def backward(self, dL_da):
        input_image = self.input_image
        # N = 1 / (1 + (self.input_size - self.kernel_size) // self.stride)**2
        self.delta_matrix = np.zeros((self.batchsize, self.input_size, self.input_size, self.input_channel))
        for m in range(self.batchsize):
            for d in range(self.channel_number):
                for i in range(self.output_size):
                    for j in range(self.output_size):
                        patch_image = self.get_patch(input_image[m, :, :, d], i, j, self.kernel_size, self.kernel_size,
                                                     self.stride)
                        k, l = self.get_max_index(patch_image)  # noqa: E741
                        self.delta_matrix[m, i * self.stride + k, j * self.stride + l, d] += dL_da[m, i, j, d]
        return self.delta_matrix

    def get_max_index(self, array):
        max_i = 0
        max_j = 0
        max_value = 0
        for i in range(array.shape[0]):
            for j in range(array.shape[1]):
                if array[i, j] > max_value:
                    max_value = array[i, j]
                    max_i, max_j = i, j
        return max_i, max_j

    def get_patch(self, input_array, i, j, filter_width, filter_height, stride):
        start_i = i * stride
        start_j = j * stride
        if input_array.ndim == 2:
            input_array_conv = input_array[start_i:start_i + filter_height, start_j:start_j + filter_width]
            return input_array_conv
        elif input_array.ndim == 3:
            input_array_conv = input_array[:, start_i:start_i + filter_height, start_j:start_j + filter_width]
            return input_array_conv
