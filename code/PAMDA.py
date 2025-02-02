import glob
import gzip
import itertools
import os
import sys
import copy
import warnings
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.optimize import curve_fit
from scipy.stats import linregress
from scipy.stats import pearsonr
from scipy.stats import skew
from tqdm.notebook import tqdm
from concurrent.futures import ProcessPoolExecutor
import traceback


def check_inputs(RUN_NAME,
                 TIMEPOINT_CSV,
                 FASTQ_DIR,
                 SAMPLE_FASTQ,
                 PAM_ORIENTATION,
                 PAM_LENGTH,
                 PAM_START,
                 CONTROL_RAW_COUNT_CSV,
                 CONTROL_SAMPLE,
                 CONTROL_SAMPLE_SAMPLE_FASTQ,
                 TIMEPOINTS,
                 MAX_PAM_LENGTH,
                 SPACERS,
                 P5_TIMEPOINT_BARCODE_START,
                 P7_TIMEPOINT_BARCODE_START,
                 USE_TIMEPOINTS,
                 TOP_N_NORMALIZE,
                 INIT_RATE_EST,
                 READ_SUM_MIN,
                 TPS_SUM_MIN,
                 PAM1_NT_RANK,
                 PAM2_NT_RANK,
                 PAM1_INDEX_RANK,
                 PAM2_INDEX_RANK,
                 AVERAGE_SPACER,
                 HEATMAP_FIXED_MIN,
                 HEATMAP_FIXED_MAX,
                 LOG_SCALE_HEATMAP):
    """
    perform some checks for input parameters
    """
    if not os.path.exists(TIMEPOINT_CSV):
        raise Exception('TIMEPOINT_CSV "%s" not found' % TIMEPOINT_CSV)
    if not os.path.exists(FASTQ_DIR):
        raise Exception('fastq directory "%s" not found' % FASTQ_DIR)
    if CONTROL_RAW_COUNT_CSV != None:
        if not os.path.exists(CONTROL_RAW_COUNT_CSV):
            raise Exception('CONTROL_RAW_COUNT_CSV "%s" not found' % CONTROL_RAW_COUNT_CSV)

    fastqs = glob.glob(FASTQ_DIR + '/**/*R1*.fastq.gz', recursive=True)
    if len(fastqs) == 0:
        raise Exception('no fastq files found')
    for fastq in fastqs:
        fastqR1 = fastq
        fastqR2 = fastq.replace('R1', 'R2')
        fastq_name = fastqR1.split('/')[-1]
        fastq_name = fastq_name.split('_L00')[0]
        try:
            SAMPLE_FASTQ[fastq_name]
        except:
            warnings.warn('%s not found in SAMPLE_FASTQ. This fastq will be ignored.' % fastq_name)

    if not isinstance(MAX_PAM_LENGTH, int):
        raise Exception('MAX_PAM_LENGTH should be an integer value, you entered: %s' % MAX_PAM_LENGTH)
    if not isinstance(P5_TIMEPOINT_BARCODE_START, int):
        raise Exception('P5_TIMEPOINT_BARCODE_START should be an integer value, you entered: %s' % P5_TIMEPOINT_BARCODE_START)
    if not isinstance(P7_TIMEPOINT_BARCODE_START, int):
        raise Exception('P7_TIMEPOINT_BARCODE_START should be an integer value, you entered: %s' % P7_TIMEPOINT_BARCODE_START)
    if not isinstance(PAM_LENGTH, int):
        raise Exception('PAM_LENGTH should be an integer value, you entered: %s' % PAM_LENGTH)
    if not isinstance(PAM_START, int):
        raise Exception('PAM_START should be an integer value, you entered: %s' % PAM_START)
    if (CONTROL_RAW_COUNT_CSV == None) and (CONTROL_SAMPLE_SAMPLE_FASTQ == None):
        raise Exception('Either CONTROL_RAW_COUNT_CSV or CONTROL_SAMPLE_SAMPLE_FASTQ must be specified')
    if not (isinstance(CONTROL_SAMPLE_SAMPLE_FASTQ, int) or (CONTROL_SAMPLE_SAMPLE_FASTQ == None)):
        raise Exception(
            'CONTROL_SAMPLE_SAMPLE_FASTQ should be "None" or an integer value, you entered: %s' % CONTROL_SAMPLE_SAMPLE_FASTQ)
    if not isinstance(TOP_N_NORMALIZE, int):
        raise Exception('TOP_N_NORMALIZE should be an integer value, you entered: %s' % TOP_N_NORMALIZE)
    if not isinstance(READ_SUM_MIN, int):
        raise Exception('READ_SUM_MIN should be an integer value, you entered: %s' % READ_SUM_MIN)
    if not isinstance(TPS_SUM_MIN, int):
        raise Exception('TPS_SUM_MIN should be an integer value, you entered: %s' % TPS_SUM_MIN)
    if not isinstance(TIMEPOINTS, list):
        raise Exception('TIMEPOINTS should be a list, you entered: %s' % TIMEPOINTS)
    if not isinstance(INIT_RATE_EST, list):
        raise Exception('INIT_RATE_EST should be a list, you entered: %s' % INIT_RATE_EST)
    if not isinstance(AVERAGE_SPACER, bool):
        raise Exception("AVERAGE_SPACER should be 'True' or 'False', you entered: %s" % AVERAGE_SPACER)
    if not isinstance(LOG_SCALE_HEATMAP, bool):
        raise Exception("LOG_SCALE_HEATMAP should be 'True' or 'False', you entered: %s" % LOG_SCALE_HEATMAP)
    if (HEATMAP_FIXED_MIN != False and not (
            isinstance(HEATMAP_FIXED_MIN, int) or isinstance(HEATMAP_FIXED_MIN, float))):
        raise Exception(
            "HEATMAP_FIXED_MIN should be 'False' or a float or an integer, you entered: %s" % HEATMAP_FIXED_MIN)
    if (HEATMAP_FIXED_MAX != False and not (
            isinstance(HEATMAP_FIXED_MAX, int) or isinstance(HEATMAP_FIXED_MAX, float))):
        raise Exception(
            "HEATMAP_FIXED_MAX should be 'False' or a float or an integer, you entered: %s" % HEATMAP_FIXED_MAX)
    if PAM_ORIENTATION not in ['three_prime', 'five_prime']:
        raise Exception("please enter 'three_prime' or 'five_prime' for PAM_ORIENTATION")
    if PAM_LENGTH > 8:
        warnings.warn('PAM lengths longer than 8 are not recommended')
    if PAM_LENGTH < 1:
        raise Exception('please choose a PAM length >0')
    if PAM_START + PAM_LENGTH > MAX_PAM_LENGTH:
        raise Exception('PAM_START (%s) + PAM_LENGTH (%s) is greater than MAX_PAM_LENGTH (%s)'
                        % (PAM_START, PAM_LENGTH, MAX_PAM_LENGTH))
    if (PAM1_INDEX_RANK != None and PAM2_INDEX_RANK != None):
        if not isinstance(PAM1_INDEX_RANK, list):
            raise Exception('PAM1_INDEX_RANK should be a list, you entered: %s' % PAM1_INDEX_RANK)
        if not isinstance(PAM2_INDEX_RANK, list):
            raise Exception('PAM2_INDEX_RANK should be a list, you entered: %s' % PAM2_INDEX_RANK)
        if len(PAM1_INDEX_RANK) + len(PAM2_INDEX_RANK) != PAM_LENGTH:
            raise Exception(
                'The number of ranked PAM positions in PAM1_INDEX_RANK and PAM2_INDEX_RANK is not equal to PAM_LENGTH')
    elif ((PAM1_INDEX_RANK == None and PAM2_INDEX_RANK != None) or
          (PAM1_INDEX_RANK != None and PAM2_INDEX_RANK == None)):
        raise Exception('Please specify both PAM1_INDEX_RANK and PAM2_INDEX_RANK or leave both as "None".')

