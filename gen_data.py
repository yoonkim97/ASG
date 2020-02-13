'''
Generate data for ASG methods

Author:
    Wei-Yang Qu  quwy@lamda.nju.edu.cn
Date:
    2018.04.15
'''


import os
import random
import scipy.linalg as linalg
import copy
import numpy as np
from zoopt import Dimension, Objective, Parameter, Opt, Solution
import time

class GenData:
    
    def __init__(self, ori_data, class_num, generate_size, classifier, budget):
        timestr = time.strftime("%Y%m%d-%H%M%S")
        self.__dim_size = ori_data.shape[1]                                 # dimension size of generated data
        self.__classifier = classifier                                      # discriminitor when generating example
        self.__positive_dataset = []                                        # positive data set generated by ASG 
        self.__negative_dataset = []                                        # negative data set generated by ASG
        self.__deta = 0                                                     # maximum Euclidean distance of original data
        self.__deta_min = 0                                                 # minimum Euclidean distance of original data
        self.__original_data = ori_data                                     # original data
        self.__class_num = class_num                                        # class category
        self.__generate_size = generate_size                                # data size of generative data
        self.__gendir = "gendata"                                           # path of store generated data
        self.__datadir = "datastorage"
        self.__positive_filename = "gendata/D_plus"+str(class_num)+"_1"     # filename of positive data
        self.__negative_filename = "gendata/D_minus"+str(class_num)+"_1"    # filename of negative data
        self.__pos_filename = "datastorage/D_plus" + str(class_num) + "_" + timestr
        self.__neg_filename = "datastorage/D_minus" + str(class_num) + "_" + timestr
        self.__deta,self.__deta_min = self.getMinMaxDistance(ori_data)
        self.__Budget = budget                                              # budget in racos
        self.__init_num = 10                                                # init data in racos

    '''
        Get class category of data
    '''
    def getClassNum(self):
        return self.__class_num

    '''
        Get original data of this class
    '''
    def getOriginData(self):
        return self.__original_data

    '''
        Get the generated positive data 
    '''
    def getGenPositiveData(self):
        return self.__positive_dataset

    '''
        Get the generated negative data
    '''
    def getGenNegativeData(self):
        return self.__negative_dataset

    '''
        Get minimun and maximun Euclidion distance of all instance in 'Data'
    '''
    def getMinMaxDistance(self, Data):
        size = Data.shape[0]
        res = []
        for i in range(size):
            for j in range(i+1,size):
                dis = linalg.norm(Data[i]-Data[j], ord = 2)
                res.append(dis)
        res = np.array(res)
        return res.max(),res.min()

    '''
        Get minimun Euclidion distance between x and all instance in 'Data'
    '''
    def getMinDistance(self, x, Data):
        Data = np.array(Data)
        size = Data.shape[0]
        res = []
        for i in range(size):
            dis = linalg.norm(Data[i] - x,ord = 2)
            res.append(dis)
        res = np.array(res)
        return res.min()

    '''
        Objective function of generating positive data
    '''
    def train_Dplus(self, sol):
        sample = sol.get_x()
        temp = copy.deepcopy(self.__positive_dataset)
        temp.append(sample)
        temp = np.array(temp)
        x,y = [],[]
        x_p,y_p = [],[]
        x_n,y_n = [],[]
        weight = []

        for i in range(self.__original_data.shape[0]):
            x.append(self.__original_data[i])
            x_p.append(self.__original_data[i])
            y.append(1)
            y_p.append(1)
            weight.append(100.0/self.__original_data.shape[0])
        for i in range(temp.shape[0]):
            x.append(temp[i])
            y.append(0)
            x_n.append(temp[i])
            y_n.append(0)
            weight.append(100.0/(temp.shape[0]))
        weight= np.array(weight)
        x = np.array(x); y = np.array(y)

        # get classifier of gen_data
        clf = copy.deepcopy(self.__classifier)
        
        '''
        If clf does not support sample classification with weight, plus modify this code
        '''
        clf = clf.fit(x,y,sample_weight = weight)
  
        # 1:positive   0:negative
        pred_proba_p = clf.predict_proba(x_p)
        pred_proba_n = clf.predict_proba(x_n)
        pred_proba_p, pred_proba_n = np.array(pred_proba_p), np.array(pred_proba_n)

        # build the objective function to be optimized by racos
        if (len(self.__positive_dataset) > 0):
            sample_temp = copy.deepcopy(sample)
            D_plus_temp = copy.deepcopy(self.__positive_dataset)
            dis = self.getMinDistance(sample_temp,np.array(D_plus_temp))
        else:
            dis = 0

        punish = 0
        deta_temp = self.__deta_min
        if (deta_temp - dis < 0):
            punish = 0
        else:
            punish = deta_temp - dis

        C = 0.01
        temp_prob_p = pred_proba_p[:,1]
        temp_prob_n = pred_proba_n[:,1]
        return temp_prob_p.mean() - temp_prob_n.mean()  + C * punish 

    '''
        Function of generate positive data process
    '''
    def generate_positive_data(self, dim_range):
        
        self.__positive_dataset = []
        dim_size = self.__dim_size  # dimensions
        dim_regs = [dim_range] * dim_size  # dimension range
        dim_tys = [True] * dim_size  # dimension type : real
        dim = Dimension(dim_size, dim_regs, dim_tys)  # form up the dimension object
        
        budget = self.__Budget  # number of calls to the objective function
        # by setting autoset=false, the algorithm parameters will not be set by default
        parameter = Parameter(algorithm="racos", budget=budget, autoset=True)

        #so you are allowed to setup algorithm parameters of racos
        # parameter.set_train_size(6)
        # parameter.set_probability(0.95)
        # parameter.set_uncertain_bits(2)
        # parameter.set_positive_size(1)
        # parameter.set_negative_size(5)

        print("generate positive sample of class:", self.__class_num)
        for i in range(self.__generate_size):
            # initial for the generate program
            sample_list = random.sample(range(self.__original_data.shape[0]),self.__init_num)
            init_data = self.__original_data[sample_list]
            parameter.set_init_samples(init_data)

            objective = Objective(self.train_Dplus, dim)
            solution = Opt.min(objective, parameter)
            x_plus = solution.get_x()
            self.__positive_dataset.append(x_plus)         
            print("[ASG] class",self.__class_num, ": generating positive data, data size:",len(self.__positive_dataset))
            print("**************************************************")

            isDataExists = os.path.exists(self.__datadir)
            if not isDataExists:
                os.mkdir(self.__datadir)
            with open(self.__pos_filename, "a") as f:
                for k in range(len(self.__positive_dataset)):
                    for t in range(len(self.__positive_dataset[k])):
                        f.write(str(self.__positive_dataset[k][t]) + ' ')
                    f.write("\n")

            # store the generated data
            isExists = os.path.exists(self.__gendir)
            if not isExists:
                os.mkdir(self.__gendir)
            with open(self.__positive_filename,"w") as f:
                f.write("")
            with open(self.__positive_filename,"a") as f:
                for k in range(len(self.__positive_dataset)):
                    for t in range(len(self.__positive_dataset[k])):
                        f.write(str(self.__positive_dataset[k][t])+ ' ')
                    f.write("\n")
        return

    '''
        Objective function of generating positive data
    '''
    def train_Dminus(self,sol):
        sample = sol.get_x()
        temp = copy.deepcopy(self.__negative_dataset)
        temp.append(sample)
        temp = np.array(temp)
        x_p = self.__original_data; x_n = temp
        x = np.concatenate((x_p,x_n))
        y_p = np.zeros(x_p.shape[0])+1;y_n = np.zeros(x_n.shape[0])
        y = np.concatenate((y_p,y_n))
        weight_p = np.zeros(x_p.shape[0])+100.0/self.__original_data.shape[0]
        weight_n = np.zeros(x_n.shape[0])+100.0/(temp.shape[0])
        weight = np.concatenate((weight_p,weight_n))
        x = np.array(x); y = np.array(y)

        # get classifier of gen_data
        clf = copy.deepcopy(self.__classifier)

        '''
        If clf does not support sample classification with weight, plus modify this code
        '''
        clf = clf.fit(x,y,sample_weight = weight) 
    
        # 1:positive   0:negative
        pred_proba_p = clf.predict_proba(x_p)
        pred_proba_n = clf.predict_proba(x_n)
        pred_proba_p, pred_proba_n = np.array(pred_proba_p), np.array(pred_proba_n)
        sample_temp = copy.deepcopy(sample)
        train_x_temp = copy.deepcopy(self.__original_data)

        # build the objective function to be optimized by racos
        dis = self.getMinDistance(sample_temp,train_x_temp)
        punish = 0
        deta_temp = 5*self.__deta_min
        if (dis - deta_temp < 0):
            punish = 0
        else:
            punish = dis - deta_temp

        if(len(self.__negative_dataset) > 0):
            sample_temp = copy.deepcopy(sample)
            D_minus_temp = copy.deepcopy(self.__negative_dataset)
            dis2 = self.getMinDistance(sample_temp,np.array(D_minus_temp))
        else :
            dis2 = 0
        punish2 = 0

        if (deta_temp - dis2 < 0):
            punish2 = 0
        else:
            punish2 = deta_temp - dis2

        C = 0.01;C2 = 0.01
    
        temp_prob_p = pred_proba_p[:,1]
        temp_prob_n = pred_proba_n[:,1]
        return temp_prob_n.mean() - temp_prob_p.mean() + C * punish + C2 * punish2

    '''
        Function of generate positive data process
    '''
    def generate_negative_data(self, dim_range):   
        self.__negative_dataset = [] 
        dim_size = self.__dim_size  # dimensions
        dim_regs = [dim_range] * dim_size  # dimension range
        dim_tys = [True] * dim_size  # dimension type : real
        dim = Dimension(dim_size, dim_regs, dim_tys)  # form up the dimension object
        
        budget = self.__Budget  # number of calls to the objective function
        # by setting autoset=false, the algorithm parameters will not be set by default
        parameter = Parameter(algorithm="racos", budget=budget, autoset=True)
        # so you are allowed to setup algorithm parameters of racos
        # parameter.set_train_size(6)
        # parameter.set_probability(0.95)
        # parameter.set_uncertain_bits(2)
        # parameter.set_positive_size(1)
        # parameter.set_negative_size(5)

        print("generate negative sample of class:", self.__class_num)
        for i in range(self.__generate_size):
            # init the SRACOS randomly 
            sample_list = random.sample(range(self.__original_data.shape[0]),self.__init_num)
            init_data = self.__original_data[sample_list]
            parameter.set_init_samples(init_data)

            objective = Objective(self.train_Dminus, dim)
            solution = Opt.min(objective, parameter)
            x_minus = solution.get_x()
            self.__negative_dataset.append(x_minus)          
            print("[ASG] class",self.__class_num,": Generating negative data, data size:",len(self.__negative_dataset))
            print("**************************************************")

            isDataExists = os.path.exists(self.__datadir)
            if not isDataExists:
                os.mkdir(self.__datadir)
            with open(self.__neg_filename, "a") as f:
                for k in range(len(self.__negative_dataset)):
                    for t in range(len(self.__negative_dataset[k])):
                        f.write(str(self.__negative_dataset[k][t]) + ' ')
                    f.write("\n")

            isExists = os.path.exists(self.__gendir)
            # store the generated data
            if not isExists:
                os.mkdir(self.__gendir)
            with open(self.__negative_filename,"w") as f:
                f.write("")
            with open(self.__negative_filename,"a") as f:
                for k in range(len(self.__negative_dataset)):
                    for t in range(len(self.__negative_dataset[k])):
                        f.write(str(self.__negative_dataset[k][t])+ ' ')
                    f.write("\n")
        return
