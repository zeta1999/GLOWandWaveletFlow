import torch
from models.adapter import Adapter
import os
dir_path = os.path.dirname(os.path.realpath(__file__))

def execute(modelName, ds, bs, eval_bs, eps, seed, n_workers, device, output_dir):
    adapter = Adapter(modelName, ds.data.imDim, device)
    train_loader, test_loader = adapter.scripts.initialize(ds, bs, eval_bs, seed, n_workers)

    loss = []
    avgEval = []
    lastEval = 999999

    for i in range(eps):
        print(f"Epoch: {i}")
        loss = adapter.scripts.train_step(train_loader, loss)
        print("\n Evaluating...")
        eval_loss = []
        eval_loss = adapter.scripts.eval_step(test_loader, eval_loss)
        lastEval = eval_loss
        avgEval.append(sum(eval_loss)/len(eval_loss))
        print(f'Avg eval loss: {avgEval[-1]}')
        save_name(adapter, i, loss, lastEval, avgEval, ds.nameDataset)


def save_name(adapter, idx, loss, lastEval, avgEval, dsName):
    if idx == eps - 1:
        directory = f"{modelName}-{dsName}-bs{bs}-ep{eps}-lr{str(adapter.flow.lr)[2:]}-class{classNo}_Final.pt"
        torch.save({'epoch': idx, 'model_state_dict': adapter.flow.model.state_dict(),
                    'optimizer_state_dict': adapter.flow.optimizer.state_dict(), 'trainLoss': loss,
                    'evalLoss': avgEval}, dir_path + '\\' + output_dir + directory)

    elif lastEval > avgEval[-1]:
        print('Saving model...')
        directory = f"{modelName}-{dataset}-bs{bs}-ep{eps}-lr{str(adapter.flow.lr)[2:]}-class{classNo}.pt"
        lastEval = avgEval[-1]

        torch.save({'epoch': idx, 'model_state_dict': adapter.flow.model.state_dict(),
                    'optimizer_state_dict': adapter.flow.optimizer.state_dict(), 'trainLoss': loss,
                    'evalLoss': avgEval}, dir_path + '\\' + output_dir + directory)


if __name__ == "__main__":
    torch.cuda.empty_cache()
    cuda = True
    device = "cpu" if (not torch.cuda.is_available() or not cuda) else "cuda:0"
    modelName = 'waveletglow'
    dataset = 'isic'
    classNo = 'benign'
    download = True
    dataAugment = True
    bs = 16
    eval_bs = 512
    eps = 500
    seed = 42069
    n_workers = 0
    output_dir = "saves\\"
    modelSave = "saves\\model-bs32-ep40-lr001_Final.pt"
    print(f"Model: {modelName}, Dataset: {dataset}, bs: {bs}, eps: {eps}, classNo: {classNo}")
    execute(modelName, dataset, bs, eval_bs, eps, seed, n_workers, device, output_dir)