#-----------------------------------------------------------------------------------------------------------------------------#

def PAMDA_complete(RUN_NAME,
                   TIMEPOINT_CSV,
                   FASTQ_DIR,
                   SAMPLE_FASTQ,
                   PAM_ORIENTATION,
                   PAM_LENGTH,
                   PAM_START,
                   CONTROL_RAW_COUNT_CSV,
                   CONTROL_SAMPLE,
                   CONTROL_SAMPLE_SAMPLE_FASTQ=None,
                   TIMEPOINTS=[],
                   MAX_PAM_LENGTH=8,
                   SPACERS={'SPACER1': 'GGGCACGGGCAGCTTGCCGG',
                            'SPACER2': 'GTCGCCCTCGAACTTCACCT'},
                   P5_TIMEPOINT_BARCODE_START=2,
                   P7_TIMEPOINT_BARCODE_START=2,
                   USE_TIMEPOINTS=None,
                   TOP_N_NORMALIZE=5,
                   INIT_RATE_EST=[0.0001, 0.001, 0.01],
                   READ_SUM_MIN=4,
                   TPS_SUM_MIN=1,
                   PAM1_NT_RANK={1: 'A', 2: 'C', 3: 'G', 4: 'T'},
                   PAM2_NT_RANK={1: 'A', 2: 'C', 3: 'G', 4: 'T'},
                   PAM1_INDEX_RANK=None,
                   PAM2_INDEX_RANK=None,
                   AVERAGE_SPACER=True,
                   HEATMAP_FIXED_MIN=False,
                   HEATMAP_FIXED_MAX=False,
                   LOG_SCALE_HEATMAP=True):
    """
    Runs the complete PAMDA analysis from fastq files to heat map visualization.
    """
    # perform some checks
    check_inputs(RUN_NAME,
                 TIMEPOINT_CSV,
                 FASTQ_DIR,
                 SAMPLE_FASTQ,
                 PAM_ORIENTATION,
                 PAM_LENGTH,
                 PAM_START,
                 CONTROL_RAW_COUNT_CSV,
                 CONTROL_SAMPLE,
                 CONTROL_SAMPLE_SAMPLE_FASTQ,
                 TIMEPOINTS,
                 MAX_PAM_LENGTH,
                 SPACERS,
                 P5_TIMEPOINT_BARCODE_START,
                 P7_TIMEPOINT_BARCODE_START,
                 USE_TIMEPOINTS,
                 TOP_N_NORMALIZE,
                 INIT_RATE_EST,
                 READ_SUM_MIN,
                 TPS_SUM_MIN,
                 PAM1_NT_RANK,
                 PAM2_NT_RANK,
                 PAM1_INDEX_RANK,
                 PAM2_INDEX_RANK,
                 AVERAGE_SPACER,
                 HEATMAP_FIXED_MIN,
                 HEATMAP_FIXED_MAX,
                 LOG_SCALE_HEATMAP)

    # run the complete pipeline

    print('BEGIN: generate counts from fastqs')
    fastq2count(RUN_NAME,
                TIMEPOINT_CSV,
                FASTQ_DIR,
                SAMPLE_FASTQ,
                PAM_ORIENTATION,
                TIMEPOINTS,
                MAX_PAM_LENGTH,
                SPACERS,
                P5_TIMEPOINT_BARCODE_START,
                P7_TIMEPOINT_BARCODE_START)
    print('FINISHED: generate counts from fastqs \n')

    print('BEGIN: convert raw counts to normalized counts')
    rawcount2normcount(RUN_NAME,
                       CONTROL_RAW_COUNT_CSV,
                       CONTROL_SAMPLE,
                       CONTROL_SAMPLE_SAMPLE_FASTQ,
                       PAM_ORIENTATION,
                       PAM_LENGTH,
                       PAM_START,
                       SPACERS,
                       TIMEPOINTS,
                       MAX_PAM_LENGTH,
                       TOP_N_NORMALIZE)
    print('FINISHED: convert raw counts to normalized counts \n')

    print('BEGIN: calculate rates from normalized counts')
    normcount2rate(RUN_NAME,
                   PAM_LENGTH,
                   PAM_START,
                   TIMEPOINTS,
                   INIT_RATE_EST,
                   READ_SUM_MIN,
                   TPS_SUM_MIN,
                   USE_TIMEPOINTS)
    print('FINISHED: calculate rates from normalized counts \n')

    print('BEGIN: plot heat maps')
    rate2heatmap(RUN_NAME,
                 TIMEPOINT_CSV,
                 PAM_LENGTH,
                 PAM_START,
                 PAM1_NT_RANK,
                 PAM2_NT_RANK,
                 PAM1_INDEX_RANK,
                 PAM2_INDEX_RANK,
                 AVERAGE_SPACER,
                 HEATMAP_FIXED_MIN,
                 HEATMAP_FIXED_MAX,
                 LOG_SCALE_HEATMAP)
    print('FINISHED: plot heat maps')

    print(" _______  _______  __   __  ______   _______ ")
    print("|       ||   _   ||  |_|  ||      | |   _   |")
    print("|    _  ||  |_|  ||       ||  _    ||  |_|  |")
    print("|   |_| ||       ||       || | |   ||       |")
    print("|    ___||       ||       || |_|   ||       |")
    print("|   |    |   _   || ||_|| ||       ||   _   |")
    print("|___|    |__| |__||_|   |_||______| |__| |__|")
    print('complete')

#-----------------------------------------------------------------------------------------------------------------------------#

