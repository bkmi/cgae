import torch
import torch.nn
import torch.nn.functional
import torch.optim
import torch.utils.data

from functools import partial

from se3cnn.non_linearities.gated_block import GatedBlock
from se3cnn.point.kernel import Kernel
from se3cnn.point.operations import Convolution
from se3cnn.point.radial import CosineBasisModel
from se3cnn.non_linearities import rescaled_act


ACTS = {
    'sigmoid': rescaled_act.sigmoid,
    'tanh': rescaled_act.tanh,
    'relu': rescaled_act.relu,
    'absolute': rescaled_act.absolute,
    # 'softplus': rescaled_act.Softplus,
    # 'shifted_softplus': rescaled_act.ShiftedSoftplus
}


class Encoder(torch.nn.Module):
    def __init__(self, args):
        super().__init__()
        radial_model = partial(
            CosineBasisModel,
            max_radius=args.rad_maxr,
            number_of_basis=args.rad_nb,
            h=args.rad_h,
            L=args.rad_L,
            act=ACTS[args.rad_act]
        )
        K = partial(Kernel, RadialModel=radial_model)
        C = partial(Convolution, K)

        if args.high_l_encoder:
            Rs = [(args.enc_l0, 0), (args.l1, 1), (args.l2, 2), (args.l3, 3), (args.l4, 4), (args.l5, 5)]
            Rs = [[(args.atomic_nums, 0)]] + [Rs] * args.enc_L + [[(args.ncg, 0)]]
        else:
            Rs = [(args.enc_l0, 0)]
            Rs = [[(args.atomic_nums, 0)]] + [Rs] * args.enc_L + [[(args.ncg, 0)]]

        self.layers = torch.nn.ModuleList(
            [GatedBlock(Rs_in, Rs_out, ACTS[args.scalar_act], ACTS[args.gate_act], C)
             for Rs_in, Rs_out in zip(Rs[:-1], Rs[1:-1])] +
            [C(Rs[-2], Rs[-1])]
        )
        self.Rs = Rs

    def forward(self, features, geometry):
        output = features
        for layer in self.layers:
            output = layer(output.div(geometry.size(1) ** 0.5), geometry)  # Normalization of layers by number of atoms.
        return output


class Decoder(torch.nn.Module):
    def __init__(self, args):
        super().__init__()
        radial_model = partial(
            CosineBasisModel,
            max_radius=args.rad_maxr,
            number_of_basis=args.rad_nb,
            h=args.rad_h,
            L=args.rad_L,
            act=ACTS[args.rad_act]
        )
        K = partial(Kernel, RadialModel=radial_model)
        C = partial(Convolution, K)

        Rs = [(args.l0, 0), (args.l1, 1), (args.l2, 2), (args.l3, 3), (args.l4, 4), (args.l5, 5)]
        Rs = [[(args.ncg, 0)]] + [Rs] * args.dec_L
        Rs += [[(mul, l) for l, mul in enumerate([1] * (args.proj_lmax + 1))] * args.atomic_nums]

        self.layers = torch.nn.ModuleList(
            [GatedBlock(Rs_in, Rs_out, ACTS[args.scalar_act], ACTS[args.gate_act], C)
             for Rs_in, Rs_out in zip(Rs[:-1], Rs[1:-1])] +
            [C(Rs[-2], Rs[-1])]
        )
        self.Rs = Rs

    def forward(self, features, geometry):
        output = features
        for layer in self.layers:
            output = layer(output.div(geometry.size(1) ** 0.5), geometry)  # Normalization of layers by number of atoms.
        return output


class Autoencoder(object):
    def __init__(self):
        pass
