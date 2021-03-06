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
from visualsemantic.semantic_embedding import SemanticEmbedding

'''
Module to train a simple Semantic-Embedding model to score the similarity of captions (using no visual information)
'''

IMAGE_LIMIT=64
BATCH_SIZE=4 #TODO: higher batches!!
LR_GAMMA=0.75
EMBED_DIM=512
SHUFFLE=True
MARGIN=0.5

DATASET='SUMMER' #summer-dawn

#CAPTURE arg values
LR=float(sys.argv[-1])

print(f'Semantic Embedding training: image limit: {IMAGE_LIMIT} ds: {DATASET} bs: {BATCH_SIZE} lr gamma: {LR_GAMMA} embed-dim: {EMBED_DIM} margin: {MARGIN} lr:{LR}')

transform=transforms.Compose([
    #transforms.Resize((950,1000)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

if DATASET=='SUMMER': data_set=SynthiaDatasetTriplet('data/SYNTHIA-SEQS-04-SUMMER/dense', transform=transform, image_limit=IMAGE_LIMIT, return_caption_data=True)

#Option: shuffle, pin_memory crashes on my system, 
data_loader=DataLoader(data_set, batch_size=BATCH_SIZE, num_workers=2, pin_memory=False, shuffle=SHUFFLE) 

loss_dict={}
best_loss=np.inf
best_model=None

for lr in (5e-3,1e-3,5e-4):
#for lr in (LR,):
    print('\n\nlr: ',lr)

    model=SemanticEmbedding(data_set.get_known_words(),EMBED_DIM)
    model.cuda()

    criterion=nn.TripletMarginLoss(margin=MARGIN)
    optimizer=optim.Adam(model.parameters(), lr=lr) #Adam is ok for PyG | Apparently also for packed_sequence!
    scheduler=optim.lr_scheduler.ExponentialLR(optimizer,LR_GAMMA)   

    loss_dict[lr]=[]
    for epoch in range(6):
        epoch_loss_sum=0.0
        for i_batch, batch in enumerate(data_loader):
            
            optimizer.zero_grad()
            #print(batch)
            
            a_out=model(batch['captions_anchor'])
            p_out=model(batch['captions_positive'])
            n_out=model(batch['captions_negative'])

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
model_name=f'model_SemanticEmbed_l{IMAGE_LIMIT}_d{DATASET}_b{BATCH_SIZE}_g{LR_GAMMA:0.2f}_e{EMBED_DIM}_s{SHUFFLE}_m{MARGIN}_lr{LR}.pth'
print('Saving best model',model_name)
torch.save(best_model.state_dict(),model_name)

for k in loss_dict.keys():
    l=loss_dict[k]
    line, = plt.plot(l)
    line.set_label(k)
plt.gca().set_ylim(bottom=0.0) #Set the bottom to 0.0
plt.legend()
#plt.show()
plt.savefig(f'loss_SemanticEmbed_l{IMAGE_LIMIT}_d{DATASET}_b{BATCH_SIZE}_g{LR_GAMMA:0.2f}_e{EMBED_DIM}_s{SHUFFLE}_m{MARGIN}_lr{LR}.png')    