def fastq2count_single(fastq, fastq_to_sample_dict, pam_orientation, timepoints, max_pam_len, spacers, 
                       timepoint_dict, P5_timepoint_BC_start, P5_timepoint_BC_len, P5_timepoint_BCs, 
                       P7_timepoint_BC_start, P7_timepoint_BC_len, P7_timepoint_BCs):
    print(os.getcwd())
    try: 
        count_data = {}
        fastqR1 = fastq
        fastqR2 = fastq.replace('R1', 'R2')
        fastq_name = fastqR1.split('/')[-1]
        fastq_name = fastq_name.split('_L00')[0]
    
        if fastq_name not in fastq_to_sample_dict.keys():
            print(f'Ignoring {fastq_name}, sample unknown\n')
            return None, None
        sample = fastq_to_sample_dict[fastq_name]
        
        if fastqR1.endswith('.gz'):
            infileR1 = gzip.open(fastqR1, 'rt')
            infileR2 = gzip.open(fastqR2, 'rt')
        else:
            infileR1 = open(fastqR1, 'r')
            infileR2 = open(fastqR2, 'r')
    
        wrong_barcode = 0
        wrong_spacer = 0
        total_reads = 0
        counted_reads = 0
        unknown_tp = 0
        level1 = 0
        level2 = 0
        level1rc = 0
        level2rc = 0
        while infileR1.readline() and infileR2.readline():
            read_sequenceR1 = infileR1.readline().strip()
            infileR1.readline()
            infileR1.readline()
            read_sequenceR2 = infileR2.readline().strip()
            infileR2.readline()
            infileR2.readline()
    
            total_reads += 1
            
            top_read, _, spacer, spacer_loc, P5_timepoints_BC, P7_timepoint_BC = \
                find_BCs_and_spacer(spacers, read_sequenceR1, read_sequenceR2,
                                    P5_timepoint_BC_start, P5_timepoint_BC_len,
                                    P7_timepoint_BC_start, P7_timepoint_BC_len)
    
            if spacer_loc == -1:
                wrong_spacer += 1
                continue
            # print(P7_timepoint_BC, P5_timepoints_BC)
            if len(P5_timepoint_BCs) == 0: 
                barcode_pair = 0
            elif P7_timepoint_BC in P7_timepoint_BCs:
                barcode_pair =  P7_timepoint_BC
            elif P5_timepoints_BC in P5_timepoint_BCs:
                barcode_pair = P5_timepoints_BC
            else:
                wrong_barcode += 1
                continue
    
            if spacer not in count_data:
                nucleotides = ['A', 'T', 'C', 'G']
                total_pam_space = [''.join(p) for p in itertools.product(nucleotides, repeat=max_pam_len)]
                empty_spacer_dict = {x: [0] * (len(timepoints)-1) for x in total_pam_space}
                count_data[spacer] = empty_spacer_dict 
            if barcode_pair in timepoint_dict.keys():
                if pam_orientation == 'three_prime':
                    spacer3p = spacer_loc + len(spacers[spacer])
                    PAM = top_read[spacer3p: spacer3p + max_pam_len]
                    try:
                        tp = timepoint_dict[barcode_pair]
                        count_data[spacer][PAM][tp] += 1
                        counted_reads += 1
                    except:
                        unknown_tp += 1  
                elif pam_orientation == 'five_prime':
                    PAM = top_read[spacer_loc - max_pam_len: spacer_loc]
                    try:
                        tp = timepoint_dict[barcode_pair]
                        count_data[spacer][PAM][tp] += 1
                        counted_reads += 1
                    except:
                        unknown_tp += 1 
                else:
                    raise ValueError('Uknown PAM orientation')
            else:
                wrong_barcode += 1
    
        write_out = (f"{round(float(counted_reads) / float(total_reads) * 100, 2)}% of reads mapped from {fastq_name} ({counted_reads} reads)\n" 
                     f"Total Reads: {total_reads}, Wrong Spacer: {wrong_spacer}, Wrong Barcode: {wrong_barcode}, Unknown Timeppoint: {unknown_tp}")
        tqdm.write(write_out, file=sys.stdout)
    
        return sample, count_data
    except Exception as ex:
        print(f"Processing {fastq} generated an exception: {ex}")
        traceback.print_exception(type(ex), ex, ex.__traceback__)
        raise ex


