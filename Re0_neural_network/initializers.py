import numpy as np


def He(shape):
    """
    for ReLu unit, we use He initialization to faster convergence
    Args:
        shape: tuple(out_channels, inchannels)
    Return:
        matirx(out_channels, inchannels)
    """
    return np.random.randn(*shape) * np.sqrt(2. / shape[-1])
