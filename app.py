import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout
import matplotlib.pyplot as plt

# Define functions for loading data, training model, and making predictions
def load_data(ticker):
    try:
        data = yf.download(tickers=ticker, period='6mo', interval='1h')
        data['Direction'] = np.where(data['Close'] > data['Open'], 1, 0)
        return data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def preprocess_data(data):
    close_price = data['Close'].values
    close_price = close_price.reshape(-1, 1)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(close_price)
    return scaled_data, scaler

def create_dataset(dataset, time_step=60):
    X, y = [], []
    for i in range(len(dataset) - time_step - 1):
        X.append(dataset[i:(i + time_step), 0])
        y.append(dataset[i + time_step, 0])
    return np.array(X), np.array(y)

def build_model(time_step):
    model = Sequential()
    model.add(LSTM(50, return_sequences=True, input_shape=(time_step, 1)))
    model.add(Dropout(0.2))
    model.add(LSTM(50, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(25))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

def predict_next_24_hours(model, last_data, scaler):
    predictions = []
    directions = []
    input_data = last_data.copy()

    for _ in range(24):  # Predict for the next 24 hours
        pred = model.predict(input_data)
        pred_unscaled = scaler.inverse_transform(pred)
        predictions.append(pred_unscaled[0][0])

        # Determine direction: up (1) if the price is predicted to rise, down (0) otherwise
        last_price = scaler.inverse_transform(input_data[0])[-1][0]
        direction = "UP" if pred_unscaled[0][0] > last_price else "DOWN"
        directions.append(direction)

        # Update input data by appending the predicted price
        new_input = np.append(input_data[0][1:], pred, axis=0)
        input_data = new_input.reshape(1, -1, 1)

    return predictions, directions

def main():
    st.title('Next 24-Hour Stock Price and Direction Prediction')

    # Sidebar for ticker input
    ticker = st.sidebar.text_input('Enter Stock Type:', 'AMZN')

    # Fetch and display current data
    data = load_data(ticker)
    
    if not data.empty:
        st.subheader(f'Current Prices for {ticker}')
        st.write(data.tail())  # Display last few records from the data for current prices
        
        # Preprocess data for model
        scaled_data, scaler = preprocess_data(data)
        time_step = 60
        train_size = int(len(scaled_data) * 0.8)
        train_data = scaled_data[:train_size, :]
        test_data = scaled_data[train_size:, :]

        X_train, y_train = create_dataset(train_data, time_step)
        X_test, y_test = create_dataset(test_data, time_step)

        X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
        X_test = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)

        # Build and train the LSTM model
        model = build_model(time_step)
        model.fit(X_train, y_train, batch_size=64, epochs=50, verbose=1)
        


        # Next 24-hour predictions
        last_60_days = scaled_data[-time_step:]
        last_60_days = last_60_days.reshape(1, -1, 1)
        next_24_hours, next_24_directions = predict_next_24_hours(model, last_60_days, scaler)

        # Dataframe for next 24 hours
        future_times = pd.date_range(data.index[-1], periods=24, freq='H')
        prediction_df = pd.DataFrame({
            'Date/Time': future_times,
            'Predicted Price': next_24_hours,
            'Predicted Direction': next_24_directions
        })

        # Display next 24-hour predictions
        st.subheader(f'Predicted Stock Prices for the Next 24 Hours for {ticker}')
        st.dataframe(prediction_df)

        # Plot: Next 24-Hour Predicted Prices
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.plot(future_times, next_24_hours, label='Next 24-Hour Predictions', color='orange', linestyle='--')
        ax.set_title(f'{ticker} Stock Price Prediction for Next 24 Hours')
        ax.set_xlabel('Date/Time')
        ax.set_ylabel('Stock Price')
        ax.legend()

        st.pyplot(fig)

        # Plot: Predicted Stock Direction
        fig2, ax2 = plt.subplots(figsize=(16, 8))
        ax2.plot(future_times, [1 if d == "UP" else 0 for d in next_24_directions], color='green', marker='o', linestyle='-')
        ax2.set_title('Predicted Stock Direction (1: UP, 0: DOWN)')
        ax2.set_xlabel('Date/Time')
        ax2.set_ylabel('Direction')
        ax2.set_yticks([0, 1])
        ax2.set_yticklabels(['DOWN', 'UP'])
        ax2.grid(True)

        st.pyplot(fig2)

if __name__ == "__main__":
    main()
