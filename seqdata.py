import pandas as pd
from Bio import SeqIO
import numpy as np
import tensorflow as tf
import os, subprocess, shutil
from itertools import product

class Seq:

    def __init__(self, fasta_dir, encoding, k):

        self.fasta_dir = fasta_dir

        fasta_files = [fasta_dir + file for file in os.listdir(fasta_dir)]
        fasta_labels = [os.path.splitext(f.split('/')[-1])[0] for f in fasta_files]

        self.names = fasta_labels

        label_dict = {label: [1 if label_num == label else 0 for label_num in fasta_labels] for label in fasta_labels}

        combs = list(product(['A', 'C', 'G', 'T'], repeat= k))
        num_combs = len(combs)

        if encoding == 0: # one-hot encoding
            seq_ohe = {''.join(comb): [0]*num_combs for comb in combs}
            
            for i, comb in enumerate(seq_ohe):
                seq_ohe[comb][i] = 1
        elif encoding == 1: # k-mer embedding    
            seq_kmer = {''.join(comb): i for i, comb in enumerate(product(['A', 'C', 'G', 'T'], repeat = k))}
        
        seqs, labels = [], []

        for i, fasta_file in enumerate(fasta_files):
            for record in SeqIO.parse(fasta_file, "fasta"):

                if encoding == 0:
                    seqs.append([seq_ohe[record.seq[i:i+k]] for i in range(0, len(record.seq) - k + 1)])
                elif encoding == 1:
                    seqs.append([seq_kmer[record.seq[i:i+k]] for i in range(len(record.seq) - k + 1)])

                labels.append(label_dict[fasta_labels[i]])

        self.seqs = np.array(seqs, dtype=object)
        self.labels = np.array(labels)

    def padding(self, max_len):
        self.seqs = tf.keras.preprocessing.sequence.pad_sequences(self.seqs, maxlen=max_len, padding='post', truncating='post')

    def __len__(self):
        return len(self.seqs)

    def max_len(self):
        return max([len(seq) for seq in self.seqs])
    
    def feature_extraction(self, features, train = True, features_exist = False):
        path = 'feat_extraction'

        if not features_exist:
            try:
                if train:
                    shutil.rmtree(path + '/train')
                else:
                    shutil.rmtree(path + '/test')
            except OSError as e:
                print("Error: %s - %s." % (e.filename, e.strerror))
                print('Creating Directory...')

        if not os.path.exists(path):
            os.mkdir(path)
        
        if not os.path.exists(path + '/train'):
            os.mkdir(path + '/train')
        
        if not os.path.exists(path + '/test'):
            os.mkdir(path + '/test')

        self.features = pd.DataFrame()

        fasta_files = [self.fasta_dir + file for file in os.listdir(self.fasta_dir)]

        for i, fasta_file in enumerate(fasta_files):
            if train:
                dataset_path = path + "/train"
            else:
                dataset_path = path + "/test"

            datasets = []

            if 1 in features:
                dataset = dataset_path + '/NAC.csv'

                if not features_exist:
                    subprocess.run(['python', 'MathFeature/methods/ExtractionTechniques.py',
                                    '-i', fasta_file, '-o', dataset, '-l', self.names[i],
                                    '-t', 'NAC', '-seq', '1'], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                datasets.append(dataset)

            if 2 in features:
                dataset = dataset_path + '/DNC.csv'

                if not features_exist:
                    subprocess.run(['python', 'MathFeature/methods/ExtractionTechniques.py', '-i',
                                    fasta_file, '-o', dataset, '-l', self.names[i],
                                    '-t', 'DNC', '-seq', '1'], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                datasets.append(dataset)

            if 3 in features:
                dataset = dataset_path + '/TNC.csv'

                if not features_exist:
                    subprocess.run(['python', 'MathFeature/methods/ExtractionTechniques.py', '-i',
                                    fasta_file, '-o', dataset, '-l', self.names[i],
                                    '-t', 'TNC', '-seq', '1'], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                datasets.append(dataset)

            if 4 in features:
                dataset_di = dataset_path + '/kGap_di.csv'
                dataset_tri = dataset_path + '/kGap_tri.csv'

                if not features_exist:
                    subprocess.run(['python', 'MathFeature/methods/Kgap.py', '-i',
                                    fasta_file, '-o', dataset_di, '-l',
                                    self.names[i], '-k', '1', '-bef', '1',
                                    '-aft', '2', '-seq', '1'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

                    subprocess.run(['python', 'MathFeature/methods/Kgap.py', '-i',
                                    fasta_file, '-o', dataset_tri, '-l',
                                    self.names[i], '-k', '1', '-bef', '1',
                                    '-aft', '3', '-seq', '1'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                datasets.append(dataset_di)
                datasets.append(dataset_tri)

            if 5 in features:
                dataset = dataset_path + '/ORF.csv'

                if not features_exist:
                    subprocess.run(['python', 'MathFeature/methods/CodingClass.py', '-i',
                                    fasta_file, '-o', dataset, '-l', self.names[i]],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                datasets.append(dataset)

            if 6 in features:
                dataset = dataset_path + '/Fickett.csv'

                if not features_exist:
                    subprocess.run(['python', 'MathFeature/methods/FickettScore.py', '-i',
                                    fasta_file, '-o', dataset, '-l', self.names[i],
                                    '-seq', '1'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                datasets.append(dataset)
            
        if datasets:
            dataframes = pd.concat([pd.read_csv(f) for f in datasets], axis=1)
            dataframes = dataframes.loc[:, ~dataframes.columns.duplicated()]
            dataframes = dataframes[~dataframes.nameseq.str.contains("nameseq")]

        dataframes.pop('nameseq')
        dataframes.pop('label')
        
        self.features = dataframes.reset_index(drop=True).values.astype(np.float32)

def pad_data(train, test):

    if train.max_len() > test.max_len():
        train.padding(train.max_len())
        test.padding(train.max_len())

        return train.max_len()
    else:
        train.padding(test.max_len())
        test.padding(test.max_len())

        return test.max_len()
    
