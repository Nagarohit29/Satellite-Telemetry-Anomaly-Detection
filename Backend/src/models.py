import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import pickle
import math
import numpy as np

try:
    import dgl
    from dgl.nn import GATConv
    DGL_AVAILABLE = True
except ImportError:
    DGL_AVAILABLE = False

from torch.nn import TransformerEncoder, TransformerDecoder
from torch.nn import TransformerEncoderLayer, TransformerDecoderLayer
from src.dlutils import *
from src.constants import *

torch.manual_seed(1)