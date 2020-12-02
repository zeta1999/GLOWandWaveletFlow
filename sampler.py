import torch
from utils import postprocess
from datasets import Dataset
from adapter import Adapter
import os
import matplotlib.pyplot as plt
from torchvision.utils import make_grid
from barbar import Bar
import numpy as np
from scipy.stats import norm
dir_path = os.path.dirname(os.path.realpath(__file__))


def sampler(modelName, modelDir, ds, n, temp, post=True):
    adapter = Adapter(modelName, ds.data.imDim, device)
    adapter.flow.model.set_actnorm_init()
    adapter.flow.model.load_state_dict(torch.load(modelDir)['model_state_dict'])
    images = adapter.flow.sampler(n, temp)
    if post:
        images = postprocess(images).cpu()
    return images, adapter


def likelihoodEst(adapter, temp=None, n=None, ds=None, sampled=True):
    if not sampled:
        nlls = []
        data_loader = torch.utils.data.DataLoader(ds.data.train_dataset, batch_size=n, num_workers=0)
        for x, y in Bar(data_loader):
            with torch.no_grad():
                _, nll, _ = adapter.flow.model.forward(x.to(device))
                nlls.append(nll)
        return torch.cat(nlls)
    else:
        ims, adapter = sampler(modelName, modelSave, ds_car, n=n, temp=temp, post=False)
        with torch.no_grad():
            _, nll, _ = adapter.flow.model.forward(ims)
    return nll


if __name__ == "__main__":
    cuda = True
    device = "cpu" if (not torch.cuda.is_available() or not cuda) else "cuda:0"
    print(device)
    modelName = 'glow'
    dataset = 'cifar10'
    classNo1 = 2
    classNo2 = 9
    dataroot = dir_path
    download = True
    dataAugment = True
    n = 512
    temp = 1
    output_dir = "saves\\"
    modelSave = "saves\\model-bs64-ep200-lr001-class1_Final.pt"
    sample = False
    likelihood = True
    ds_car = Dataset(dataset, dataroot, dataAugment, download, classNo1)
    ds_truck = Dataset(dataset, dataroot, dataAugment, download, classNo2)
    if sample:
        ims, adapter = sampler(modelName, modelSave, ds_car, n, temp)
        # print(ims[0])
        grid = make_grid(ims[:30], nrow=6).permute(1, 2, 0)
        plt.figure(figsize=(10, 10))
        plt.imshow(grid)
        plt.axis('off')
        plt.show()
    if likelihood:
        adapter = Adapter(modelName, ds_car.data.imDim, device)
        nll_c_sampled = likelihoodEst(adapter, n=1000, temp=temp, sampled=True).cpu().detach().numpy()
        nll_t = likelihoodEst(adapter, n=n, ds=ds_truck, sampled=False).cpu().detach().numpy()
        nll_c = likelihoodEst(adapter, n=n, ds=ds_car, sampled=False).cpu().detach().numpy()
        nllts = [-nll_c_sampled, -nll_c, -nll_t]
        labels = ['sampled car', 'car', 'truck']
        mu, sigma, x, weights, bins, patches, n = [], [], [], [], [], [], []

        plt.figure()

        for i, nllt in enumerate(nllts):
            nllt = nllt[~np.isnan(nllt)]
            mu, sigma = norm.fit(nllt)
            x = np.linspace(mu - 3 * sigma, mu + 3 * sigma, 100)
            plt.hist(nllt, bins=20, label=labels[i], density=True)
            plt.plot(x, norm.pdf(x, mu, sigma))
        plt.title("Histogram Glow - trained on CIFAR10 car")
        plt.xlabel("Negative bits per dimension")
        plt.legend()
        plt.show()
