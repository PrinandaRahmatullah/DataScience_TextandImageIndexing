'''
General-Purpose Image Matching
==============================

Class that can match an image against a dataset with
options for parameters such as image size and the type 
of image matching, e.g. color-based, SIFT, SURF, ORB,
etc.

Usage:
------
    python Matcher.py -q [<query image>] -d [<directory>] -a [<algorithm>]

    Viable algorithms are ORB, SIFT, and SURF.
'''

import cv2
import numpy as np
import argparse
import glob
import time
from matplotlib import pyplot as plt

from search import Searcher
from pano import Panorama

class Matcher(object):

    def __init__(self, queryPath, directory, algorithm, width=800, height=600):
        self.image = cv2.imread(queryPath)
        self.w = width
        self.h = height
        self.image = cv2.resize(self.image, (self.w, self.h))
        self.data = directory
        self.alg = algorithm

    def createIndex(self):
        '''
        Creates dictionary with keys as image names and histograms as values.
        '''

        def createHistogram(image, bins=[8, 8, 8]):
            '''
            Creates a flattened 3D histogram.
            '''

            hist = cv2.calcHist([image], [0, 1, 2], None, bins, [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist, 0, 255, cv2.NORM_MINMAX)
            return hist.flatten()

        print("Indexing: " + self.data + "...")
        index = {}

        for imagePath in glob.glob(self.data + "/*.jpg"):
            filename = imagePath[imagePath.rfind("/") + 1:]
            image = cv2.imread(imagePath)
            print('\t%s' % imagePath)
            features = createHistogram(image)
            index[filename] = features

        return index

    def colorSearch(self, max_matches=5):
        '''
        Searches query image against index and returns the specified number of matches.
        Results are in the format (chi-squared distance, image name).
        '''
        self.index = self.createIndex()

        image = cv2.imread(self.image)
        print("Querying: " + self.image + " ...")
        searcher = Searcher(self.index)
        queryFeatures = self.createHistogram(image)

        results = searcher.search(queryFeatures)[:max_matches]

        print("Matches found:")
        for j in range(len(results)):
            (score, imageName) = results[j]
            print("\t%d. %s : %.3f" % (j+1, imageName, score))

        return results


    #################################
    ### Image Matching Algorithms ###
    #################################

    def ORBMatch(self, imagePath, display_results=False):
        '''
        Matches query against specified image using the Oriented FAST and Rotated BRIEF algorithm.
        Matching is done through Brute-Force.
        '''
        training = cv2.imread(imagePath)
        training = cv2.resize(training, (self.w, self.h))

        orb = cv2.ORB_create()

        kp1, des1 = orb.detectAndCompute(self.image, None)
        kp2, des2 = orb.detectAndCompute(training, None)

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        matches = bf.match(des1, des2)

        matches = sorted(matches, key=lambda x: x.distance)

        if display_results:
            draw_params = dict(matchColor=(0,255,0), 
                singlePointColor=None, 
                flags=2)

            image = cv2.drawMatches(self.image, kp1, training, kp2, matches, None, **draw_params)
            plt.imshow(image), plt.show()

        return len(matches)

    def SURFMatch(self, imagePath, display_results=False):
        '''
        Performs a match using Speeded-Up Robust Features algorithm.
        Matching is done with Fast Library for Approximate Nearest Neighbors.
        Lowe's ratio test is applied.
        '''
        training = cv2.imread(imagePath)
        training = cv2.resize(training, (self.w, self.h))

        surf = cv2.xfeatures2d.SURF_create()

        kp1, des1 = surf.detectAndCompute(self.image, None)
        kp2, des2 = surf.detectAndCompute(training, None)

        FLANN_INDEX_KDTREE = 0
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=25)

        flann = cv2.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(des1, des2, k=2)
        filtered = list(filter(lambda x:x[0].distance < 0.7*x[1].distance, matches))
        good = list(map(lambda x: x[0], filtered))

        if display_results:
            draw_params = dict(matchColor=(0,255,0), 
                singlePointColor=None, 
                flags=2)

            result = cv2.drawMatches(self.image, kp1, training, kp2, good, None, **draw_params)
            plt.imshow(result), plt.show()

        return len(good)

    def SIFTMatch(self, imagePath, display_results=False):
        '''
        Performs a match using Scale-Invariant Feature Transform algorithm.
        Matching is done with Fast Library for Approximate Nearest Neighbors.
        Lowe's ratio test is applied.
        '''
        training = cv2.imread(imagePath)
        training = cv2.resize(training, (self.w, self.h))

        sift = cv2.xfeatures2d.SIFT_create()

        kp1, des1 = sift.detectAndCompute(self.image, None)
        kp2, des2 = sift.detectAndCompute(training, None)

        FLANN_INDEX_KDTREE = 0
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)

        flann = cv2.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(des1, des2, k=2)
        filtered = list(filter(lambda x:x[0].distance < 0.7*x[1].distance, matches))
        good = list(map(lambda x: x[0], filtered))

        if display_results:
            draw_params = dict(matchColor=(0,255,0), 
                singlePointColor=None, 
                flags=2)

            result = cv2.drawMatches(self.image, kp1, training, kp2, good, None, **draw_params)
            plt.imshow(result), plt.show()

        return len(good)

    def write(self, filename, mode):
        file = open(filename, mode)
        totalMatches, results, bestMatch = self.run()
        file.write(str(totalMatches) + '\n')
        file.write('[')
        for prob in results[:len(results)-1]:
            file.write(str(prob) + ', ')
        file.write(str(results[-1]) + ']\n')

        angle = int(bestMatch[0].replace(self.data,'').replace('/angle','').replace('.jpg',''))
        Panorama(self.data, 100, 100, angle).write(self.data + '_panorama.jpg')

    def run(self):
        start = time.time()
        print('%s matching...' % self.alg)

        matches = []
        for i in range(0, 375, 15):
            imagePath = self.data + '/angle' + str(i).zfill(3) + '.jpg'
            print('\tMatching %s ...' % imagePath)
            if self.alg == 'SIFT':
                numMatches = self.SIFTMatch(imagePath)
            elif self.alg == 'SURF':
                numMatches = self.SURFMatch(imagePath)
            else:
                numMatches = self.ORBMatch(imagePath)
            print("\tFound %s matches" % numMatches)
            matches.append((imagePath, numMatches))

        sorted_matches = sorted(matches, key=lambda x: x[1])

        totalMatches = sum(list(map(lambda x: x[1], matches)))

        for j in range(1,6):
            (imageName, score) = sorted_matches[-j]
            print("%d. %s : %0.3f" % (j, imageName, 1.0*score / totalMatches))

        print("Found %d total matches" % totalMatches)

        end = time.time()

        print('Time elapsed: %0.1f s' % (end-start))
        results = [1.0*match[1]/totalMatches for match in matches]
        bestMatch = sorted_matches[-1]
        # bestMatch = int(sorted_matches[-1][0].replace(self.data,'').replace('/angle','').replace('.jpg',''))
        return (totalMatches, results, bestMatch)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-q', '--query', required=True,
        help='Path to query image')
    ap.add_argument('-d', '--dataset', required=True,
        help='Path to directory of training images')
    ap.add_argument('-a', '--algorithm', required=True,
        help='Algorithm to use for matching')
    args = vars(ap.parse_args())

    print(__doc__)

    Matcher(args['query'], args['dataset'], args['algorithm']).run()
