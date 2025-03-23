"""
Handles routes, json reading/writing and weather api
"""
import json
import os
import requests
from datetime import datetime
from flask import Blueprint, request, redirect, url_for, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

main = Blueprint('main', __name__)

########################################### JSONS TO STORE DATA ###########################################
GROCERY_FILE = os.path.join(os.path.dirname(__file__), '../data/grocery.json')
MEALPLAN_FILE = os.path.join(os.path.dirname(__file__), '../data/mealplan.json')
TRASH_FILE = os.path.join(os.path.dirname(__file__), '../data/trash.json')

def load_data(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_data(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

########################################### MAIN ROUTE NAD WEATHER ###########################################
def get_weather():

    api_key = os.getenv('API_KEY')
    city = 'Gelsenkirchen'
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    response = requests.get(url)
    data = response.json()

    if data['cod'] == 200:
        weather = {
            "temperature": data['main']['temp'],
            "description": data['weather'][0]['description'],
            "city": city,
            "date": datetime.now().strftime('%Y-%m-%d')
        }
        return weather
    return None

@main.route('/')
def home():
    weather = get_weather()
    trash_status = load_data(TRASH_FILE).get('status', 'No trash tomorrow')
    meals = load_data(MEALPLAN_FILE)
    return render_template('index.html', trash_status=trash_status, weather=weather, meals=meals)

########################################### GROCERY ROUTES ###########################################
@main.route('/grocery', methods=['GET', 'POST'])
def grocery():
    if request.method == 'POST':
        item = request.form.get('item')
        if item:
            items = load_data(GROCERY_FILE)
            new_item = {"id": len(items) + 1, "name": item}
            items.append(new_item)
            save_data(GROCERY_FILE, items)
        return redirect(url_for('main.grocery'))
    
    items = load_data(GROCERY_FILE)
    return render_template('grocery.html', items=items)

@main.route('/grocery', methods=['GET'])
def get_grocery():
    grocery = load_data(GROCERY_FILE)
    return render_template('grocery.html', items=grocery)

@main.route('/grocery/add', methods=['POST'])
def add_grocery():
    data = request.json
    grocery = load_data(GROCERY_FILE)

    new_item = {
        'id': len(grocery) + 1,
        'name': data.get('name')
    }
    grocery.append(new_item)
    save_data(GROCERY_FILE, grocery)
    
    return jsonify(new_item), 201

@main.route('/grocery/delete/<int:item_id>', methods=['POST'])
def delete_grocery(item_id):
    grocery = load_data(GROCERY_FILE)
    grocery = [item for item in grocery if item['id'] != item_id]
    save_data(GROCERY_FILE, grocery)
    
    return jsonify({'status': 'deleted'}), 200

@main.route('/grocery/delete_all', methods=['POST'])
def delete_all_items():
    save_data(GROCERY_FILE, []) 
    return '', 204

########################################### MEALPLAN ROUTES ###########################################
@main.route('/mealplan', methods=['GET', 'POST'])
def mealplan():
    if request.method == 'POST':
        meal_name = request.form.get('meal')
        if meal_name:
            meals = load_data(MEALPLAN_FILE)
            
            days = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
            
            # Find the first available day
            for day in days:
                if len([m for m in meals if m.get('day') == day]) < 1:
                    new_meal = {"id": len(meals) + 1, "name": meal_name, "day": day}
                    meals.append(new_meal)
                    save_data(MEALPLAN_FILE, meals)
                    break
            else:
                # If all days are full, add to Sonstige
                existing_sonstige = [m for m in meals if m.get('day') == 'Sonstige']
                existing_sonstige_names = [meal['name'] for meal in existing_sonstige]
                if meal_name not in existing_sonstige_names:
                    new_meal = {"id": len(meals) + 1, "name": meal_name, "day": 'Sonstige'}
                    meals.append(new_meal)
                    save_data(MEALPLAN_FILE, meals)
                
        return redirect(url_for('main.mealplan'))

    meals = load_data(MEALPLAN_FILE)
    meals_by_day = {day: [] for day in ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']}
    meals_by_day['Sonstige'] = []

    # Group meals by day of the week
    for meal in meals:
        day = meal.get('day')
        if day in meals_by_day:
            meals_by_day[day].append(meal)

    return render_template('mealplan.html', meals_by_day=meals_by_day)

@main.route('/mealplan', methods=['GET'])
def get_mealplan():
    mealplan = load_data(MEALPLAN_FILE)
    return render_template('mealplan.html', meals=mealplan)

@main.route('/mealplan/add', methods=['POST'])
def add_meal():
    data = request.json
    mealplan = load_data(MEALPLAN_FILE)

    new_meal = {
        'id': len(mealplan) + 1,
        'day': data.get('day'),
        'meal': data.get('meal')
    }
    mealplan.append(new_meal)
    save_data(MEALPLAN_FILE, mealplan)

    return jsonify(new_meal), 201

@main.route('/mealplan/delete/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    mealplan = load_data(MEALPLAN_FILE)
    mealplan = [meal for meal in mealplan if meal['id'] != meal_id]
    save_data(MEALPLAN_FILE, mealplan)

    return jsonify({'status': 'deleted'}), 200

@main.route('/mealplan/delete_all', methods=['POST'])
def delete_all_meals():
    save_data(MEALPLAN_FILE, [])
    return '', 204
