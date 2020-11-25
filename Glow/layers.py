import math
import torch
import torch.nn as nn
from layers import SqueezeLayer

class FlowUnit(nn.Module):
    def __init__(self, inUnits, hiddenUnits, actNormScale, perm, coupling, LU):
        super().__init__()
        self.coupling = coupling
        self.actnorm - Act

class MultiScaleFlow(nn.Module):
    def __init__(self, imageDim, hiddenUnits, K, L, actNormScale, perm, coupling, LU):
        super().__init__()

        self.layers = nn.ModuleList() # properly registered list of modules
        self.outputDim = []

        self.K = K
        self.L = L
        H, W, C = imageDim

        # Build squeeze --> K x flow --> split loop L times
        for i in range(L):
            # Squeeze
            C, H, W = C * 4, H // 2, W // 2  # new dimensions
            self.layers.append(SqueezeLayer(factor=2))
            self.output_shapes.append([-1, C, H, W])

            # Flow
            for _ in range(K):
                self.layers.append(FlowStep())

class GLOW(nn.Module):
    # imageDim: Dimensions of input images
    # hiddenUnits: Number of units in a single hidden layer
    # K: Depth (number of actNorm -> 1x1 conv -> affine coupling) of a single flow
    # L: Levels, or number of times (L-1) the sqeeze-step-split process occurs before final sqeeze-step
    # actNormScale: Scale parameter of actnorm layer
    # perm: 1x1 convolution
    # coupling: Affine coupling layer
    # LU: LU decomposition of weight matrix W
    def __init__(self, imageDim, hiddenUnits, K, L, actNormScale, perm, coupling, LU):
        super().__init__()
        self.flow = Flow()

A:\Projects\GLOW>git show e69de29bb2d1d6434b8b29ae775ad8c2e48c5391

A:\Projects\GLOW>git show eedd7ef66b9464bd9abdccc8d6acf719de47ba2b
import torch.nn as nn
import torch
import torch.nn.functional as F
from tools import splitter
import math


def gaussian_p(mean, logs, x):
    """
    lnL = -1/2 * { ln|Var| + ((X - Mu)^T)(Var^-1)(X - Mu) + kln(2*PI) }
            k = 1 (Independent)
            Var = logs ** 2
    """
    c = math.log(2 * math.pi)
    return -0.5 * (logs * 2.0 + ((x - mean) ** 2) / torch.exp(logs * 2.0) + c)


def gaussian_likelihood(mean, logs, x):
    p = gaussian_p(mean, logs, x)
    return torch.sum(p, dim=[1, 2, 3])


def gaussian_sample(mean, logs):
    # Sample from Gaussian with temperature
    z = torch.normal(mean, torch.exp(logs))

    return z

