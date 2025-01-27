#!/usr/bin/env python
# coding: utf-8

import pickle
import matplotlib.pyplot as plt
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
import pandas as pd
import numpy as np
import torch as T
import torch
import math
from sklearn import metrics
import torch.nn as nn
from torch import optim
import importlib
import torch.nn.functional as F
import import_ipynb
import model_utils
import evaluation
import parameters
from parameters import *
#import model as model
import mimic_model as model
import random
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from sklearn.preprocessing import StandardScaler, OneHotEncoder, MinMaxScaler
from imblearn.over_sampling import RandomOverSampler
from pickle import dump,load
from sklearn.model_selection import train_test_split

#import torchvision.utils as utils
import argparse
from torch.autograd import Variable
from argparse import ArgumentParser
import matplotlib.pyplot as plt
get_ipython().run_line_magic('matplotlib', 'inline')

import warnings
warnings.filterwarnings('ignore')
warnings.simplefilter('ignore')

#save_path = "saved_models/model.tar"
if not os.path.exists("saved_models"):
    os.makedirs("saved_models")

importlib.reload(model_utils)
import model_utils
importlib.reload(model)
import mimic_model as model
importlib.reload(parameters)
import parameters
from parameters import *
importlib.reload(evaluation)
import evaluation


class DL_models():
    def __init__(self,diag_flag,proc_flag,out_flag,chart_flag,med_flag,lab_flag,model_type,k_fold,oversampling,model_name,train):
        self.save_path="saved_models/"+model_name+".tar"
        self.diag_flag,self.proc_flag,self.out_flag,self.chart_flag,self.med_flag,self.lab_flag=diag_flag,proc_flag,out_flag,chart_flag,med_flag,lab_flag
        self.modalities=self.diag_flag+self.proc_flag+self.out_flag+self.chart_flag+self.med_flag+self.lab_flag
        self.k_fold=k_fold
        self.model_type=model_type
        self.oversampling=oversampling
        
        if train: self.cond_vocab_size,self.proc_vocab_size,self.med_vocab_size,self.out_vocab_size,self.chart_vocab_size,self.lab_vocab_size,self.eth_vocab,self.gender_vocab,self.age_vocab,self.ins_vocab=model_utils.init(diag_flag,proc_flag,out_flag,chart_flag,med_flag,lab_flag)
        else:
            self.cond_vocab_size,self.proc_vocab_size,self.med_vocab_size,self.out_vocab_size,self.chart_vocab_size,self.lab_vocab_size,self.eth_vocab,self.gender_vocab,self.age_vocab,self.ins_vocab=model_utils.init_read(diag_flag,proc_flag,out_flag,chart_flag,med_flag,lab_flag)
        
        self.eth_vocab_size,self.gender_vocab_size,self.age_vocab_size,self.ins_vocab_size=len(self.eth_vocab),len(self.gender_vocab),len(self.age_vocab),len(self.ins_vocab)
        
        self.loss=evaluation.Loss('cpu',True,True,True,True,True,True,True,True,True,True,True)
        if torch.cuda.is_available():
            self.device='cuda:0'
        #self.device='cpu'
        if train:
            print("===============MODEL TRAINING===============")
            self.dl_train()
            
        else:
            self.net=torch.load(self.save_path)
            print("[ MODEL LOADED ]")
            print(self.net)
        
        
        
        
        
    def create_kfolds(self):
        labels=pd.read_csv('./data/csv/labels.csv', header=0)
        
        if (self.k_fold==0):
            k_fold=5
        else:
            k_fold=self.k_fold
        hids=labels.iloc[:,0]
        y=labels.iloc[:,1]
        #print(len(hids))
        if self.oversampling:
            print("=============OVERSAMPLING===============")
            oversample = RandomOverSampler(sampling_strategy='minority')
            hids=np.asarray(hids).reshape(-1,1)
            hids, y = oversample.fit_resample(hids, y)
            #print(hids.shape)
            hids=hids[:,0]
            print(len(hids))
        
        ids=range(0,len(hids))
        batch_size=int(len(ids)/k_fold)
        k_hids=[]
        for i in range(0,k_fold):
            rids = random.sample(ids, batch_size)
            ids = list(set(ids)-set(rids))
            if i==0:
                k_hids.append(hids[rids])             
            else:
                k_hids.append(hids[rids])
        return k_hids


    def dl_train(self):
        k_hids=self.create_kfolds()
        
        labels=pd.read_csv('./data/csv/labels.csv', header=0)
        for i in range(self.k_fold):
            self.create_model(self.model_type)
            print("[ MODEL CREATED ]")
            print(self.net)
            print("==================={0:2d} FOLD=====================".format(i))
            
            test_hids=list(k_hids[i])
            #test_hids=test_hids[0:200]
            train_ids=list(set([0,1,2,3,4])-set([i]))
            train_hids=[]
            for j in train_ids:
                train_hids.extend(k_hids[j])  
            #print(test_hids)
            #train_hids=train_hids[0:200]
            val_hids=random.sample(train_hids,int(len(train_hids)*0.1))
            train_hids=list(set(train_hids)-set(val_hids))
            min_loss=100
            counter=0
            for epoch in range(args.num_epochs):
                if counter==args.patience:
                    print("STOPPING THE TRAINING BECAUSE VALIDATION ERROR DID NOT IMPROVE FOR {:.1f} EPOCHS".format(args.patience))
                    break
                train_prob=[]
                train_logits=[]
                train_truth=[]
                self.net.train()
            
                print("======= EPOCH {:.1f} ========".format(epoch))
                for nbatch in range(int(len(train_hids)/(args.batch_size))):
                    meds,chart,out,proc,lab,stat_train,demo_train,Y_train=self.getXY(train_hids[nbatch*args.batch_size:(nbatch+1)*args.batch_size],labels)