def fastq2count(run_name,
                timepoint_csv,
                fastq_dir,
                sample_fastq,
                pam_orientation,
                timepoints,
                max_pam_len=8,
                spacers={'SPACER1': 'GGGCACGGGCAGCTTGCCGG', 'SPACER2': 'GTCGCCCTCGAACTTCACCT'},
                P5_timepoint_BC_start=2,
                P7_timepoint_BC_start=2):
    """
    generate raw PAM read counts from fastq files
    Note: We only use P7_timepint_BC, which should be on the same strand as the provided spacer! 

    """
    # check inputs
    fastqs = glob.glob(fastq_dir + '/**/*R1*.fastq.gz', recursive=True)
    if len(fastqs) == 0:
        raise Exception('no fastq files found')

    if pam_orientation not in ['three_prime', 'five_prime']:
        raise Exception("please enter 'three_prime' or 'five_prime' for PAM_ORIENTATION")

    if timepoint_csv is not None:
        try:
            timepoint_ids = pd.read_csv(timepoint_csv)
        except:
            raise Exception('TIMEPOINT_CSV "%s" not found' % timepoint_csv)
        P5_timepoint_BCs = timepoint_ids['P5_timepoint_barcode'].tolist()
        P5_timepoint_BC_len = len(P5_timepoint_BCs[0])
        P7_timepoint_BCs = timepoint_ids['P7_timepoint_barcode'].tolist()
        P7_timepoint_BC_len = len(P5_timepoint_BCs[0])
        timepoint_dict = {}
        for index, row in timepoint_ids.iterrows():
            timepoint_dict[row['P7_timepoint_barcode']] = row['timepoint']
        print(timepoint_dict)
    else:
        print('Not using timepoints')
        timepoint_dict = {0: 0}
        P5_timepoint_BC_len = 0
        P7_timepoint_BC_len = 0
        P5_timepoint_BCs = []
        P7_timepoint_BCs = []
    nt_complement = dict({'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'N': 'N', '_': '_', '-': '-'})

    store_all_data = {}
    n_samples = len(fastqs)

    with ProcessPoolExecutor() as executor:
        futures = executor.map(fastq2count_single, fastqs, 
                               [sample_fastq]*n_samples, 
                               [pam_orientation]*n_samples, 
                               [timepoints]*n_samples, 
                               [max_pam_len]*n_samples, 
                               [spacers]*n_samples, 
                               [timepoint_dict]*n_samples, 
                               [P5_timepoint_BC_start]*n_samples,
                               [P5_timepoint_BC_len]*n_samples, 
                               [P5_timepoint_BCs]*n_samples, 
                               [P7_timepoint_BC_start]*n_samples,
                               [P7_timepoint_BC_len]*n_samples, 
                               [P7_timepoint_BCs]*n_samples
                        )
        for sample, count_data in tqdm(futures, total=n_samples):
            if sample is None:
                continue
            elif sample in store_all_data.keys():
                all_data = store_all_data[sample]    
                # TODO: there's a better way to do it, one file should have one spacer
                for spacer in count_data:
                    if spacer not in all_data.keys():
                        all_data[spacer] = count_data[spacer]
                    else:
                        for pam in count_data[spacer]:
                            for tp, count in enumerate(count_data[spacer][pam]):
                                all_data[spacer][pam][tp] += count
            else:
                store_all_data[sample] = count_data

    # output raw count results as a csv
    print('writing compressed CSV output')

    if not os.path.exists('output/%s' % run_name):
        os.makedirs('output/%s' % run_name)

    with open('output/%s/PAMDA_1_raw_counts.csv' % (run_name), mode='w') as f_out:
        f_out.write((','.join(map(str, ['Sample', 'Spacer', 'PAM'] +
                                  ['Raw_Counts_' + str(x)
                                   for x in range(1, len(timepoints))])) + '\n'))
        for fastq in store_all_data:
            for spacer in store_all_data[fastq]:
                for pam in store_all_data[fastq][spacer]:
                    total_info = [fastq, spacer, pam] + store_all_data[fastq][spacer][pam]
                    f_out.write((','.join(map(str, total_info)) + '\n'))

    # also output summary csv file
    print('summarizing raw read counts')
    raw_count_summary(run_name)

#-----------------------------------------------------------------------------------------------------------------------------#

def rawcount2normcount(run_name,
                       control_rawcount_csv,
                       control_sample,
                       control_sample_SAMPLE_FASTQ,
                       pam_orientation,
                       pam_length,
                       pam_start,
                       spacers={'SPACER1': 'GGGCACGGGCAGCTTGCCGG', 'SPACER2': 'GTCGCCCTCGAACTTCACCT'},
                       timepoints=[0, 60, 480, 1920],
                       max_pam_length=8,
                       top_n=5,
                       input_csv=None):
    """
    generate normalized PAM read counts from raw counts
    """
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    nucleotides = ['A', 'T', 'C', 'G']
    total_pam_space = [''.join(p) for p in itertools.product(nucleotides, repeat=pam_length)]

    if input_csv is None:
        df_input = pd.read_csv('output/%s/PAMDA_1_raw_counts.csv' % (run_name))
    else:
        df_input = pd.read_csv(input_csv)

    if control_rawcount_csv is not None:
        df_control = pd.read_csv(control_rawcount_csv)
        print(df_control.Sample.unique())
        df_input = pd.concat([df_input, df_control], sort=False)
        control_sample_SAMPLE_FASTQ = 1

    # generate counts for the PAMs defined by indicated start position and PAM length
    print('grouping counts by indicated PAM bases')

    column_sort = {'Sample': 'first', 'Spacer': 'first'}
    count_columns = df_input.columns.values[3:]
    new_columns = ['Sample', 'Spacer', 'PAM']
    for count_column in count_columns:
        column_sort[count_column] = 'sum'
        new_columns.append(count_column)
    if pam_orientation == 'three_prime':
        df_input['selected_PAM'] = df_input['PAM'].str[pam_start:pam_start + pam_length]
    else:
        df_input['selected_PAM'] = df_input['PAM'].str[max_pam_length - pam_length - pam_start:
                                                       max_pam_length - pam_start]
    pbar = tqdm(desc='sample:', total=df_input['Sample'].nunique())
    df_list = []
    for sample in df_input['Sample'].unique().tolist():
        for spacer in df_input['Spacer'].unique().tolist():
            temp_df = df_input[(df_input['Sample'] == sample) & (df_input['Spacer'] == spacer)] \
                .groupby(['selected_PAM'], as_index=False).agg(column_sort)
            df_list.append(temp_df)
        pbar.update()
    pbar.close()
    df = pd.concat(df_list)
    df = df.rename(columns={'selected_PAM': 'PAM'})
    df = df.loc[:, new_columns]
    df = df.reset_index(drop=True)

    # start normalizing read counts
    # set up dataframes

    for i in range(1, len(timepoints)):
        df['Norm_Counts_' + str(i)] = df['Raw_Counts_' + str(i)] / \
                                      df.groupby(['Sample', 'Spacer'])['Raw_Counts_' + str(i)].transform(sum)

    # determine t0 read counts for control sample

    print('Control Sample', control_sample)
    print(df.Sample.unique())
    control_dict = {}
    for spacer in spacers:
        control_dict[spacer] = {}
        for PAM in total_pam_space:
            control_dict[spacer][PAM] = 0

    for index, row in df.iterrows():
        if row['Sample'] == control_sample:
            control_dict[row['Spacer']][row['PAM']] = row['Norm_Counts_' +
                                                          str(control_sample_SAMPLE_FASTQ)]

    norm_counts_0 = []
    for index, row in df.iterrows():
        norm_counts_0.append(control_dict[row['Spacer']][row['PAM']])
    df['Norm_Counts_0'] = norm_counts_0
    print(df['Norm_Counts_0'])
    # drop control sample
    df = df[df['Sample'] != control_sample]
    print(df)
    # determing top n enriched PAMs per sample
    print('determining most enriched PAMs per sample')
    pbar = tqdm(desc='samples: ', total=df['Sample'].nunique(),
                file=sys.stdout)
    sample_last = None
    uptrends = {}
    x = range(len(timepoints))
    for index, row in df.iterrows():
        sample_current = row['Sample']
        if sample_current != sample_last:
            pbar.update()
        sample_spacer = str(row['Sample']) + '_' + str(row['Spacer'])
        y = [row['Norm_Counts_' + str(i)] for i in range(len(timepoints))]
        slope = linregress(x, y)
        if sample_spacer in uptrends:
            uptrends[sample_spacer].append([slope[0], y])
        else:
            uptrends[sample_spacer] = [[slope[0], y]]
        sample_last = sample_current
    pbar.close()
    # determine correction for enrichment based on top n enriched PAMs per sample

    uptrend_corrections = {} # contains normalized reads of top n enriched PAMs per sample
    for u in uptrends:
        uptrends[u] = sorted(uptrends[u])
        top_n_entries = [x[1] for x in uptrends[u][-top_n:]]
        top_n_entries_reformat = map(list, zip(*top_n_entries))
        top_n_entries_median = [np.median(x) for x in top_n_entries_reformat]
        uptrend_corrections[u] = top_n_entries_median
    
    print(uptrend_corrections)
    # calculate normalized read counts
    # correct for enrichment
    # normalize relative to t0 abundance

    print('normalizing each sample:')

    pbar = tqdm(desc='samples: ', total=df['Sample'].nunique(),
                file=sys.stdout)
    sample_last = None
    for index, row in df.iterrows():
        sample_current = row['Sample']
        if sample_current != sample_last:
            pbar.update()

        sample_spacer = str(row['Sample']) + '_' + str(row['Spacer'])
        for i in range(len(timepoints)):
            df.loc[index, 'Norm_Counts_' + str(i)] = row['Norm_Counts_' + str(i)] / \
                                                     uptrend_corrections[sample_spacer][i]
            df.loc[index, 'Norm_Counts_' + str(i)] = row['Norm_Counts_' + str(i)] / \
                                                     row['Norm_Counts_0'] if row['Norm_Counts_0'] != 0 else 0   
        sample_last = sample_current
    pbar.close()

    if not os.path.exists('output/%s/PAM_start_%s_length_%s' % (run_name, pam_start, pam_length)):
        os.makedirs('output/%s/PAM_start_%s_length_%s' % (run_name, pam_start, pam_length))

    df.to_csv('output/%s/PAM_start_%s_length_%s/PAMDA_2_norm_counts.csv' %
              (run_name, pam_start, pam_length), index=False)

#-----------------------------------------------------------------------------------------------------------------------------#

def normcount2rate(run_name,
                   pam_length,
                   pam_start,
                   timepoints,
                   init_rate_est=[0.0001, 0.001, 0.01],
                   read_sum_minimum=10,
                   tps_sum_minimum=2,
                   use_timepoints=None,
                   input_csv=None):
    """
    calculate rates (k) of PAM depletion, modeled as exponential decay y(t)=e^-(k*t)
    """

    if input_csv == None:
        df = pd.read_csv('output/%s/PAM_start_%s_length_%s/PAMDA_2_norm_counts.csv' %
                         (run_name, pam_start, pam_length))
    else:
        df = pd.read_csv(input_csv)

    if use_timepoints is None:
        use_timepoints = [n for n in range(len(timepoints))]

    # exponential decay
    def func(x, a, b):
        return a * np.exp(-b * x)

    ks = []
    timepoint_indices = []
    for i in use_timepoints:
        timepoint_indices.append([i, timepoints[i]])

    # Find rates:
    print('calculating rate constants')

    # loop through one row at a time and nonlinear fit rates

    pbar = tqdm(desc='samples: ', total=df['Sample'].nunique(),
                file=sys.stdout)
    previous_row = 'n/a'
    for index, row in df.iterrows():

        current_row = row['Sample']
        if current_row != previous_row:
            pbar.update()

        tps = [x[1] for x in timepoint_indices]
        obs_raw = [0.00000000001] + [row['Raw_Counts_' + str(x[0])]
                                     for x in timepoint_indices if str(x[0]) != '0']
        obs_norm = [row['Norm_Counts_' + str(x[0])] for x in timepoint_indices]

        zero_indices = [i for i, e in enumerate(obs_raw) if e == 0]
        for zero_index in sorted(zero_indices)[::-1]:
            del tps[zero_index]
            del obs_norm[zero_index]
            del obs_raw[zero_index]

        if sum(obs_raw) >= read_sum_minimum and len(obs_norm) >= tps_sum_minimum:

            # map initial conditions to fit error
            min_search = []

            # loop across different initial conditions for k
            for j in init_rate_est:
                p0 = [1.0, j]
                # nonlinear curve fit
                try:
                    popt, pcov = curve_fit(func, tps, obs_norm, p0=p0)
                    # prediction from outputted paramters
                    pred = [func(x, popt[0], popt[1]) for x in tps]
                    # error
                    error = sum([(x[0] - x[1]) ** 2 for x in zip(pred, obs_norm)])
                    # append into dictionary mapping initial conditions to fit error
                    min_search.append([error, list(popt)])
                except:
                    continue
            if len(min_search) != 0:
                ks.append(sorted(min_search)[0][1][1])
            else:
                ks.append('NaN')

        else:
            ks.append('NaN')
        previous_row = current_row
    pbar.close()

    print('appending rate constants')

    min_k = min([100 if ((isinstance(x, float) and x <= 0) or x == 'NaN') else x for x in ks]) if len(ks) > 0 else 'NaN'

    df['Rate_Constant_k'] = [x if ((isinstance(x, float) and x > 0) or x == 'NaN') else min_k for x in ks]

    print('output to CSV')

    if not os.path.exists('output/%s/PAM_start_%s_length_%s' % (run_name, pam_start, pam_length)):
        os.makedirs('output/%s/PAM_start_%s_length_%s' % (run_name, pam_start, pam_length))

    df.to_csv('output/%s/PAM_start_%s_length_%s/PAMDA_3_rates.csv' %
              (run_name, pam_start, pam_length), index=False)

#-----------------------------------------------------------------------------------------------------------------------------#

def rate2heatmap(run_name,
                 TIMEPOINT_CSV,
                 pam_length,
                 pam_start,
                 pam1_nucleotide_rank={1: 'A', 2: 'C', 3: 'G', 4: 'T'},
                 pam2_nucleotide_rank={1: 'A', 2: 'C', 3: 'G', 4: 'T'},
                 pam1_index_rank=None,
                 pam2_index_rank=None,
                 avg_spacer=True,
                 heatmap_fixed_min=False,
                 heatmap_fixed_max=False,
                 log_scale_heatmap=True,
                 input_csv=None):
    """
    generate a heatmap representation of PAM preference
    """

    if input_csv == None:
        csv_input = 'output/%s/PAM_start_%s_length_%s/PAMDA_3_rates.csv' % (run_name, pam_start, pam_length)
    else:
        csv_input = input_csv

    plt.switch_backend('agg')

    timepoint_ids = pd.read_csv(TIMEPOINT_CSV)  # sample barcode file input
    #timepoints = timepoint_ids['timepoint'].tolist()
    # timepoint_name_dict = {}
    # for index, row in timepoint_ids.iterrows():
    #     timepoint_name_dict[row['timepoint']] = row['description']

    if not os.path.exists('figures/%s/PAM_start_%s_length_%s' % (run_name, pam_start, pam_length)):
        os.makedirs('figures/%s/PAM_start_%s_length_%s' % (run_name, pam_start, pam_length))

    def translate_pam(pam_as_numbers, tranlsate_dict):
        pam_as_bases = ''
        for n in str(pam_as_numbers):
            pam_as_bases += tranlsate_dict[int(n)]
        return pam_as_bases

    # Reformatting input dataframe
    df_input = pd.read_csv(csv_input)

    if (pam1_index_rank == None or pam2_index_rank == None):
        # if not specified, split PAM in the middle for x and y-axis
        # default ordering is higher priority for "inner" bases of the PAM
        split_pam_index = np.floor_divide(pam_length, 2)
        pam1_index_rank = [x for x in range(0, split_pam_index)][::-1]
        pam2_index_rank = [x for x in range(split_pam_index, pam_length)]
    else:
        split_pam_index = len(pam1_index_rank)

    df_input['PAM_pt1'] = [x[:split_pam_index] for x in df_input['PAM'].tolist()]
    df_input['PAM_pt2'] = [x[split_pam_index:] for x in df_input['PAM'].tolist()]

    spacers = df_input['Spacer'].unique().tolist()

    pam_length = len(df_input['PAM'].tolist()[0])

    numbers = ['1', '2', '3', '4']
    pam_space = [''.join(p) for p in itertools.product(numbers, repeat=pam_length)]

    # Sort PAMs according to rules
    pam1_ids = []
    pam2_ids = []
    for pam in pam_space:
        pam1_ids.append(int(pam[:split_pam_index]))
        pam2_ids.append(int(pam[split_pam_index:]))

    pam1_ids = sorted([int(x) for x in set(pam1_ids)])
    pam2_ids = sorted([int(x) for x in set(pam2_ids)])

    columns = []
    indices = []
    tmp = ''
    for pam in pam1_ids:
        tmp_dict = {i: j for i, j in zip(pam1_index_rank, list(str(pam)))}
        for i in sorted(tmp_dict):
            tmp += pam1_nucleotide_rank[int(tmp_dict[i])]
        indices.append(tmp)
        tmp = ''

    tmp = ''
    for pam in pam2_ids:
        tmp_dict = {i: j for i, j in zip(pam2_index_rank, list(str(pam)))}
        for i in sorted(tmp_dict):
            tmp += pam2_nucleotide_rank[int(tmp_dict[i])]
        columns.append(tmp)
        tmp = ''

    def save_heatmap():
        """
        save heatmaps
        """
        if avg_spacer:
            plt.savefig('figures/%s/PAM_start_%s_length_%s/PAMDA_HEATMAP_%s.pdf' %
                        (run_name, pam_start, pam_length, variant))
            df_output.to_csv('figures/%s/PAM_start_%s_length_%s/PAMDA_HEATMAP_%s.csv' %
                             (run_name, pam_start, pam_length, variant))
        else:
            plt.savefig('figures/%s/PAM_start_%s_length_%s/PAMDA_HEATMAP_%s_%s.pdf' %
                        (run_name, pam_start, pam_length, variant, spacer))
            df_output.to_csv('figures/%s/PAM_start_%s_length_%s/PAMDA_HEATMAP_%s_%s.csv' %
                             (run_name, pam_start, pam_length, variant, spacer))

    def plot_default_heatmap(df_output, avg_spacer, spacer=None):
        """
        plot heatmap without fancy formatting
        """
        heatmap_min = None
        heatmap_max = None
        if heatmap_fixed_min:
            heatmap_min = heatmap_fixed_min
        if heatmap_fixed_max:
            heatmap_max = heatmap_fixed_max

        # generate heatmaps and save
        sns.set(font_scale=1)
        fig, ax = plt.subplots()
        plt.title(variant + '(' + sample + ')', y=1)
        ax = sns.heatmap(df_output,
                         vmin=heatmap_min,
                         vmax=heatmap_max,
                         square=True,
                         cmap='Blues',
                         cbar=True,
                         cbar_kws={"shrink": 0.5},
                         linewidth=0.2,
                         linecolor="White",
                         xticklabels=[translate_pam(pam, pam2_nucleotide_rank) for pam in pam2_ids])
        fig.tight_layout(pad=4)
        ax.xaxis.tick_top()
        ax.tick_params(length=0)
        plt.yticks(rotation=0)
        plt.xticks(rotation=90)
        save_heatmap()
        plt.close()

    def plot_nice_heatmap(df_output, avg_spacer, spacer=None):
        """
        plot pretty heatmaps with color-formatted axes labels (only for 2-5 nt PAMs)
        """
        heatmap_min = None
        heatmap_max = None
        if heatmap_fixed_min:
            heatmap_min = heatmap_fixed_min
        if heatmap_fixed_max:
            heatmap_max = heatmap_fixed_max

        if log_scale_heatmap:
            cbar_label = 'Log10(rate)'
        else:
            cbar_label = 'rate'

        # heatmap plotting
        axes = [12 * (pam_length - split_pam_index), 12 * (split_pam_index)]
        fig, ax1 = plt.subplots(1, figsize=(axes[0], axes[1]))
        sns.heatmap(df_output,
                    ax=ax1,
                    vmin=heatmap_min,
                    vmax=heatmap_max,
                    square=True,
                    cmap='Blues',
                    cbar=True,
                    cbar_kws={'shrink': axes[1] / axes[0] / 2,
                              'label': cbar_label,
                              'aspect': 8,},
                    linewidth=0.2,
                    linecolor="White",
                    xticklabels=False,
                    yticklabels=False)
        heatmap_size = fig.get_size_inches()
        cbar = ax1.collections[0].colorbar


        # format the axis labels

        # colors of the bases of the axis labels
        colors = {'A': '#feb2b1', 'C': '#14c7fe', 'T': '#14f485', 'G': '#f8ffa3'}
        # scaling dict manually scales the colored axis labels
        # dict structure: {pam_len:{split_index:[x_width,x_height,y_width,y_height]}}
        scaling_dict = {2: {1: [1, 3.5, 4, 1.07]},
                        3: {1: [1, 1.7, 1, 2.15], 2: [1, 2, 4, 3.53]},
                        4: {1: [1, 0.7, 0.3, 5.5], 2: [1, 5.1, 1, 4.3], 3: [1, 1, 4, 14.1]},
                        5: {1: [1, 0.25, 0.08, 17], 2: [1, 3, 0.3, 11.5],
                            3: [1, 1, 1, 14.15], 4: [1, 0.3, 3, 56.5]}}
        x_text = [[columns[n][m] for n in range(len(columns))] for m in range(len(columns[0]))]
        x_text = x_text[::-1]
        x_color = [[colors[x_text[n][m]] for m in range(len(x_text[0]))] for n in range(len(x_text))]
        xtable = ax1.table(cellText=x_text, cellColours=x_color,
                           cellLoc='center', loc='top')
        for key, cell in xtable.get_celld().items():
            cell.set_linewidth(0)
        y_text = [[indices[n][m] for m in range(len(indices[0]))] for n in range(len(indices))]
        y_color = [[colors[y_text[n][m]] for m in range(len(y_text[0]))] for n in range(len(y_text))]
        y_widths = [0.06 for n in enumerate(y_text)]
        ytable = ax1.table(cellText=y_text, cellColours=y_color, colWidths=y_widths,
                           cellLoc='center', loc='left')
        for key, cell in ytable.get_celld().items():
            cell.set_linewidth(0)
        xtable.set_fontsize(12)
        ytable.set_fontsize(12)
        xtable.scale(scaling_dict[pam_length][split_pam_index][0],
                     scaling_dict[pam_length][split_pam_index][1])
        ytable.scale(scaling_dict[pam_length][split_pam_index][2],
                     heatmap_size[1] / scaling_dict[pam_length][split_pam_index][3])
        plt.tight_layout(pad=6)

        # save the heatmap
        save_heatmap()
        plt.close()

    def spacer_correlation(df_input, sample, spacer1, spacer2):
        """
        if len(spacers)==2, the correlation between the two spacers may be plotted
        """
        x = df_input['Rate_Constant_k'][(df_input['Sample'] == sample) & (df_input['Spacer'] == spacer1)].fillna(0)
        y = df_input['Rate_Constant_k'][(df_input['Sample'] == sample) & (df_input['Spacer'] == spacer2)].fillna(0)
        corr, pval = pearsonr(x, y)
        plt.figure(figsize=(6, 6))
        plt.scatter(x, y, color='Black')
        plt.title('Correlation %s versus %s \n Pearson r: %s' % (spacer1, spacer2, round(corr, 4)))
        plt.xlabel('Rate constant %s' % spacer1)
        plt.ylabel('Rate constant %s' % spacer2)
        plt.xlim(xmin=0)
        plt.ylim(ymin=0)
        plt.tight_layout()
        plt.savefig('figures/%s/PAM_start_%s_length_%s/PAMDA_spacer_correlation_%s_%s.pdf' %
                    (run_name, pam_start, pam_length, variant, sample))
        plt.close()

    # loop through variants and make heatmaps
    pbar = tqdm(desc='samples: ', total=df_input['Sample'].nunique(),
                file=sys.stdout)
    new_columns = []
    print(df_input)
    for variant in df_input['Sample'].unique().tolist():
        for column in columns:
            assert not ':' in variant, 'Sample name cannot contain ":" in its name'
            new_columns.append(str(column) + ':' + str(variant))
        df_output = pd.DataFrame(columns=new_columns, index=indices)

        if avg_spacer:
            for row in df_output.index:
                for column in df_output.columns:
                    pam2 = str(column.split(':')[0].strip('\n'))
                    sample = str(column.split(':')[1].strip('\n'))
                    rate_avg = 0
                    for spacer in sorted(spacers):
                        rate_avg += float(df_input['Rate_Constant_k'][(df_input['PAM_pt1'] == str(row)) &
                                                                      (df_input['PAM_pt2'] == pam2) &
                                                                      (df_input['Sample'] == sample) &
                                                                      (df_input['Spacer'] == spacer)].tolist()[0])
                    rate_avg = rate_avg / len(spacers)
                    if log_scale_heatmap:
                        df_output.loc[row, column] = np.log10(rate_avg)
                    else:
                        df_output.loc[row, column] = rate_avg
            df_output = df_output[df_output.columns].astype(float)
            if (pam_length <= 5) and (pam_length >= 2):
                plot_nice_heatmap(df_output, avg_spacer)
            else:
                plot_default_heatmap(df_output, avg_spacer)
            if len(spacers) == 2:
                spacer_correlation(df_input, variant, spacers[0], spacers[1])

        else:
            for spacer in sorted(spacers):
                for row in df_output.index:
                    for column in df_output.columns:
                        pam2 = str(column.split(':')[0].strip('\n'))
                        sample = str(column.split(':')[1].strip('\n'))
                        rate = df_input['Rate_Constant_k'][(df_input['PAM_pt1'] == str(row)) &
                                                                 (df_input['PAM_pt2'] == pam2) &
                                                                 (df_input['Sample'] == sample) &
                                                                 (df_input['Spacer'] == spacer)]
                        if rate.empty:
                            print(f'Could not find rate value for {sample}, {spacer}')
                            rate = 0.0
                        else:
                            rate = float(rate.tolist()[0])
                        if log_scale_heatmap:
                            df_output.loc[row, column] = np.log10(rate)
                        else:
                            df_output.loc[row, column] = rate
                df_output = df_output[df_output.columns].astype(float)
                if (pam_length <= 5) and (pam_length >= 2):
                    plot_nice_heatmap(df_output, avg_spacer)
                else:
                    plot_default_heatmap(df_output, avg_spacer)
                if len(spacers) == 2:
                    spacer_correlation(df_input, variant, spacers[0], spacers[1])
        pbar.update()
        new_columns = []
    pbar.close()

def reverse_complement(seq):
    nt_complement = {
        'A': 'T', 'a': 'T',
        'C': 'G', 'c': 'G',
        'G': 'C', 'g': 'C',
        'T': 'A', 't': 'A',
        'N': 'N', 'n': 'N',
        '_': '_', '-': '-'
        }
    return "".join(nt_complement[c] for c in reversed(seq.upper()))

def find_BCs_and_spacer(spacers, read_sequenceR1, read_sequenceR2,
                        P5_sample_BC_start, P5_sample_BC_len,
                        P7_sample_BC_start, P7_sample_BC_len):
    """
    find the sample barcodes and the spacer, orientation, and location
    more complicated than necessary for standard HT-PAMDA library prep
    intended for compatibility with other library prep methods
    such as cases where P5 and P7 ends are not defined

    return:
        top_read: read containing spacer, oriented 5' to 3'. If the spacer is found in both reads,
            top read is the read where the spacer occurs earlier in the sequence
        bot_read: the other read
        spacer: the spacer that was found in the input 'spacers' list
        spacer_loc: the location of the 5' end of the spacer in the top_read
        P5_sample_BC: the P5 sample barcode
        P7_sample_BC: the P7 sample barcode
    """

    spacer_loc = -1  # location of 5' end of spacer
    spacer_loc_rc = -1
    spacer = None
    top_read = None
    bot_read = None
    P5_sample_BC = None
    P7_sample_BC = None

    for sp in spacers:
        spacer_loc = read_sequenceR1.find(spacers[sp])
        spacer_loc_rc = reverse_complement(read_sequenceR2).find(spacers[sp])
        if (spacer_loc != -1 or spacer_loc_rc != -1):
            spacer = sp
            P5_sample_BC = read_sequenceR2[P5_sample_BC_start:
                                           P5_sample_BC_start + P5_sample_BC_len]
            P7_sample_BC = read_sequenceR1[P7_sample_BC_start:
                                           P7_sample_BC_start + P7_sample_BC_len]
            if spacer_loc == -1:
                spacer_loc = spacer_loc_rc
                top_read = reverse_complement(read_sequenceR2)
                bot_read = read_sequenceR1
                break
            elif spacer_loc_rc == -1:
                top_read = read_sequenceR1
                bot_read = reverse_complement(read_sequenceR2)
                break
            elif spacer_loc > spacer_loc_rc:
                spacer_loc = spacer_loc_rc
                top_read = reverse_complement(read_sequenceR2)
                bot_read = read_sequenceR1
                break
            else:
                top_read = read_sequenceR1
                bot_read = reverse_complement(read_sequenceR2)
                break
        else:
            spacer_loc = read_sequenceR2.find(spacers[sp])
            spacer_loc_rc = reverse_complement(read_sequenceR1).find(spacers[sp])
            if (spacer_loc != -1 or spacer_loc_rc != -1):
                spacer = sp
                P5_sample_BC = read_sequenceR1[P5_sample_BC_start:
                                               P5_sample_BC_start + P5_sample_BC_len]
                P7_sample_BC = read_sequenceR2[P7_sample_BC_start:
                                               P7_sample_BC_start + P7_sample_BC_len]
                if spacer_loc == -1:
                    spacer_loc = spacer_loc_rc
                    top_read = reverse_complement(read_sequenceR1)
                    bot_read = read_sequenceR2
                    break
                elif spacer_loc_rc == -1:
                    top_read = read_sequenceR2
                    bot_read = reverse_complement(read_sequenceR1)
                    break
                elif spacer_loc > spacer_loc_rc:
                    spacer_loc = spacer_loc_rc
                    top_read = reverse_complement(read_sequenceR1)
                    bot_read = read_sequenceR2
                    break
                else:
                    top_read = read_sequenceR2
                    bot_read = reverse_complement(read_sequenceR1)
                    break

    return top_read, bot_read, spacer, spacer_loc, P5_sample_BC, P7_sample_BC

def raw_count_summary(run_name, input_csv=None):
    """
    just sum across all PAMs for each sample and timepoint to summarize raw counts
    """
    if input_csv is None:
        df_input = pd.read_csv('output/%s/PAMDA_1_raw_counts.csv' % run_name)
    else:
        df_input = pd.read_csv(input_csv)

    df_output = df_input.groupby(['Sample', 'Spacer']).sum()

    if not os.path.exists('output/%s' % run_name):
        os.makedirs('output/%s/' % run_name)

    df_output.to_csv('output/%s/PAMDA_1_raw_counts_summary.csv' %
                     run_name)

def library_QC(RUN_NAME, 
                CONTROL_FASTQ_DIR,
                CONTROL_FASTQ,
                CONTROL_SAMPLE,
                PAM_ORIENTATION,
                PAM_LENGTH,
                PAM_START,
                MAX_PAM_LENGTH = 8, 
                SPACERS = {'SPACER1':'GGGCACGGGCAGCTTGCCGG', 'SPACER2':'GTCGCCCTCGAACTTCACCT'},
                P5_TIMEPIONT_BARCODE_START = 2,
                P7_TIMEPOINT_BARCODE_START = 2):
    
    print('Begin library QC')
    library_QC_check_inputs(RUN_NAME, 
                            CONTROL_FASTQ_DIR,
                            CONTROL_FASTQ,
                            PAM_ORIENTATION,
                            PAM_LENGTH,
                            PAM_START,
                            MAX_PAM_LENGTH, 
                            SPACERS,
                            P5_TIMEPIONT_BARCODE_START,
                            P7_TIMEPOINT_BARCODE_START)
    
    control_fastq2count(RUN_NAME, 
                        CONTROL_FASTQ_DIR,
                        CONTROL_FASTQ,
                        CONTROL_SAMPLE,
                        PAM_ORIENTATION,
                        PAM_LENGTH,
                        PAM_START,
                        MAX_PAM_LENGTH, 
                        SPACERS,
                        P5_TIMEPIONT_BARCODE_START,
                        P7_TIMEPOINT_BARCODE_START)
    
    rawcount2PAMcount(RUN_NAME,
                      PAM_ORIENTATION,
                      PAM_LENGTH,
                      PAM_START,
                      MAX_PAM_LENGTH)
    
    print('Library QC complete')


def library_QC_check_inputs(RUN_NAME,
                           CONTROL_FASTQ_DIR,
                           CONTROL_FASTQ,
                           PAM_ORIENTATION,
                           PAM_LENGTH,
                           PAM_START,
                           MAX_PAM_LENGTH, 
                           SPACERS,
                           P5_TIMEPOINT_BARCODE_START,
                           P7_TIMEPOINT_BARCODE_START):
    """
    perform some checks for input parameters
    """
    if not os.path.exists(CONTROL_FASTQ_DIR):
        raise Exception('CONTROL_FASTQ_DIR "%s" not found' % CONTROL_FASTQ_DIR)
    fastqs = glob.glob(CONTROL_FASTQ_DIR +'/**/*R1*.fastq.gz', recursive = True)
    print(os.getcwd())
    print(fastqs)
    if len(fastqs)==0:
        raise Exception('no fastq files found')
    fastq_names = []
    for fastq in fastqs:
        fastqR1 = fastq
        fastqR2 = fastq.replace('R1','R2')
        fastq_name = fastqR1.split('/')[-1]
        fastq_name = fastq_name.split('_L00')[0]
        fastq_names.append(fastq_name)
        if fastq_name != CONTROL_FASTQ:
            warnings.warn('%s is not the CONTROL_FASTQ. This fastq will be ignored.' % fastq_name)
    if CONTROL_FASTQ not in fastq_names:
        raise Exception('CONTROL_FASTQ %s not found' % CONTROL_FASTQ)
    if not isinstance(MAX_PAM_LENGTH,int):
        raise Exception('MAX_PAM_LENGTH should be an integer value, you entered: %s' % MAX_PAM_LENGTH)
    if not isinstance(P5_TIMEPOINT_BARCODE_START,int):
        raise Exception('P5_TIMEPOINT_BARCODE_START should be an integer value, you entered: %s' % P5_TIMEPOINT_BARCODE_START)
    if not isinstance(P7_TIMEPOINT_BARCODE_START,int):
        raise Exception('P7_TIMEPOINT_BARCODE_START should be an integer value, you entered: %s' % P7_TIMEPOINT_BARCODE_START)
    if not isinstance(PAM_LENGTH,int):
        raise Exception('PAM_LENGTH should be an integer value, you entered: %s' % PAM_LENGTH)
    if not isinstance(PAM_START,int):
        raise Exception('PAM_START should be an integer value, you entered: %s' % PAM_START)
    if PAM_ORIENTATION not in ['three_prime', 'five_prime']:
        raise Exception("please enter 'three_prime' or 'five_prime' for PAM_ORIENTATION")
    if PAM_LENGTH > 8 :
        warnings.warn('PAM lengths longer than 8 are not recommended')
    if PAM_LENGTH < 1 :
        raise Exception('please choose a PAM length >0')
    if PAM_START + PAM_LENGTH > MAX_PAM_LENGTH:
        raise Exception('PAM_START (%s) + PAM_LENGTH (%s) is greater than MAX_PAM_LENGTH (%s)' 
                        % (PAM_START,PAM_LENGTH,MAX_PAM_LENGTH))


def control_fastq2count(run_name, 
                        fastq_dir,
                        control_fastq,
                        control_sample,
                        pam_orientation,
                        pam_length,
                        pam_start,
                        max_pam_len = 8, 
                        spacers = {'SPACER1':'GGGCACGGGCAGCTTGCCGG', 'SPACER2':'GTCGCCCTCGAACTTCACCT'},
                        P5_sample_BC_start = 2,
                        P7_sample_BC_start = 2):
    """
    generate raw read counts from a fastq file containing control reads
    just runs fastq2count with a single sample and a single timepoint
    """
    
    sample_fastq = {control_fastq: control_sample}
    
    fastq2count(run_name, 
                None,
                fastq_dir,
                sample_fastq, 
                pam_orientation,
                timepoints=[0, 1], # fake timepoints
                max_pam_len = max_pam_len, 
                spacers = spacers,
                P5_timepoint_BC_start = P5_sample_BC_start,
                P7_timepoint_BC_start = P7_sample_BC_start)

def rawcount2PAMcount(run_name,
                      pam_orientation,
                      pam_length,
                      pam_start,
                      max_pam_length = 8):
    """
    generate counts for the PAMs defined by indicated start position and PAM length
    generate QC plots
    """
    
    df_input = pd.read_csv('output/%s/PAMDA_1_raw_counts.csv' % (run_name))
    
    # generate counts for the PAMs defined by indicated start position and PAM length
    print('grouping counts by indicated PAM bases')
    
    column_sort = {'Sample':'first','Spacer':'first'}
    count_columns = df_input.columns.values[3:]
    new_columns = ['Sample','Spacer','PAM']
    for count_column in count_columns:
        column_sort[count_column] = 'sum'
        new_columns.append(count_column)
    if pam_orientation == 'three_prime':
        df_input['selected_PAM']=df_input['PAM'].str[pam_start:pam_start+pam_length]
    else:
        df_input['selected_PAM']=df_input['PAM'].str[max_pam_length - pam_length - pam_start:
                                                     max_pam_length - pam_start]
    df_list=[]
    for sample in df_input['Sample'].unique().tolist():
        for spacer in df_input['Spacer'].unique().tolist():
            temp_df = df_input[(df_input['Sample']==sample) & (df_input['Spacer']==spacer)]\
                .groupby(['selected_PAM'], as_index = False).agg(column_sort)
            df_list.append(temp_df)
    df = pd.concat(df_list)
    df = df.rename(columns={'selected_PAM':'PAM'})
    df = df.loc[:,new_columns]
    df = df.reset_index(drop=True)    
    
    for sample in df['Sample'].unique().tolist():
        QC_metrics(run_name, df[df['Sample']==sample])
    
    if not os.path.exists('output/%s' % run_name):
        os.makedirs('output/%s' % run_name)

    df.to_csv('output/%s/PAMDA_1_raw_counts_PAM_start_%s_length_%s.csv' %
              (run_name,pam_start,pam_length), index = False)

def QC_metrics(run_name, df):
    """
    Simple QC plots for PAM library composition
    """

    plt.switch_backend('agg')

    if not os.path.exists('figures/%s' % run_name):
        os.makedirs('figures/%s' % run_name)
    
    for spacer in df['Spacer'].unique().tolist():
        df_spacer = df[df['Spacer']==spacer]
        counts = df_spacer['Raw_Counts_1'].sort_values(ascending = False).tolist()
        PAM_count = len(df_spacer)
        top10 = int(0.1*PAM_count)
        bot10 = int(0.9*PAM_count)
        val90 = counts[top10]
        val10 = counts[bot10]
        if val10 == 0:
            ratio9010 = 'nan (10th percentile is zero)'
        else:
            ratio9010 = round(val90/val10,4)
        skewness = round(skew(counts),4)

        if counts[-1] ==0 :
            ratiomaxmin = 'nan (min is zero)'
        else:
            ratiomaxmin = round(counts[0]/counts[-1],4)
        normalized_reads = df_spacer['Raw_Counts_1'].tolist()/df_spacer['Raw_Counts_1'].sum()
        
        plt.figure(figsize=(12,4))
        plt.subplot(1,2,1)
        plt.hist(df_spacer['Raw_Counts_1'],color='Black')
        plt.title('PAM read count histogram for %s \n max:min ratio: %s \n 90:10 ratio: %s \n skewness: %s' % 
            (spacer,ratiomaxmin,ratio9010,skewness) )
        plt.xlabel('Read counts')
        plt.ylabel('PAM count')
        plt.subplot(1,2,2)
        plt.plot([x+1 for x in range(PAM_count)],sorted(normalized_reads),color='Black')
        plt.ylim(bottom=0)
        plt.title('PAM representation for %s \n max:min ratio: %s \n 90:10 ratio: %s \n skewness: %s' % 
            (spacer,ratiomaxmin,ratio9010,skewness) )
        plt.xlabel('PAMs')
        plt.ylabel('Proportion of library')
        plt.tight_layout()
        plt.savefig('figures/%s/%s_PAMDA_library_QC_%s.pdf'%(run_name, run_name, spacer) )
        plt.close()

        print('PAM library %s max:min ratio: %s' % (spacer, ratiomaxmin)) 
        print('PAM library %s 90:10 ratio: %s' % (spacer, ratio9010)) 
        print('PAM library %s skewness: %s' % (spacer, skewness))