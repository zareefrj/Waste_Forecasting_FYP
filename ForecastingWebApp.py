import streamlit as st
import pandas as pd
from prophet import Prophet
from prophet.plot import plot_plotly
import datetime
import requests
from sklearn.metrics import mean_absolute_error, mean_squared_error
import math

# Define a dictionary to map device names to their device IDs
device_id_mapping = {
        "Level Sensor 1": "ee5ed210-7174-11ed-a3e8-cd953d903e76",
	"Level Sensor 2": "7484aaf0-7174-11ed-a3e8-cd953d903e76",
	"Level Sensor 3": "89854130-7174-11ed-861d-25ac767dd88b",
	"Level Sensor 4": "a3676240-7174-11ed-a3e8-cd953d903e76",
	"Level Sensor 5": "b8206830-7174-11ed-8b62-e9eba22b9df6",
	"Level Sensor 6": "bf2fa870-7174-11ed-8b62-e9eba22b9df6",
	"Level Sensor 7": "cbe57130-7174-11ed-861d-25ac767dd88b",
	"Level Sensor 8": "d455a100-7174-11ed-861d-25ac767dd88b",
	"Level Sensor 9": "dbecfd00-7174-11ed-a3e8-cd953d903e76",
	"Level Sensor 10": "e3806160-7174-11ed-8b62-e9eba22b9df6",
	"Level Sensor 11": "cb254a10-578c-11ed-b28a-eb999599ab40",
	"Level Sensor 13": "d226fe80-7514-11ed-b24c-ab40826c689b"
        # Add more mappings as needed
    }

#access token copied from thingsboard user profile for GET request later
#access_token="Bearer..."

#function to convert the current time to UNIX timestamp in ms
def get_endTs(): 
    end_ts = datetime.datetime.now()
    end_ts_unix_ms = int(end_ts.timestamp() * 1000)
    #print(end_ts_unix_ms) #For double check the value
    return end_ts_unix_ms

# Function to run the forecast and plot graph
def predict(data):

    # Predict forecast with Prophet
    df_train = data[['Timestamp', 'Level']]
    df_train = df_train.rename(columns={"Timestamp": "ds", "Level": "y"})

    m = Prophet()
    m.fit(df_train)

    # Allow prediction up to 1 week (7 days)
    future = m.make_future_dataframe(periods=7, freq='D')
    forecast = m.predict(future)

    st.success("Forecasting done ! Hooray !")

    st.subheader(f'Waste Forecast for {selected_device_name}')

    #show prediction table
    prediction_table = forecast.tail(7) #show the next 7 days
    prediction_table = prediction_table[['ds', 'yhat']] # Keep only the desired columns
    prediction_table.rename(columns={"ds": "Date", "yhat": "Predicted Value"}, inplace=True)
    st.dataframe(prediction_table)
    
    #show prediction graph
    fig1 = plot_plotly(m, forecast)
    st.plotly_chart(fig1)

    #forecast components
    st.subheader(f'Forecast Components for {selected_device_name}')
    with st.expander("Click to read more on the components"):
        st.write("The forecast components represent the individual factors contributing to the overall forecast.These components include trend, weekly seasonality, and any other patterns identified by the model.")
    
    fig2 = m.plot_components(forecast)
    st.write(fig2)

    # Calculate performance metrics
    MAE = mean_absolute_error(data['Level'], forecast['yhat'][:-7]) #exclude the last 7 values in yhat, these are the prediction values
    RMSE = math.sqrt(mean_squared_error(data['Level'], forecast['yhat'][:-7]))

    # Display performance metrics
    st.subheader('Performance Metrics of the Forecast')
    with st.expander("Click to read more on the metrics"):
        st.write("The lower the value of the metrics, the better the performance of the prediction model. Mean Absolute Error (MAE): Measures the average absolute difference between the predicted values and the actual values. Mean Squared Error (MSE): Measures the squared average squared difference between the predicted values and the actual values.")
    st.write(f'Mean Absolute Error: {MAE}')
    st.write(f'Root Mean Squared Error: {RMSE}')

    st.balloons()

# Function to get the time series data from thingsboard via GET request
@st.cache_data
def get_timeseries(deviceID):

    # ThingsBoard API endpoint
    url = "https://thingsboard.cloud:443/api/plugins/telemetry/DEVICE/"+deviceID+"/values/timeseries"
    params = {
        "keys": "Level",
        "startTs": 1697285822857, #the start_ts is set to 2023-10-14 20:14:58.294887
        "endTs":   get_endTs(), #converts current time to UNIX timestamp in milliseconds
        "limit":10000,
    }

    # Headers with authorization token
    headers = {
        "Authorization": st.secrets['access_token']
        #"Authorization": access_token
    }

    # Make the API request
    response = requests.get(url, params=params, headers=headers)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        return response.json()

    if response.status_code == 401:
         st.error("Unauthorized Access ! Please check your access token.")
    else:
        st.error(f"Error: {response.status_code} - {response.text}")
        return None

# Function to modify the json format to panda data frames
@st.cache_data
def modify_json(json_data):
    try:
            # Extract 'Level' data from JSON
            level_data = json_data.get("Level", [])

            # Create DataFrame
            data = pd.DataFrame(level_data)

            # Convert timestamps to datetime format
            data['Timestamp'] = pd.to_datetime(data['ts'], unit='ms')

            # Drop unnecessary columns
            data = data[['Timestamp', 'value']]

            # Rename columns
            data.columns = ['Timestamp', 'Level']

            # Drop rows with missing timestamps
            data.dropna(subset=['Timestamp'], inplace=True)

            st.write(f"No. of data in JSON file: {len(data)}")
            # run the predictions
            predict(data)
        
    except Exception as e:
            st.error(f"Error: {e}")

########### Streamlit app setup ################
st.set_page_config(layout='wide')  # Adjust page config

# Header
st.title('Waste Forecasting')

# User selects a device
selected_device_name = st.selectbox("Select a device", list(device_id_mapping.keys()))

# begin forecast when user press button
if st.button("Forecast Now !"):
     with st.spinner("Forecasting... Please wait."):
        #get raw telemetry
        raw_telemetry = get_timeseries(device_id_mapping.get(selected_device_name))

        # only start modifying when there is raw telemetry
        if raw_telemetry is not None:
            # modify the json file
            data = modify_json(raw_telemetry)