from flask import Flask, render_template, request
import pandas as pd
import os

app = Flask(__name__)

def prep_data(time_range_in_mins, include_bluelight_flag, include_ambientlight_flag, user):
   # Set threshold for displaying
   if user == 0:
      HEVthreshold = 0.4
   elif user == 1:
      HEVthreshold = 0.2

   # Get current directory
   current_directory = os.getcwd()
   data_directory = current_directory+'\data\dataLog3.csv'

   # Import CSV
   df = pd.read_csv(data_directory)

   # Shift everything down by 1, and make replace first row with column names
   df.index = df.index+1
   df.loc[0] = df.columns
   df.sort_index(inplace=True)
   df = df[df.columns[0:4]].copy()
   df.columns = ['timeNow','harmfulHEVIntensity', 'overallLightIntensity', 'artificialLightBool']

   # Convert values to appropriate data types
   df['timeNow'] = pd.to_datetime(df['timeNow']).copy()
   df[['harmfulHEVIntensity', 'overallLightIntensity', 'artificialLightBool']] = df[['harmfulHEVIntensity', 'overallLightIntensity', 'artificialLightBool']].apply(pd.to_numeric)
   
   # Filter down by appropriate time length
   time_of_last_collection = df['timeNow'].iloc[-1]
   df = df.loc[((time_of_last_collection - df.timeNow).dt.total_seconds()/60) < time_range_in_mins].copy()
   

   # Generate list data
   data = []
   harmfulHEVIntensity_data = list(df['harmfulHEVIntensity'])
   overallLightIntensity_data = list(df['overallLightIntensity'])
   data.append(harmfulHEVIntensity_data)
   data.append(overallLightIntensity_data)
   data.append([HEVthreshold for x in harmfulHEVIntensity_data])
   labels = list(df['timeNow'].dt.strftime('%Y-%m-%d, %H:%M'))

   return labels, data


@app.route('/', methods=['GET', 'POST'])
def hello_world_3():
   print(request.method)
   if request.method == 'POST':
      if request.form.get('time_range_button') == 'Last 15 mins':
         labels_data, values_data = prep_data(15,0,0,0)
         time_range_text = '15 mins'

      elif request.form.get('time_range_button') == 'Last 24 hours':
         labels_data, values_data = prep_data(60*24,0,0,0)
         time_range_text = '24 hours'

   elif request.method == 'GET':
      time_range_text = '1 hour'
      labels_data, values_data = prep_data(60,0,0,0)
   return render_template('hello.html', labels=labels_data, harmful_values=values_data[0], overall_values=values_data[1], HEVthreshold_values = values_data[2], time_range_text = time_range_text)

@app.route('/bla')
def hello_world_2():
   return 'hello worldbla'

if __name__ == '__main__':
    app.debug = True
    app.run()
    app.run(debug = True)