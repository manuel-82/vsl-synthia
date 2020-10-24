import numpy as np
import cv2
import os
import random
import pickle
import sys
from sklearn.cluster import KMeans

from semantic.imports import CLASS_IDS, CLASS_COLORS, RELATIONSHIP_TYPES, DIRECTIONS, CORNERS, CORNER_NAMES, IMAGE_WIDTH, IMAGE_HEIGHT
from semantic.imports import ViewObject, SceneGraph, SceneGraphObject, draw_scenegraph_on_image

from semantic.viewobjects import create_view_objects
from semantic.scenegraphs import create_scenegraph_from_viewobjects, score_scenegraph_to_viewobjects
from dataloading.data_loading import SynthiaDataset

'''
TODO

Try-depth split B-200 (does not have to work everywhere), use class min-areas (F-160 roof) -> Seems good ✓
Merge: small objects in that label, ordered by area, verify that *reduces* the number of blobs (check F-180, B-170) -> seems good, don't know how much difference ✓

New, unified scoring
Investigate 848->852, rel+nn+unused, rel+corner-05+nn+unused, rel+corner-10+nn+unused
Investigate 898 -> before/after (bigger min-areas?, direction via distance/overlap?, ),
Check SG->SG
'''

#TODO: Higher rel-count ?! -> No, not really
#CONTINUE: eval indirect methods (VGE-UE / VGE-NV-CO), if sucessful possibly report retrieval @ K or grid-vote or dense db

data=SynthiaDataset('data/SYNTHIA-SEQS-04-SUMMER/selection/')

#EVAL HAND-PICKED INDICES
if False:
    idx0, idx1=0,310 # 0-> 6, 10,11, 208, 310
    vo0, vo1= data.image_viewobjects[idx0], data.image_viewobjects[idx1]
    sg0, sgd0= create_scenegraph_from_viewobjects(vo0, return_debug_sg=True)
    sg1, sgd1= create_scenegraph_from_viewobjects(vo1, return_debug_sg=True)

    rgb0, rgb1= cv2.imread(data.image_paths[idx0]), cv2.imread(data.image_paths[idx1])
    rbg_draw=rgb1.copy()
    sgd0.draw_on_image(rgb0)
    sgd1.draw_on_image(rgb1)

    score, groundings=score_scenegraph_to_viewobjects(sg0, vo1, unused_factor=0.5)
    print('score:', score)
    draw_scenegraph_on_image(rbg_draw, groundings)

    cv2.imshow("idx0", rgb0)
    cv2.imshow("idx1", rgb1)
    cv2.imshow("matching", rbg_draw)

    cv2.imwrite(str(idx1)+'.jpg', np.hstack((rgb0, rgb1, rbg_draw)))

    cv2.waitKey()
    quit()

#EVAL HAND-PICKED VS. ALL
if False:
    idx=0
    vo= data.image_viewobjects[idx]
    sg, sgd= create_scenegraph_from_viewobjects(vo, return_debug_sg=True)
    scores=np.zeros(len(data))
    for test_index in range(len(data)):
        score,_= score_scenegraph_to_viewobjects(sg, data.image_viewobjects[test_index], unused_factor=0.5)
        scores[test_index]=score

    sorted_indices=np.argsort( -1.0*scores)
    print('sorted indices', sorted_indices[0:10])
    print('scores', scores[0:10])
    quit()

# data_winter=SynthiaDataset('data/SYNTHIA-SEQS-04-WINTER/selection/')
# data_dawn=SynthiaDataset('data/SYNTHIA-SEQS-04-DAWN/selection/')

# #data=data_winter

#query_index=0
#vo=data_winter.image_viewobjects[query_index]
#sg, sgd=create_scenegraph_from_viewobjects(vo, return_debug_sg=True)
# img=cv2.imread(data.image_paths[query_index])
# sgd.draw_on_image(img)

# score,_ = score_scenegraph_to_viewobjects(sg, vo)
# print('score',score)

# for v in vo:
#     print(SceneGraphObject.from_viewobject(v))
# cv2.imshow("",img); cv2.waitKey()

# quit()

# scores=np.zeros(len(data_summer))
# for test_index in range(len(data_summer)):
#     score,_= score_scenegraph_to_viewobjects(sg, data_summer.image_viewobjects[test_index], score_combine='mean')
#     scores[test_index]=score

# sorted_indices=np.argsort( -1.0*scores)
# print('sorted indices', sorted_indices[0:10])
# print('index',np.argwhere(sorted_indices==297))
# print('index',np.argwhere(sorted_indices==307))
# print('--')
# print('index',np.argwhere(sorted_indices==308))

# print('\n---\n')

# qidx,didx=0,0

