from asyncio.windows_events import NULL
from flask import Flask, render_template, request
import pandas as pd
import numpy as np
import os
from scipy.ndimage import gaussian_filter1d

app = Flask(__name__)

def prep_data(time_range_in_mins, filter_flag):
   # Set threshold for displaying
   Overallthreshold = 0.6
   HEVthreshold = 0.4

   # Get current directory
   current_directory_split = os.getcwd().split('\\')
   data_directory = ''
   for i in current_directory_split[:-1]: # get the embeddedsys folder
      data_directory += i + '\\'
   data_directory = data_directory + 'laptopClient\\datalog.csv'

   # Import CSV
   df = pd.read_csv(data_directory)

   # Shift everything down by 1, and replace first row with column names
   df.index = df.index+1
   df.loc[0] = df.columns
   df.sort_index(inplace=True)
   df = df[df.columns[0:4]].copy()
   df.columns = ['timeNow','harmfulHEVIntensity', 'overallLightIntensity', 'artificialLightBool']

   # Convert values to appropriate data types
   df['timeNow'] = pd.to_datetime(df['timeNow']).copy()
   df[['harmfulHEVIntensity', 'overallLightIntensity', 'artificialLightBool']] = df[['harmfulHEVIntensity', 'overallLightIntensity', 'artificialLightBool']].apply(pd.to_numeric)
   
   # Filter down by appropriate time length
   time_of_last_collection = []
   time_of_last_collection = df['timeNow'].iloc[-1]
   df = df.loc[((time_of_last_collection - df.timeNow).dt.total_seconds()/60) < time_range_in_mins].copy()

   # Gaussian filter the data
   df['harmfulHEVIntensity'] = gaussian_filter1d(df['harmfulHEVIntensity'].values, 5)
   df['overallLightIntensity'] = gaussian_filter1d(df['overallLightIntensity'].values, 5)

   if filter_flag:
      df['harmfulHEVIntensity'] = df['harmfulHEVIntensity'].apply(lambda x: x if x >= HEVthreshold-0.01 else 0)
      df['overallLightIntensity'] = df['overallLightIntensity'].apply(lambda x: x if x >= Overallthreshold-0.01 else 0)

   # Generate list data
   data = {}
   labels = {}
   harmfulHEVIntensity_data = list(df['harmfulHEVIntensity'])
   overallLightIntensity_data = list(df['overallLightIntensity'])
   data['HEV_values'] = harmfulHEVIntensity_data
   data['Overall_values'] = overallLightIntensity_data
   data['HEVThreshold_values'] = [HEVthreshold for x in harmfulHEVIntensity_data]
   data['OverallThreshold_values'] = [Overallthreshold for x in harmfulHEVIntensity_data]
   labels['Last_Collection_Time'] = [list(df['timeNow'].dt.strftime('%Y-%m-%d'))[-1], time_of_last_collection.strftime('%H:%M')]
   labels['Label_values'] = list(df['timeNow'].dt.strftime('%H:%M'))

   # Calculate perc of time more than threshold
   number_of_entries = len(df)
   number_of_entries_more_than_threshold_HEV = len(df.loc[df.harmfulHEVIntensity > HEVthreshold])
   number_of_entries_more_than_threshold_Overall = len(df.loc[df.overallLightIntensity > Overallthreshold])
   data['HEV_overthresh_perc'] = round(number_of_entries_more_than_threshold_HEV/number_of_entries*100)
   data['Overall_overthresh_perc'] = round(number_of_entries_more_than_threshold_Overall/number_of_entries*100)
   
   # Determine overthresh level
   if data['HEV_overthresh_perc'] > 30:
      data['HEV_overthresh_level'] = 'High'
      data['recommendation_text'] = 'Try to reduce electronic device usage and focus on objects about 20 feet away to relax your eyes! At the same time, '
   else:
      data['HEV_overthresh_level'] = 'Low'
      data['recommendation_text'] = 'Blue light levels are low, keep it up! At the same time, '
   if data['Overall_overthresh_perc'] > 30:
      data['Overall_overthresh_level'] = 'High'
      data['recommendation_text'] += 'overall light exposure is high, try to seek shelter!'
   else:
      data['Overall_overthresh_level'] = 'Low'
      data['recommendation_text'] += 'overall light exposure is low, great job!'

   return labels, data

# By default, we will call this function which presents all the data
@app.route('/', methods=['GET', 'POST'])
def disp_graph_user():
   print(request.method)
   
   # If any of the time range buttons are pressed
   if request.method == 'POST':
      
      # We will specify the time range
      if request.form.get('time_range_button') == 'Last 15 mins':
         labels_data, values_data = prep_data(15,0)
         time_range_text = '15 mins'

      elif request.form.get('time_range_button') == 'Last 1 hour':
         labels_data, values_data = prep_data(60,0)
         time_range_text = '1 hour'

   # Else, by default we will show 1 hour worth of data
   elif request.method == 'GET':
      time_range_text = '1 hour'
      labels_data, values_data = prep_data(60,0)

   # Return a response with the summary_simplified html template
   return render_template('summary.html', \
      labels=labels_data['Label_values'], \
      harmful_values=values_data['HEV_values'], \
      overall_values=values_data['Overall_values'], \
      HEVthreshold_values = values_data['HEVThreshold_values'], \
      Overallthreshold_values = values_data['OverallThreshold_values'], \
      time_range_text = time_range_text, \
      date = labels_data['Last_Collection_Time'][0], \
      last_collection_time = labels_data['Last_Collection_Time'][1],
      bluelight_perc =  values_data['HEV_overthresh_perc'],\
      overalllight_perc =  values_data['Overall_overthresh_perc'],\
      bluelight_level = values_data['HEV_overthresh_level'],\
      overalllight_level = values_data['Overall_overthresh_level'],\
      recommendation_text = values_data['recommendation_text'],\
      time_range_action = "\\"
      )

# If requested, we will call this function which presents only the data that are above the threshold
@app.route('/simplified', methods=['GET', 'POST'])
def disp_graph_user_simplified():
   print(request.method)
   
   # If any of the time range buttons are pressed
   if request.method == 'POST':
      
      # We will specify the time range
      if request.form.get('time_range_button') == 'Last 15 mins':
         labels_data, values_data = prep_data(15,1)
         time_range_text = '15 mins'

      elif request.form.get('time_range_button') == 'Last 1 hour':
         labels_data, values_data = prep_data(60,1)
         time_range_text = '1 hour'
   
   # Else, by default we will show 1 hour worth of data
   elif request.method == 'GET':
      time_range_text = '1 hour'
      labels_data, values_data = prep_data(60,1)

   # Return a response with the summary_simplified html template
   return render_template('summary.html', \
      labels=labels_data['Label_values'], \
      harmful_values=values_data['HEV_values'], \
      overall_values=values_data['Overall_values'], \
      HEVthreshold_values = values_data['HEVThreshold_values'], \
      Overallthreshold_values = values_data['OverallThreshold_values'], \
      time_range_text = time_range_text, \
      date = labels_data['Last_Collection_Time'][0], \
      last_collection_time = labels_data['Last_Collection_Time'][1],
      bluelight_perc =  values_data['HEV_overthresh_perc'],\
      overalllight_perc =  values_data['Overall_overthresh_perc'],\
      bluelight_level = values_data['HEV_overthresh_level'],\
      overalllight_level = values_data['Overall_overthresh_level'],\
      recommendation_text = values_data['recommendation_text'], \
      time_range_action = "\\simplified"
      )

if __name__ == '__main__':
    app.debug = True
    app.run()
    app.run(debug = True)