#                     print(chart.shape)
#                     print(meds.shape)
#                     print(stat_train.shape)
#                     print(demo_train.shape)
#                     print(Y_train.shape)
                    
                    output,logits = self.train_model(meds,chart,out,proc,lab,stat_train,demo_train,Y_train)
                    
                    
                    train_prob.extend(output.data.cpu().numpy())
                    train_truth.extend(Y_train.data.cpu().numpy())
                    train_logits.extend(logits.data.cpu().numpy())
                
                #print(train_prob)
                #print(train_truth)
                self.loss(torch.tensor(train_prob),torch.tensor(train_truth),torch.tensor(train_logits),False,False)
                val_loss=self.model_val(val_hids)
                #print("Updating Model")
                #T.save(self.net,self.save_path)
                if(val_loss<=min_loss+0.02):
                    print("Validation results improved")
                    min_loss=val_loss
                    print("Updating Model")
                    T.save(self.net,self.save_path)
                    counter=0
                else:
                    print("No improvement in Validation results")
                    counter=counter+1
            self.model_test(test_hids)
            self.save_output()
            
    def model_val(self,val_hids):
        print("======= VALIDATION ========")
        labels=pd.read_csv('./data/csv/labels.csv', header=0)
        
        val_prob=[]
        val_truth=[]
        val_logits=[]
        self.net.eval()

        for nbatch in range(int(len(val_hids)/(args.batch_size))):
            meds,chart,out,proc,lab,stat_train,demo_train,y=self.getXY(val_hids[nbatch*args.batch_size:(nbatch+1)*args.batch_size],labels)
            
            output,logits = self.net(meds,chart,out,proc,lab,stat_train,demo_train)
            output=output.squeeze()
            logits=logits.squeeze()
            
            output=output.squeeze()
            logits=logits.squeeze()

            val_prob.extend(output.data.cpu().numpy())
            val_truth.extend(y.data.cpu().numpy())
            val_logits.extend(logits.data.cpu().numpy())

        self.loss(torch.tensor(val_prob),torch.tensor(val_truth),torch.tensor(val_logits),False,False)
        val_loss=self.loss(torch.tensor(val_prob),torch.tensor(val_truth),torch.tensor(val_logits),True,False)
        return val_loss.item()
            
    def model_test(self,test_hids):
        
        print("======= TESTING ========")
        labels=pd.read_csv('./data/csv/labels.csv', header=0)
        
        self.prob=[]
        self.eth=[]
        self.gender=[]
        self.age=[]
        self.ins=[]
        self.truth=[]
        self.logits=[]
        self.net.eval()
        #print(len(test_hids))
        for nbatch in range(int(len(test_hids)/(args.batch_size))):
            #print(test_hids[nbatch*args.batch_size:(nbatch+1)*args.batch_size])
            meds,chart,out,proc,lab,stat,demo,y=self.getXY(test_hids[nbatch*args.batch_size:(nbatch+1)*args.batch_size],labels)
            
            output,logits = self.net(meds,chart,out,proc,lab,stat,demo)
            output=output.squeeze()
            logits=logits.squeeze()