# vo_q=data_winter.image_viewobjects[qidx]
# sg_q,sgd_q=create_scenegraph_from_viewobjects(vo_q,return_debug_sg=True)
# img_q=cv2.imread(data_winter.image_paths[qidx])

# vo_d=data_summer.image_viewobjects[didx]
# sg_d,sgd_d=create_scenegraph_from_viewobjects(vo_d,return_debug_sg=True)
# img_d=cv2.imread(data_summer.image_paths[didx])

# score, groundings=score_scenegraph_to_viewobjects(sg_q, vo_d, verbose=True, score_combine='mean')
# print(score)
# for v in vo_d:
#     v.draw_on_image(img_d)

# draw_scenegraph_on_image(img_q, sgd_q)
# cv2.imshow("query"+str(qidx),img_q)

# draw_scenegraph_on_image(img_d, groundings)
# cv2.imshow("db"+str(didx),img_d)
# cv2.waitKey()



# for idx in (0,4):
#     sg, sgd=create_scenegraph_from_viewobjects(data.image_viewobjects[idx], return_debug_sg=True)
#     rgb=cv2.imread(data.image_paths[idx])
#     sgd.draw_on_image(rgb)
#     cv2.imshow(str(idx),rgb)
# cv2.waitKey()

'''
Module to create View-Objects and Scene-Graphs for the data
'''
if __name__=='__main__':
    if 'gather-colors' in sys.argv:
        all_colors=[]
        for base_dir in ('data/SYNTHIA-SEQS-04-SUMMER/', 'data/SYNTHIA-SEQS-04-DAWN/', 'data/SYNTHIA-SEQS-04-WINTER/'):
            vo_dict=pickle.load( open( os.path.join(base_dir,'view_objects.pkl'),'rb') )
            
            for direction in DIRECTIONS:
                for vo_list in vo_dict[direction].values():
                    for vo in vo_list:
                        all_colors.append(vo.color)

        all_colors=np.array(all_colors).reshape((-1,3))

        kmeans=KMeans(n_clusters=8).fit(all_colors)
        colors=kmeans.cluster_centers_
        print('Colors:',colors)

    if 'create-semantic' in sys.argv:
        # for base_dir in ('data/SYNTHIA-SEQS-04-SUMMER/train', 'data/SYNTHIA-SEQS-04-SUMMER/test/', 'data/SYNTHIA-SEQS-04-SUMMER/dense', 'data/SYNTHIA-SEQS-04-SUMMER/full/', 
        #                  'data/SYNTHIA-SEQS-04-DAWN/train', 'data/SYNTHIA-SEQS-04-DAWN/test/', 
        #                  'data/SYNTHIA-SEQS-04-WINTER/train', 'data/SYNTHIA-SEQS-04-WINTER/test/'):
        print('CARE: VO only')
        for base_dir in ('data/SYNTHIA-SEQS-04-SUMMER/selection',
                         'data/SYNTHIA-SEQS-04-DAWN/selection',
                         'data/SYNTHIA-SEQS-04-WINTER/selection',):

            file_names=os.listdir( os.path.join(base_dir,'RGB', 'Stereo_Left', DIRECTIONS[0]) )
            print(f'{len(file_names)} positions for {base_dir}...')

            #Create View-Objects and Scene-Graphs
            view_objects={ direction:{} for direction in DIRECTIONS} # {direction: {filename: view-objects} }
            scene_graphs={ direction:{} for direction in DIRECTIONS} # {direction: {filename: Scene-Graph } }
            for direction in DIRECTIONS:
                print(f'Direction: {direction}...')
                view_object_counts=[]
                for file_name in file_names:
                    rgb=   cv2.imread( os.path.join(base_dir,'RGB','Stereo_Left', direction, file_name) )
                    labels=cv2.imread( os.path.join(base_dir,'GT/LABELS','Stereo_Left', direction, file_name), cv2.IMREAD_UNCHANGED)[:,:,2]
                    depth= cv2.imread( os.path.join(base_dir,'Depth','Stereo_Left', direction, file_name), cv2.IMREAD_UNCHANGED)[:,:,0]
                    assert rgb is not None and labels is not None and depth is not None

                    vo=create_view_objects(rgb, labels, depth)
                    view_objects[direction][file_name]=vo
                    view_object_counts.append(len(vo))

                    #sg=create_scenegraph_from_viewobjects(vo)
                    #scene_graphs[direction][file_name]=sg

                print(f'Done, {np.mean(view_object_counts)} view-objects on average, saving')

            pickle.dump(view_objects, open(os.path.join(base_dir,'view_objects.pkl'),'wb'))
            #pickle.dump(scene_graphs, open(os.path.join(base_dir,'scene_graphs.pkl'),'wb'))
