# -*- coding: utf-8 -*-
'''
@time: 2019/9/8 19:47

@ author: javis
'''
import pywt, os, copy
import torch
import numpy as np
import pandas as pd
from config import config
from torch.utils.data import Dataset
from sklearn.preprocessing import scale
from scipy import signal
import pickle


def resample(sig, target_point_num=None):
    '''
    对原始信号进行重采样
    :param sig: 原始信号
    :param target_point_num:目标型号点数
    :return: 重采样的信号
    '''
    sig = signal.resample(sig, target_point_num) if target_point_num else sig
    return sig


def scaling(X, sigma=0.1):
    scalingFactor = np.random.normal(loc=1.0, scale=sigma, size=(1, X.shape[1]))
    myNoise = np.matmul(np.ones((X.shape[0], 1)), scalingFactor)
    return X * myNoise


def verflip(sig):
    '''
    信号竖直翻转
    :param sig:
    :return:
    '''
    return sig[::-1, :]


def shift(sig, interval=20):
    '''
    上下平移
    :param sig:
    :return:
    '''
    for col in range(sig.shape[1]):
        offset = np.random.choice(range(-interval, interval))
        sig[:, col] += offset
    return sig


def transform(sig, train=False):
    # 前置不可或缺的步骤
    sig = resample(sig, config.target_point_num)
    # # 数据增强
    if train:
        if np.random.randn() > 0.5: sig = scaling(sig)
        if np.random.randn() > 0.5: sig = verflip(sig)
        if np.random.randn() > 0.5: sig = shift(sig)
    # 后置不可或缺的步骤
    sig = sig.transpose()
    sig = torch.tensor(sig.copy(), dtype=torch.float)
    return sig


def add_4(data):
    III = data[:, 1] - data[:, 0]
    aVR = -(data[:, 0] + data[:, 1]) / 2
    aVL = data[:, 0] - data[:, 1] / 2
    aVF = data[:, 1] - data[:, 0] / 2
    dst_data = np.concatenate(
        (data, III.reshape(-1, 1), aVR.reshape(-1, 1), aVL.reshape(-1, 1), aVF.reshape(-1, 1)), axis=1)
    return dst_data


class ECGDataset(Dataset):
    """
    A generic data loader where the samples are arranged in this way:
    dd = {'train': train, 'val': val, "idx2name": idx2name, 'file2idx': file2idx}
    """

    def __init__(self, data_path, train=True):
        super(ECGDataset, self).__init__()
        dd = torch.load(config.train_data)
        self.train = train

        self.data = dd['train'] if train else dd['val']

        adv_path = '/DATA/disk1/zhangming6/projects/ecg_hf/res/data/dl_full/adv_over_100.pkl'
        adv_list = pickle.load(open(adv_path, 'rb'))
        self.data = adv_list['train'] if train else adv_list['val']

        self.idx2name = dd['idx2name']
        self.file2idx = dd['file2idx']
        self.wc = 1. / np.log(dd['wc'])

        self.age_sex = pickle.load(open(config.train_age_sex, 'rb'))

    def __getitem__(self, index):
        fid = self.data[index]
        if 'txt' not in fid:
            fid += '.txt'
        file_path = os.path.join(config.train_dir, fid)
        df = pd.read_csv(file_path, sep=' ').values
        df = add_4(df)
        x = transform(df, self.train)
        target = np.zeros(config.num_classes)
        target[self.file2idx[fid]] = 1
        target = torch.tensor(target, dtype=torch.float32)

        age = self.age_sex[fid.split('.')[0]]['age'].astype(np.float32)
        sex = self.age_sex[fid.split('.')[0]]['sex'].astype(np.float32)

        return x, age, sex, target

    def __len__(self):
        return len(self.data)


if __name__ == '__main__':
    d = ECGDataset(config.train_data)
    print(d[0])