#             print(demo.shape)
#             print(demo[:,1])
#             print(self.eth_vocab)
            self.eth.extend(demo[:,1].tolist())
            self.gender.extend(demo[:,0].tolist())
            self.ins.extend(demo[:,2].tolist())
            self.age.extend(demo[:,3].tolist())
                
            self.prob.extend(output.data.cpu().numpy())
            self.truth.extend(y.data.cpu().numpy())
            self.logits.extend(logits.data.cpu().numpy())
        #print(self.eth)
        self.loss(torch.tensor(self.prob),torch.tensor(self.truth),torch.tensor(self.logits),False,False)
    
    def getXY(self,ids,labels):
        dyn_df=[]
        meds=torch.zeros(size=(0,0))
        chart=torch.zeros(size=(0,0))
        proc=torch.zeros(size=(0,0))
        out=torch.zeros(size=(0,0))
        lab=torch.zeros(size=(0,0))
        stat_df=torch.zeros(size=(1,0))
        demo_df=torch.zeros(size=(1,0))
        y_df=[]
        #print(ids)
        dyn=pd.read_csv('./data/csv/'+str(ids[0])+'/dynamic.csv',header=[0,1])
        keys=dyn.columns.levels[0]
        for i in range(len(keys)):
            dyn_df.append(torch.zeros(size=(1,0)))
#         print(len(dyn_df))
        for sample in ids:
            y=labels[labels['stay_id']==sample]['label']
            y_df.append(int(y))
            #print(sample)
            dyn=pd.read_csv('./data/csv/'+str(sample)+'/dynamic.csv',header=[0,1])

            for key in range(len(keys)):
                dyn=dyn[keys[key]]
                dyn=dyn.to_numpy()
                dyn=torch.tensor(dyn)
                #print(dyn.shape)
                dyn=dyn.unsqueeze(0)
                #print(dyn.shape)
                dyn=torch.tensor(dyn)
                dyn=dyn.type(torch.LongTensor)
                
                if dyn_df[key].nelement():
                    dyn_df[key]=torch.cat((dyn_df[key],dyn),0)
                else:
                    dyn_df[key]=dyn
            
                #print(dyn_df[key].shape)        
            
            stat=pd.read_csv('./data/csv/'+str(sample)+'/static.csv',header=[0,1])
            stat=stat['COND']
            stat=stat.to_numpy()
            stat=torch.tensor(stat)
            #print(dyn.shape)
            
            if stat_df[key].nelement():
                stat_df=torch.cat((stat_df,stat),0)
            else:
                stat_df=stat
                
            demo=pd.read_csv('./data/csv/'+str(sample)+'/demo.csv',header=0)
            #print(demo["gender"])
            demo["gender"].replace(self.gender_vocab, inplace=True)
            #print(demo["gender"])
            demo["ethnicity"].replace(self.eth_vocab, inplace=True)
            demo["insurance"].replace(self.ins_vocab, inplace=True)
            demo["Age"].replace(self.age_vocab, inplace=True)
            demo=demo[["gender","ethnicity","insurance","Age"]]
            #print(demo)
            demo=demo.values
            #print(demo)
            demo=torch.tensor(demo)
            #print(dyn.shape)
            if demo_df[key].nelement():
                demo_df=torch.cat((demo_df,demo),0)
            else:
                demo_df=demo
        
        
        for k in range(len(keys)):
            if keys[k]=='MEDS':
                meds=dyn_df[k]
            if keys[k]=='CHART':
                chart=dyn_df[k]
            if keys[k]=='OUT':
                out=dyn_df[k]
            if keys[k]=='PROC':
                proc=dyn_df[k]
            if keys[k]=='LAB':
                lab=dyn_df[k]
            
        stat_df=torch.tensor(stat_df)
        stat_df=stat_df.type(torch.LongTensor)
        
        demo_df=torch.tensor(demo_df)
        demo_df=demo_df.type(torch.LongTensor)
        
        y_df=torch.tensor(y_df)
        y_df=y_df.type(torch.LongTensor)
#             #print(stat.shape)
            
     #         X_df=X_df.type(torch.LongTensor)        
        return meds,chart,out,proc,lab ,stat_df, demo_df, y_df       
            
           
        
    
    
    def train_model(self,meds,chart,out,proc,lab,stat_train,demo_train,Y_train):
        
        self.optimizer.zero_grad()
        # get the output sequence from the input and the initial hidden and cell states
        output,logits = self.net(meds,chart,out,proc,lab,stat_train,demo_train)
        output=output.squeeze()
        logits=logits.squeeze()
