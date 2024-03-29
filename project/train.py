import sys
sys.path.append('.')
import argparse
import torch
from torch import optim
import torch.nn as nn
from utils import *
from project.UNet import UNet

def train(net, args):

    # get args from CLI
    lr = args.lr
    epochs = args.epochs
    scale = args.scale
    valPercent = args.valPercent
    batchSize = args.batchSize

    dirImg = os.path.join(os.getcwd(), '../data/images/')
    dirMasks = os.path.join(os.getcwd(), '../data/masks/')

    # get image ids
    ids = getIds(dirImg)

    iddataset = splitTrainVal(ids, valPercent)

    print('''Started training:
        Epochs: {}
        Batch size: {}
        Learning rate: {}
        Training Size: {}
        Validation Size: {}'''.format(epochs, batchSize, lr, len(iddataset['train']), len(iddataset['val'])))

    N_TRAIN = len(iddataset['train'])

    # TODO understand and use DataParallel

    # move network to device
    device = torch.device('cuda:0') if torch.cuda.is_available() else torch.device('cpu')
    net = net.to(device)

    # used to update network weights based on training data
    optimizer = optim.SGD(net.parameters(), lr=lr, momentum=0.9, weight_decay=0.0005)

    # computes binary cross entropy b/w estimated masks and actual segmentation masks
    criterion = nn.BCELoss()

    # train network for set epochs
    for epoch in range(epochs):
        print(f"===> Epoch[{epoch + 1}]")

        # set UNet in training mode
        net.train()

        # reset generators
        train = getImageMasks(iddataset['train'], dirImg, dirMasks, scale)
        val = getImageMasks(iddataset['val'], dirImg, dirMasks, scale)

        epochLoss = 0

        # pass images through U-Net and compute loss
        for i, b in enumerate(batch(train, batchSize)):

            # load images and convert to numpy arrays
            imgs = np.array([i[0] for i in b]).astype(np.float32)

            # load image masks
            trueMasks = np.array([i[1] for i in b])

            # load images and masks onto GPU
            imgs = torch.tensor(imgs).to(device)
            trueMasks = torch.tensor(trueMasks).to(device)

            # predict masks
            predMasks = net.forward(imgs)

            # flatten matrices
            masksProbFlat = predMasks.view(-1)
            trueMasksFlat = trueMasks.view(-1)

            # compute loss
            loss = criterion(masksProbFlat, trueMasksFlat)

            epochLoss += loss.item()

            print("{0:.4f} ---- loss: {1:.6f}".format(i * batchSize / N_TRAIN, loss.item()))

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # print average loss over epoch
        print(f"Epoch finished. Avg Loss: {epochLoss / batchSize}")

        # TODO how to measure accuracy of model ?

    # save model weights
    torch.save(net.state_dict(), 'UNet model')

"""
Parses CLI args and trains model
File called "UNet model" is stored in project dir
"""
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--lr", "-learning_rate", dest='lr', type=float, help="Learning rate", default=1e-4)
    parser.add_argument("--e","-epochs", dest='epochs', type=int, help="Epochs to train model", default=80)
    parser.add_argument("--s","-scale", dest='scale', type=float, help="Scale factor for tiles", default=1.0)
    parser.add_argument("--vp", "-val_percent", dest='valPercent', type=float, help="Percentage of images to use for validation", default=0.10)
    parser.add_argument("--bs", "-batch_size", dest='batchSize', type=int, help="Number of images to train on at a time", default=1)

    args = parser.parse_args()

    net = UNet(3, 1)

    # train model
    train(net, args)






