import torch
import torch.nn as nn
import torch.optim as optim
#from torch.utils.data import DataLoader
from torchvision import transforms
import torchvision
import torchvision.models
import string
import random
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

from torch_geometric.data import DataLoader #Use the PyG DataLoader

from dataloading.data_loading import SynthiaDataset,SynthiaDatasetTriplet
from visualgeometric.geometric_embedding import GeometricEmbedding, PairwiseRankingLoss

'''
Module to train a simple Graph-Embedding model to score the similarity of graphs (using no visual information)
'''
IMAGE_LIMIT=None
BATCH_SIZE=32
LR_GAMMA=0.75
EMBED_DIM_GEOMETRIC=100
SHUFFLE=True
MARGIN=0.5

DATASET='SUMMER' #summer-dawn

LR= float(sys.argv[-1]) #Tested as best on S3D

print(f'Geometric Embedding training: image limit: {IMAGE_LIMIT} ds: {DATASET} bs: {BATCH_SIZE} lr gamma: {LR_GAMMA} embed-dim: {EMBED_DIM_GEOMETRIC} margin: {MARGIN} lr:{LR}')

transform=transforms.Compose([transforms.ToTensor(), transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),])

if DATASET=='SUMMER': data_set=SynthiaDatasetTriplet('data/SYNTHIA-SEQS-04-SUMMER/dense', transform=transform, image_limit=IMAGE_LIMIT, return_graph_data=True)

#Option: shuffle, pin_memory crashes on my system, 
data_loader=DataLoader(data_set, batch_size=BATCH_SIZE, num_workers=2, pin_memory=False, shuffle=SHUFFLE) 

loss_dict={}
best_loss=np.inf
best_model=None


#for lr in (8e-3, 4e-3, 1e-3):
for lr in (LR,):
    print('\n\nlr: ',lr)

    model=GeometricEmbedding(EMBED_DIM_GEOMETRIC)
    model.cuda()

    criterion=nn.TripletMarginLoss(margin=MARGIN)

    optimizer=optim.Adam(model.parameters(), lr=lr) #Adam is ok for PyG
    scheduler=optim.lr_scheduler.ExponentialLR(optimizer,LR_GAMMA)   

    loss_dict[lr]=[]
    for epoch in range(12):
        epoch_loss_sum=0.0
        for i_batch, batch in enumerate(data_loader):
            
            optimizer.zero_grad()
            #print(batch)
            
            a_out=model(batch['graphs_anchor'].to('cuda'))
            p_out=model(batch['graphs_positive'].to('cuda'))
            n_out=model(batch['graphs_negative'].to('cuda'))
            loss=criterion(a_out,p_out,n_out)

            loss.backward()
            optimizer.step()

            l=loss.cpu().detach().numpy()
            epoch_loss_sum+=l
            #print(f'\r epoch {epoch} loss {l}',end='')
        
        scheduler.step()

        epoch_avg_loss = epoch_loss_sum/(i_batch+1)
        print(f'epoch {epoch} final avg-loss {epoch_avg_loss}')
        loss_dict[lr].append(epoch_avg_loss)

    #Now using loss-avg of last epoch!
    if epoch_avg_loss<best_loss:
        best_loss=epoch_avg_loss
        best_model=model

print('\n----')           
model_name=f'model_GeometricEmbed-TripReal_l{IMAGE_LIMIT}_d{DATASET}_b{BATCH_SIZE}_g{LR_GAMMA:0.2f}_e{EMBED_DIM_GEOMETRIC}_m{MARGIN}_lr{LR}.pth'
print('Saving best model',model_name)
torch.save(best_model.state_dict(),model_name)

for k in loss_dict.keys():
    l=loss_dict[k]
    line, = plt.plot(l)
    line.set_label(k)
plt.gca().set_ylim(bottom=0.0) #Set the bottom to 0.0
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
#plt.show()
plt.savefig(f'loss_GeometricEmbed-TripReal_l{IMAGE_LIMIT}_d{DATASET}_b{BATCH_SIZE}_g{LR_GAMMA:0.2f}_e{EMBED_DIM_GEOMETRIC}_m{MARGIN}_lr{LR}.png')    
