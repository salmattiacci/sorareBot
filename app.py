import os
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from flask import Flask, jsonify

app = Flask(__name__)

# Fetch the API key from the environment variable
api_key = os.getenv('SORARE_API_KEY')

if not api_key:
    print("API key is missing. Set the SORARE_API_KEY environment variable.")

# Function to get your players
def get_my_players(api_key):
    url = 'https://api.sorare.com/graphql'
    headers = {'Authorization': f'Bearer {api_key}'}
    query = '''
    {
        me {
            cards {
                id
                player {
                    id
                    name
                    team {
                        name
                    }
                }
                price
                purchasePrice
            }
        }
    }
    '''
    response = requests.post(url, json={'query': query}, headers=headers)
    return response.json()


# Function to sell a player
def sell_player(player_id, price, api_key):
    url = 'https://api.sorare.com/graphql'
    headers = {'Authorization': f'Bearer {api_key}'}
    mutation = f'''
    mutation {{
        sellCard(cardId: "{player_id}", price: {price}) {{
            card {{
                id
            }}
        }}
    }}
    '''
    response = requests.post(url, json={'query': mutation}, headers=headers)
    return response.json()


# Function to buy a player
def buy_player(player_id, api_key, price):
    url = 'https://api.sorare.com/graphql'
    headers = {'Authorization': f'Bearer {api_key}'}

    mutation = f'''
    mutation {{
        buyCard(cardId: "{player_id}", price: {price}) {{
            card {{
                id
                player {{
                    name
                }}
                price
            }}
        }}
    }}
    '''

    response = requests.post(url, json={'query': mutation}, headers=headers)
    if response.status_code == 200:
        card = response.json()['data']['buyCard']['card']
        print(f"Bought player {card['player']['name']} for {card['price']}")
        return card
    else:
        print(f"Error purchasing player {player_id}: {response.status_code} {response.text}")
        return None


# Function to sell profitable players
def sell_profitable_players(api_key):
    players = get_my_players(api_key)['data']['me']['cards']
    for player in players:
        purchase_price = float(player['purchasePrice'])
        current_price = float(player['price'])
        if current_price >= purchase_price * 1.1:  # Selling with a 10% profit
            print(f"Attempting to sell {player['player']['name']} for {current_price}")
            sell_player(player['id'], current_price, api_key)


# Function to find and buy players based on budget
def find_and_buy_players(api_key, budget, profit_margin=1.1):
    url = 'https://api.sorare.com/graphql'
    query = '''
    {
        market {
            cards(first: 10) {
                edges {
                    node {
                        id
                        price
                        player {
                            id
                            name
                        }
                    }
                }
            }
        }
    }
    '''
    response = requests.post(url, json={'query': query}, headers={'Authorization': f'Bearer {api_key}'})
    cards = response.json()['data']['market']['cards']['edges']

    for card in cards:
        price = float(card['node']['price'])
        if price <= budget:  # If the price is within the budget
            expected_sale_price = price * profit_margin
            print(f"Found {card['node']['player']['name']} for {price}, with expected sale at {expected_sale_price}")
            buy_player(card['node']['id'], api_key, price)


# Flask endpoint to trigger buy/sell manually (optional, just to verify)
@app.route('/')
def home():
    return "Sorare Bot is running!"


# Scheduler for selling players
def scheduled_sell(api_key):
    sell_profitable_players(api_key)


# Scheduler for buying players
def scheduled_buy(api_key, budget):
    find_and_buy_players(api_key, budget)


# Setting up the scheduler
if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_sell, 'interval', minutes=10, args=[api_key])  # Every 10 minutes
    scheduler.add_job(scheduled_buy, 'interval', hours=6, args=[api_key, 1000])  # Every 6 hours with 1000 budget
    scheduler.start()
