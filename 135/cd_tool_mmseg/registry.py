# Copyright (c) Remote Sensing Change Detection Team. All rights reserved.

from mmcv.utils import Registry

BACKBONES = Registry('backbone')
NECKS = Registry('neck')
HEADS = Registry('head')
LOSSES = Registry('loss')
SEGMENTORS = Registry('segmentor')
DISTILLERS = Registry('distiller')