#         print(output.shape)
#         print(logits.shape)
        out_loss=self.loss(output,Y_train,logits,True,False)
        #print("loss",out_loss)
        # calculate the gradients
        out_loss.backward()
        # update the parameters of the model
        self.optimizer.step()
        
        return output,logits
        


    
    def create_model(self,model_type):
        if model_type=='Time-series LSTM':
            self.net = model.LSTMBase(self.device,
                               self.cond_vocab_size,
                               self.proc_vocab_size,
                               self.med_vocab_size,
                               self.out_vocab_size,
                               self.chart_vocab_size,
                               self.lab_vocab_size,
                               self.eth_vocab_size,self.gender_vocab_size,self.age_vocab_size,self.ins_vocab_size,
                               self.modalities,
                               embed_size=args.embedding_size,rnn_size=args.rnn_size,
                               batch_size=args.batch_size) 
        elif model_type=='Time-series CNN':
            self.net = model.CNNBase(self.device,
                               self.cond_vocab_size,self.cond_seq_len, 
                               self.proc_vocab_size,self.proc_seq_len,
                               self.med_vocab_size,self.med_seq_len,
                               self.out_vocab_size,self.out_seq_len,
                               self.chart_vocab_size,self.chart_seq_len,
                               self.lab_vocab_size,self.lab_seq_len,
                               self.med_signal,self.lab_signal,
                               embed_size=args.embedding_size,rnn_size=args.rnn_size,
                               batch_size=args.batch_size) 
        elif model_type=='Hybrid LSTM':
            self.net = model.LSTMBaseH(self.device,
                               self.cond_vocab_size,
                               self.proc_vocab_size,
                               self.med_vocab_size,
                               self.out_vocab_size,
                               self.chart_vocab_size,
                               self.lab_vocab_size,
                               self.eth_vocab_size,self.gender_vocab_size,self.age_vocab_size,self.ins_vocab_size,
                               self.modalities,
                               embed_size=args.embedding_size,rnn_size=args.rnn_size,
                               batch_size=args.batch_size) 
        elif model_type=='Hybrid CNN':
            self.net = model.CNNBaseH(self.device,
                               self.cond_vocab_size,self.cond_seq_len, 
                               self.proc_vocab_size,self.proc_seq_len,
                               self.med_vocab_size,self.med_seq_len,
                               self.out_vocab_size,self.out_seq_len,
                               self.chart_vocab_size,self.chart_seq_len,
                               self.lab_vocab_size,self.lab_seq_len,
                               self.eth_vocab_size,self.gender_vocab_size,self.age_vocab_size,
                               self.med_signal,self.lab_signal,
                               embed_size=args.embedding_size,rnn_size=args.rnn_size, 
                               batch_size=args.batch_size) 
        elif model_type=='LSTM with Attention':
            self.net = model.LSTMAttn(self.device,
                                   self.cond_vocab_size,self.cond_seq_len, 
                                   self.proc_vocab_size,self.proc_seq_len,
                                   self.med_vocab_size,self.med_seq_len,
                                   self.out_vocab_size,self.out_seq_len,
                                   self.chart_vocab_size,self.chart_seq_len,
                                   self.lab_vocab_size,self.lab_seq_len,
                                   self.eth_vocab_size,self.gender_vocab_size,self.age_vocab_size,
                                   self.med_signal,self.lab_signal,
                                   embed_size=args.embedding_size,rnn_size=args.rnn_size,
                                   batch_size=args.batch_size) 
        self.optimizer = optim.Adam(self.net.parameters(), lr=args.lrn_rate)
        #criterion = nn.CrossEntropyLoss()
        self.net.to(self.device)
    
    def save_output(self):
        reversed_eth = {self.eth_vocab[key]: key for key in self.eth_vocab}
        reversed_gender = {self.gender_vocab[key]: key for key in self.gender_vocab}
        reversed_age = {self.age_vocab[key]: key for key in self.age_vocab}
        reversed_ins = {self.ins_vocab[key]: key for key in self.ins_vocab}
#         print(self.eth)
#         print(reversed_eth)
        
        #print(self.gender)
        
        self.eth=list(pd.Series(self.eth).map(reversed_eth))
#         print(self.eth)
        self.gender=list(pd.Series(self.gender).map(reversed_gender))
        self.age=list(pd.Series(self.age).map(reversed_age))
        self.ins=list(pd.Series(self.ins).map(reversed_ins))
#         print(self.truth)
#         print(self.prob)
#         print(self.logits)
#         print(self.eth)
#         print(self.gender)
        
        output_df=pd.DataFrame()
        output_df['Labels']=self.truth
        output_df['Prob']=self.prob
        output_df['Logits']=self.logits
        output_df['ethnicity']=self.eth
        output_df['gender']=self.gender
        output_df['age']=self.age
        output_df['insurance']=self.ins
        
        with open('./data/output/'+'outputDict', 'wb') as fp:
               pickle.dump(output_df, fp)

