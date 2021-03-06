import numpy as np
import cv2
import os
import random
import pickle

from semantic.imports import CLASS_IDS, CLASS_COLORS, RELATIONSHIP_TYPES, COLORS, COLOR_NAMES, CORNERS, CORNER_NAMES, IMAGE_WIDTH, IMAGE_HEIGHT
from semantic.imports import ViewObject, DescriptionObject

'''
Module for new description strategy
'''
def score_scenegraph_to_viewobjects(description_objects, view_objects, factors, verbose=False):
    a_label, a_color, a_corner, a_distance, a_unmentioned=factors
    assert a_unmentioned<=0

    best_scores=np.array([0.0 for do in description_objects])
    best_scores_color=np.array([0.0 for do in description_objects])
    best_scores_corner=np.array([0.0 for do in description_objects])
    best_scores_dist=np.array([0.0 for do in description_objects])

    used_objects=[None for do in description_objects]

    # for do in description_objects:
    #     print(do)

    for i_sub, sub in enumerate(description_objects):
        for obj in [obj for obj in view_objects if obj.label==sub.label]: 
            #obj_score=a_label #Score for correct label
            color_score, corner_score, dist_score=0,0,0

            #Color
            color_distances= np.linalg.norm(obj.color-COLORS,axis=1)
            if np.argmin(color_distances)==COLOR_NAMES.index(sub.color): color_score=a_color

            #Corner
            corner_distances= np.linalg.norm(obj.centroid_i[0:2]/(IMAGE_WIDTH, IMAGE_HEIGHT) - CORNERS, axis=1)
            if np.argmin(corner_distances)==CORNER_NAMES.index(sub.corner): corner_score=a_corner

            #Distance (FG/BG)
            if sub.distance=='foreground' and obj.centroid_i[2]<ViewObject.BG_DIST_THRESH: dist_score=a_distance
            if sub.distance=='background' and obj.centroid_i[2]>ViewObject.BG_DIST_THRESH: dist_score=a_distance
            #print(obj_score)

            obj_score= a_label + color_score + corner_score + dist_score

            if obj_score>best_scores[i_sub]:
                best_scores[i_sub]=obj_score
                used_objects[i_sub]=obj
                best_scores_color[i_sub]=color_score
                best_scores_corner[i_sub]=corner_score
                best_scores_dist[i_sub]=dist_score

    best_scores/= (a_label+a_color+a_corner+a_distance)
    best_scores_color/= a_color
    best_scores_corner/= a_corner
    best_scores_dist/= a_distance

    #Apply penalty for all view-objects that were not mentioned in the description, weighted by description length
    penalty= a_unmentioned * len( set(view_objects).difference(set(used_objects)) )
    penalty/= len(description_objects)

    if verbose:
        print(f'color {np.mean(best_scores_color)}, corner {np.mean(best_scores_corner)}, dist {np.mean(best_scores_dist)}, penalty {penalty}')

    score=np.mean(best_scores) + penalty #Penalty is negative

    return np.clip(score,0,1)

'''
SGs as list of Description-Objects, re-creating View-Objects by using the respective cluster-centers, running DO->VO in both directions, taking average
'''
def score_scenegraph_to_scenegraph(graph0, graph1, factors, verbose=False):
    #Reconstruct the View-Objects
    view_objects0= [ViewObject.from_description_object(do) for do in graph0]
    view_objects1= [ViewObject.from_description_object(do) for do in graph1]

    score0= score_scenegraph_to_viewobjects(graph0, view_objects1, factors, verbose=verbose)
    score1= score_scenegraph_to_viewobjects(graph1, view_objects0, factors, verbose=verbose)
    return np.mean((score0,score1))
                
