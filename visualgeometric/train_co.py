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
import numpy as np
import matplotlib.pyplot as plt
import sys

from torch_geometric.data import DataLoader #Use the PyG DataLoader

from dataloading.data_loading import SynthiaDataset,SynthiaDatasetTriplet
from retrieval.netvlad import NetvladModel
from visualgeometric.visual_geometric_embedding import VisualGraphEmbeddingCombined, VisualGraphEmbeddingCombinedPT, create_image_model_resnet_18

print('Device:',torch.cuda.get_device_name())

IMAGE_LIMIT=None
BATCH_SIZE=12 #12 gives memory error, 8 had more loss than 6?
LR_GAMMA=0.75
EMBED_DIM=1024
SHUFFLE=True
MARGIN=0.5 #0.2: works, 0.4: increases loss, 1.0: TODO: acc, 2.0: loss unstable
DATASET='summer'

#CAPTURE arg values
LR=float(sys.argv[-1])

print(f'VGE-NV-CO-PT training: image limit: {IMAGE_LIMIT} bs: {BATCH_SIZE} lr gamma: {LR_GAMMA} embed-dim: {EMBED_DIM} shuffle: {SHUFFLE} margin: {MARGIN} dataset: {DATASET} lr: {LR}')

transform=transforms.Compose([transforms.ToTensor(), transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),])

if DATASET=='summer': data_set=SynthiaDatasetTriplet('data/SYNTHIA-SEQS-04-SUMMER/dense', transform=transform, image_limit=IMAGE_LIMIT, return_graph_data=True)
data_loader=DataLoader(data_set, batch_size=BATCH_SIZE, num_workers=2, pin_memory=True, shuffle=SHUFFLE) 

loss_dict={}
best_loss=np.inf
best_model=None


#for lr in (2e-2,1e-2,4e-3,2e-3,1e-3,):
for lr in (LR,):
    print('\n\nlr: ',lr)

    resnet=create_image_model_resnet_18()
    netvlad_model=NetvladModel(resnet)
    netvlad_model_name='model_NV-SYN_lNone_b12_g0.75_sTrue_m0.5_dsummer_lr0.02.pth'
    netvlad_model.load_state_dict(torch.load('models/'+netvlad_model_name)); print('Model:',netvlad_model_name)

    model=VisualGraphEmbeddingCombinedPT(netvlad_model, EMBED_DIM).cuda()

    criterion=nn.TripletMarginLoss(margin=MARGIN)

    optimizer=optim.Adam(model.parameters(), lr=lr) #Adam is ok for PyG
    scheduler=optim.lr_scheduler.ExponentialLR(optimizer,LR_GAMMA)   

    loss_dict[lr]=[]
    for epoch in range(10):
        epoch_loss_sum=0.0
        for i_batch, batch in enumerate(data_loader):
            
            optimizer.zero_grad()
            #print(batch)
            
            a_out=model(batch['images_anchor'].to('cuda'), batch['graphs_anchor'].to('cuda'))
            p_out=model(batch['images_positive'].to('cuda'), batch['graphs_positive'].to('cuda'))
            n_out=model(batch['images_negative'].to('cuda'), batch['graphs_negative'].to('cuda'))

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
model_name=f'model_VGE-NV-CO-PT_l{IMAGE_LIMIT}_b{BATCH_SIZE}_g{LR_GAMMA:0.2f}_e{EMBED_DIM}_s{SHUFFLE}_m{MARGIN}_d{DATASET}_lr{LR}.pth'
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
plt.savefig(f'loss_VGE-NV-CO-PT_l{IMAGE_LIMIT}_b{BATCH_SIZE}_g{LR_GAMMA:0.2f}_e{EMBED_DIM}_s{SHUFFLE}_m{MARGIN}_d{DATASET}_lr{LR}.png')    
