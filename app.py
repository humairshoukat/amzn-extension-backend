from flask import Flask, request, jsonify
import requests
import numpy as np
import pandas as pd
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

API_KEY = '1o73nko8s96t6f2k15hi5asshrbj0lauskgno9ek8j11vkn0u5u204h6obuugnv8'
API_URL = 'https://api.keepa.com/product?key={}&domain=1&asin={}'

def detect_ip_risk(buybox_data, sellerid_history, price_history):
    buybox_threshold = 0.2  # 20% change
    price_threshold = 0.3   # 30% change
    seller_change_threshold = 5  # 5 seller changes in a short period

    buybox_changes = np.diff(buybox_data) / buybox_data[:-1]
    significant_buybox_changes = np.abs(buybox_changes) > buybox_threshold

    price_changes = np.diff(price_history) / price_history[:-1]
    significant_price_changes = np.abs(price_changes) > price_threshold

    unique_sellers, seller_counts = np.unique(sellerid_history, return_counts=True)
    frequent_sellers = seller_counts > seller_change_threshold

    risk_factors = {
        'significant_buybox_changes': int(significant_buybox_changes.sum()),
        'significant_price_changes': int(significant_price_changes.sum()),
        'frequent_sellers': int(frequent_sellers.sum())
    }

    ip_risk = any(value > 0 for value in risk_factors.values())
    
    return ip_risk, risk_factors

@app.route('/detect_ip_risk', methods=['POST'])
def detect_ip_risk_endpoint():
    asin = request.json.get('asin')
    response = requests.get(API_URL.format(API_KEY, asin))
    json_data = response.json()
    data = json_data['products'][0]

    if 'products' not in json_data or len(json_data['products']) == 0:
        return jsonify({'error': 'No products found'}), 404

    # Extract buybox data, sellerid history, and price history
    buybox_data = data['csv'][0][::2]  # Every even index
    sellerid_history = data['csv'][0][1::2]  # Every odd index
    price_history = data['csv'][1][1::2]  # Every odd index

    price_history = price_history[:len(buybox_data)]

    df = pd.DataFrame({
        "Buybox Data": buybox_data,
        "Sellerid History": sellerid_history,
        "Price History": price_history
    })

    buybox_data = df["Buybox Data"]
    sellerid_history = df["Sellerid History"]
    price_history = df["Price History"]

    buybox_data = pd.Series(buybox_data).fillna(method='ffill').tolist()
    sellerid_history = pd.Series(sellerid_history).replace(-1, np.nan).fillna(method='ffill').tolist()
    price_history = pd.Series(price_history).replace(-1, np.nan).fillna(method='ffill').tolist()

    ip_risk, risk_factors = detect_ip_risk(buybox_data, sellerid_history, price_history)

    if not ip_risk:
        response_risk_factors = ['None']
    else:
        response_risk_factors = [key for key, value in risk_factors.items() if value > 0]

    return jsonify(ip_risk=ip_risk, risk_factors=risk_factors)

if __name__ == '__main__':
    app.run()