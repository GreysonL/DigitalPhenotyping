import os
import sys
import pandas as pd
import numpy as np
from dateutil import tz
from datetime import datetime
import pytz
from pytz import timezone
import calendar
import logging
from common_funcs import *

logger = logging.getLogger(__name__)

def comm_logs_summaries(ID:str, df_text, df_call, stamp_start, stamp_end, tz_str, option):
    """
    Docstring
    Args: Beiwe ID is needed here only for debugging. The other inputs are the outputs from read_comm_logs().
          Option is 'daily' or 'hourly', determining the resolution of the summary stats
          tz_str: timezone where the study was/is conducted
    Return: pandas dataframe of summary stats
    """
    try:
        summary_stats = []
        [start_year, start_month, start_day, start_hour, start_min, start_sec] = stamp2datetime(stamp_start,tz_str)
        [end_year, end_month, end_day, end_hour, end_min, end_sec] = stamp2datetime(stamp_end,tz_str)

        ## determine the starting and ending timestamp again based on the option
        if option == 'hourly':
            table_start = datetime2stamp([start_year, start_month, start_day, start_hour,0,0],tz_str)
            table_end = datetime2stamp([end_year, end_month, end_day, end_hour,0,0],tz_str)
            step_size = 3600
        if option == 'daily':
            table_start = datetime2stamp((start_year, start_month, start_day, 0,0,0),tz_str)
            table_end = datetime2stamp((end_year, end_month, end_day,0,0,0),tz_str)
            step_size = 3600*24

        ## for each chunk, calculate the summary statistics (colmean or count)
        for stamp in np.arange(table_start,table_end+1,step=step_size):
            (year, month, day, hour, minute, second) = stamp2datetime(stamp,tz_str)
            if df_text.shape[0] > 0:
                temp_text = df_text[(df_text["timestamp"]/1000>=stamp)&(df_text["timestamp"]/1000<stamp+step_size)]
                m_len = np.array(temp_text['message length'])
                for k in range(len(m_len)):
                    if m_len[k]=="MMS":
                        m_len[k]=0
                    if isinstance(m_len[k], str)==False:
                        if np.isnan(m_len[k]):
                            m_len[k]=0
                m_len = m_len.astype(int)
                index_s = np.array(temp_text['sent vs received'])=="sent SMS"
                index_r = np.array(temp_text['sent vs received'])=="received SMS"
                index_mms_s = np.array(temp_text['sent vs received'])=="sent MMS"
                index_mms_r = np.array(temp_text['sent vs received'])=="received MMS"
                num_s = sum(index_s.astype(int))
                num_r = sum(index_r.astype(int))
                num_mms_s = sum(index_mms_s.astype(int))
                num_mms_r = sum(index_mms_r.astype(int))
                num_s_tel = len(np.unique(np.array(temp_text['hashed phone number'])[index_s]))
                num_r_tel = len(np.unique(np.array(temp_text['hashed phone number'])[index_r]))
                total_char_s = sum(m_len[index_s])
                total_char_r = sum(m_len[index_r])

            if df_call.shape[0] > 0:
                temp_call = df_call[(df_call["timestamp"]/1000>=stamp)&(df_call["timestamp"]/1000<stamp+step_size)]
                dur_in_sec = np.array(temp_call['duration in seconds'])
                dur_in_sec[np.isnan(dur_in_sec)==True] = 0
                dur_in_min = dur_in_sec/60
                index_in_call = np.array(temp_call['call type'])=="Incoming Call"
                index_out_call = np.array(temp_call['call type'])=="Outgoing Call"
                index_mis_call = np.array(temp_call['call type'])=="Missed Call"
                num_in_call = sum(index_in_call)
                num_out_call = sum(index_out_call)
                num_mis_call = sum(index_mis_call)
                num_uniq_in_call = len(np.unique(np.array(temp_call['hashed phone number'])[index_in_call]))
                num_uniq_out_call = len(np.unique(np.array(temp_call['hashed phone number'])[index_out_call]))
                num_uniq_mis_call = len(np.unique(np.array(temp_call['hashed phone number'])[index_mis_call]))
                total_time_in_call = sum(dur_in_min[index_in_call])
                total_time_out_call = sum(dur_in_min[index_out_call])
            newline = [year, month, day, hour, num_in_call, num_out_call, num_mis_call, num_uniq_in_call, num_uniq_out_call,
                  num_uniq_mis_call, total_time_in_call, total_time_out_call, num_s, num_r, num_mms_s, num_mms_r, num_s_tel,
                  num_r_tel, total_char_s, total_char_r]
            summary_stats.append(newline)
        summary_stats = np.array(summary_stats)
        if option == 'daily':
            summary_stats = np.delete(summary_stats, 3, 1)
            stats_pdframe = pd.DataFrame(summary_stats, columns=['year', 'month', 'day','num_in_call', 'num_out_call', 'num_mis_call',
                    'num_in_caller', 'num_out_caller','num_mis_caller', 'total_mins_in_call', 'total_mins_out_call',
                    'num_s', 'num_r', 'num_mms_s', 'num_mms_r', 'num_s_tel','num_r_tel', 'total_char_s', 'total_char_r'])
        if option == 'hourly':
            stats_pdframe = pd.DataFrame(summary_stats, columns=['year', 'month', 'day','hour','num_in_call', 'num_out_call',
                    'num_mis_call','num_in_caller', 'num_out_caller','num_mis_caller', 'total_mins_in_call', 'total_mins_out_call',
                    'num_s', 'num_r', 'num_mms_s', 'num_mms_r', 'num_s_tel','num_r_tel', 'total_char_s', 'total_char_r'])
        return stats_pdframe
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.debug(str(ID) + ': ' + str(exc_value).replace(",", ""))