def squeeze(input, factor):
    if factor == 1:
        return input

    B, C, H, W = input.size()

    assert H % factor == 0 and W % factor == 0, "H or W modulo factor is not 0"

    x = input.view(B, C, H // factor, factor, W // factor, factor)
    x = x.permute(0, 1, 3, 5, 2, 4).contiguous()
    x = x.view(B, C * factor * factor, H // factor, W // factor)

    return x


def unsqueeze(input, factor):
    if factor == 1:
        return input

    factor2 = factor ** 2

    B, C, H, W = input.size()

    assert C % (factor2) == 0, "C module factor squared is not 0"

    x = input.view(B, C // factor2, factor, factor, H, W)
    x = x.permute(0, 1, 4, 2, 5, 3).contiguous()
    x = x.view(B, C // (factor2), H * factor, W * factor)

    return x


class SqueezeLayer(nn.Module):
    def __init__(self, factor):
        super().__init__()
        self.factor = factor

    def forward(self, input, logdet=None, reverse=False):
        if reverse:
            output = unsqueeze(input, self.factor)
        else:
            output = squeeze(input, self.factor)

        return output, logdet


class ActNormLayer(nn.module):
    """Initialize bias and scale with first minibatch to ensure zero mean and unit variance
    then make them trainable paramters"""

    def __init__(self, num_features, scale=1.0):
        super().__init__()
        size = [1, num_features, 1, 1]
        self.bias = nn.Parameter(torch.zeros(*size))
        self.logs = nn.Parameter(torch.zeros(*size))
        self.num_features = num_features
        self.scale = scale
        self.inited = False

        def initParameters(self, input):
            if not self.training:
                raise ValueError("In Eval mode, but ActNorm not inited")

            with torch.no_grad():
                bias = -torch.mean(input.clone(), dim=[0, 2, 3], keepdim=True)
                vars = torch.mean((input.clone() + bias) ** 2, dim=[0, 2, 3], keepdim=True)
                logs = torch.log(self.scale / (torch.sqrt(vars) + 1e-6))

                self.bias.data.copy_(bias.data)
                self.logs.data.copy_(logs.data)

                self.inited = True

        def center(self, input, reverse=False):
            if reverse:
                return input - self.bias
            else:
                return input + self.bias

        def scale(self, input, logdet=None, reverse=False):

            if reverse:
                input = input * torch.exp(-self.logs)
            else:
                input = input * torch.exp(self.logs)

            if logdet is not None:
                """
                logs is log_std of `mean of channels`
                so we need to multiply by number of pixels
                """
                b, c, h, w = input.shape

                dlogdet = torch.sum(self.logs) * h * w

                if reverse:
                    dlogdet *= -1

                logdet = logdet + dlogdet

            return input, logdet

        def forward(self, input, logdet=None, reverse=False):
            self._check_input_dim(input)

            if not self.inited:
                self.initialize_parameters(input)

            if reverse:
                input, logdet = self._scale(input, logdet, reverse)
                input = self.center(input, reverse)
            else:
                input = self.center(input, reverse)
                input, logdet = self._scale(input, logdet, reverse)

            return input, logdet


class ActNorm2d(ActNormLayer):
    def __init__(self, num_features, scale=1.0):
        super().__init__(num_features, scale)

    def _check_input_dim(self, input):
        assert len(input.size()) == 4
        assert input.size(1) == self.num_features, (
            "[ActNorm]: input should be in shape as `BCHW`,"
            " channels should be {} rather than {}".format(
                self.num_features, input.size()
            )
        )


class InvertibleConv1x1(nn.Module):
    def __init__(self, num_channels, LU):
        super().__init__()
        w_shape = [num_channels, num_channels]
        w_init = torch.qr(torch.randn(*w_shape))[0]

        if not LU:
            self.weight = nn.Parameter(torch.Tensor(w_init))
        else:
            p, lower, upper = torch.lu_unpack(*torch.lu(w_init))
            s = torch.diag(upper)
            sign_s = torch.sign(s)
            log_s = torch.log(torch.abs(s))
            upper = torch.triu(upper, 1)
            l_mask = torch.tril(torch.ones(w_shape), -1)
            eye = torch.eye(*w_shape)

            self.register_buffer("p", p)
            self.register_buffer("sign_s", sign_s)
            self.lower = nn.Parameter(lower)
            self.log_s = nn.Parameter(log_s)
            self.upper = nn.Parameter(upper)
            self.l_mask = l_mask
            self.eye = eye

        self.w_shape = w_shape
        self.LU = LU

    def get_weight(self, input, reverse):
        b, c, h, w = input.shape

        if not self.LU_decomposed:
            dlogdet = torch.slogdet(self.weight)[1] * h * w
            if reverse:
                weight = torch.inverse(self.weight)
            else:
                weight = self.weight
        else:
            self.l_mask = self.l_mask.to(input.device)
            self.eye = self.eye.to(input.device)

            lower = self.lower * self.l_mask + self.eye

            u = self.upper * self.l_mask.transpose(0, 1).contiguous()
            u += torch.diag(self.sign_s * torch.exp(self.log_s))

            dlogdet = torch.sum(self.log_s) * h * w

            if reverse:
                u_inv = torch.inverse(u)
                l_inv = torch.inverse(lower)
                p_inv = torch.inverse(self.p)

                weight = torch.matmul(u_inv, torch.matmul(l_inv, p_inv))
            else:
                weight = torch.matmul(self.p, torch.matmul(lower, u))

        return weight.view(self.w_shape[0], self.w_shape[1], 1, 1), dlogdet

    def forward(self, input, logdet=None, reverse=False):
        """
        log-det = log|abs(|W|)| * pixels
        """
        weight, dlogdet = self.get_weight(input, reverse)

        if not reverse:
            z = F.conv2d(input, weight)
            if logdet is not None:
                logdet = logdet + dlogdet
            return z, logdet
        else:
            z = F.conv2d(input, weight)
            if logdet is not None:
                logdet = logdet - dlogdet
            return z, logdet


class Permute2d(nn.Module):
    def __init__(self, num_channels, shuffle):
        super().__init__()
        self.num_channels = num_channels
        self.indices = torch.arange(self.num_channels - 1, -1, -1, dtype=torch.long)
        self.indices_inverse = torch.zeros((self.num_channels), dtype=torch.long)

        for i in range(self.num_channels):
            self.indices_inverse[self.indices[i]] = i

        if shuffle:
            self.reset_indices()

    def reset_indices(self):
        shuffle_idx = torch.randperm(self.indices.shape[0])
        self.indices = self.indices[shuffle_idx]

        for i in range(self.num_channels):
            self.indices_inverse[self.indices[i]] = i

    def forward(self, input, reverse=False):
        assert len(input.size()) == 4

        if not reverse:
            input = input[:, self.indices, :, :]
            return input
        else:
            return input[:, self.indices_inverse, :, :]


class Conv2d(nn.Module):
    def __init__(
        self,
        in_channels,
        out_channels,
        kernel_size=(3, 3),
        stride=(1, 1),
        padding="same",
        do_actnorm=True,
        weight_std=0.05,
    ):
        super().__init__()

        if padding == "same":
            padding = compute_same_pad(kernel_size, stride)
        elif padding == "valid":
            padding = 0

        self.conv = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size,
            stride,
            padding,
            bias=(not do_actnorm),
        )

        # init weight with std
        self.conv.weight.data.normal_(mean=0.0, std=weight_std)

        if not do_actnorm:
            self.conv.bias.data.zero_()
        else:
            self.actnorm = ActNorm2d(out_channels)

        self.do_actnorm = do_actnorm

    def forward(self, input):
        x = self.conv(input)
        if self.do_actnorm:
            x, _ = self.actnorm(x)
        return x


class Split2d(nn.Module):
    def __init__(self, num_channels):
        super().__init__()
        self.conv = Conv2dZeros(num_channels // 2, num_channels)

    def split2d_prior(self, z):
        h = self.conv(z)
        return splitter(h, "cross")

    def forward(self, input, logdet=0.0, reverse=False, temperature=None):
        if reverse:
            z1 = input
            mean, logs = self.split2d_prior(z1)
            z2 = gaussian_sample(mean, logs, temperature)
            z = torch.cat((z1, z2), dim=1)
            return z, logdet
        else:
            z1, z2 = splitter(input, "split")
            mean, logs = self.split2d_prior(z1)
            logdet = gaussian_likelihood(mean, logs, z2) + logdet
            return z1, logdet