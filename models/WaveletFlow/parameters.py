from models.WaveletFlow import model
import torch
import torch.optim as optim
from models.WaveletFlow.conditionNet import ConditioningNetwork
from models.model import Parameters


class WaveletFlowParamters(Parameters):
    def __init__(self, imShape, device):
        super().__init__(imShape, device)
        self.modelName = 'waveletflow'
        self.model = model.WaveletFlow(self).to(device)
        self.conditionNetwork = ConditioningNetwork()
        self.spatialBiasing = [False, False, False, False, False, False, False]  # not implemented yet
        self.stepsPerResolution = [8, 8, 16, 16, 16, 16, 16]
        self.nLevels = 6
        self.kernel = 3
        self.baseLevel = 0
        self.partialLevel = -1
        self.convWidth = [128, 128, 128, 128, 128, 256, 256]
        self.coupling = "affine"
        self.n_res_blocks = 3
        self.lr = 1e-3
        self.weight_decay = 1e-3
        self.lr_lambda = lambda epoch: min(1.0, (epoch + 1) / self.warmup)  # noqa
        self.zero_use_logscale = True
        self.normalize = True
        self.actNormScale = 3.0
        self.zero_logscale_factor = 3.0
        self.optimizer = optim.Adamax(self.model.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        self.scheduler = torch.optim.lr_scheduler.LambdaLR(self.optimizer, lr_lambda=self.lr_lambda)

        # for param in self.model.parameters():
        #     param.requires_grad = True