# Main function/wrapper should take standard arguments with Beiwe names:
def log_stats_main(study_folder: str, output_folder:str, tz_str: str,  option: str, time_start = None, time_end = None, beiwe_id = None):
    log_to_csv(output_folder)
    logger.info("Begin")
    ## beiwe_id should be a list of str
    if beiwe_id == None:
        beiwe_id = os.listdir(study_folder)
    ## create a record of processed user ID and starting/ending time
    record = []
    for ID in beiwe_id:
        try:
            sys.stdout.write('User: '+ ID + '\n')
            ## read data
            sys.stdout.write("Read in the csv files ..." + '\n')
            text_data, text_stamp_start, text_stamp_end = read_data(ID, study_folder, "texts", tz_str, time_start, time_end)
            call_data, call_stamp_start, call_stamp_end = read_data(ID, study_folder, "calls", tz_str, time_start, time_end)
            ## stamps from call and text should be the stamp_end
            stamp_start = min(text_stamp_start,call_stamp_start)
            stamp_end = max(text_stamp_end, call_stamp_end)
            ## process data
            stats_pdframe = comm_logs_summaries(ID, text_data, call_data, stamp_start, stamp_end, tz_str, option)
            ## save output
            write_all_summaries(ID, stats_pdframe, output_folder)
            [y1,m1,d1,h1,min1,s1] = stamp2datetime(stamp_start,tz_str)
            [y2,m2,d2,h2,min2,s2] = stamp2datetime(stamp_end,tz_str)
            record.append([str(ID),stamp_start,y1,m1,d1,h1,min1,s1,stamp_end,y2,m2,d2,h2,min2,s2])
        except:
            if text_data.shape[0]>0 or call_data.shape[0]>0:
                logger.debug("There is a problem unrelated to data for user %s." % str(ID))
    logger.info("End")
    ## generate the record file together with logger and comm_logs.csv
    record = pd.DataFrame(np.array(record), columns=['ID','start_stamp','start_year','start_month','start_day','start_hour','start_min','start_sec',
                          'end_stamp','end_year','end_month','end_day','end_hour','end_min','end_sec'])
    record.to_csv(output_folder + "/record.csv",index=False)
    temp = pd.read_csv(output_folder + "/log.csv")
    if temp.shape[0]==3:
      print("Finished without any warning messages.")
    else:
      print("Finished. Please check log.csv for warning messages.")

## test the code
study_folder = 'F:/DATA/hope'
output_folder = 'C:/Users/glius/Downloads/hope_log'
tz_str = 'America/New_York'
option = 'hourly'
log_stats_main(study_folder,output_folder,tz_str,option)
