"""
Handles routes, json reading/writing and weather api
"""
import datetime
import json
import os
import random
import re
import requests
from flask import Blueprint, request, redirect, url_for, jsonify, render_template

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

########################################### WEATHER (Open-Meteo, kein API-Key nötig) ###########################################
_WMO_CODES = {
    0:  ("Klar",                   "☀️"),
    1:  ("Überwiegend klar",       "🌤️"),
    2:  ("Teilweise bewölkt",      "⛅"),
    3:  ("Bewölkt",                "☁️"),
    45: ("Nebel",                  "🌫️"),
    48: ("Gefrierender Nebel",     "🌫️"),
    51: ("Leichter Nieselregen",   "🌦️"),
    53: ("Nieselregen",            "🌦️"),
    55: ("Starker Nieselregen",    "🌧️"),
    61: ("Leichter Regen",         "🌧️"),
    63: ("Regen",                  "🌧️"),
    65: ("Starker Regen",          "🌧️"),
    71: ("Leichter Schneefall",    "🌨️"),
    73: ("Schneefall",             "❄️"),
    75: ("Starker Schneefall",     "❄️"),
    80: ("Leichte Schauer",        "🌦️"),
    81: ("Schauer",                "🌧️"),
    82: ("Starke Schauer",         "⛈️"),
    95: ("Gewitter",               "⛈️"),
    96: ("Gewitter mit Hagel",     "⛈️"),
    99: ("Gewitter m. star. Hagel","⛈️"),
}

def get_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=51.5177&longitude=7.0857"
        "&current=temperature_2m,weather_code"
        "&timezone=Europe%2FBerlin"
    )
    try:
        data = requests.get(url, timeout=5).json()
        current = data.get('current', {})
        code = current.get('weather_code', 0)
        temp = current.get('temperature_2m')
        desc, icon = _WMO_CODES.get(code, ("Unbekannt", "❓"))
        return {
            "temperature": round(temp, 1) if temp is not None else "?",
            "description": desc,
            "icon": icon,
            "city": "Gelsenkirchen",
        }
    except Exception:
        return None

@main.route('/')
def home():
    weather = get_weather()
    meals = load_data(MEALPLAN_FILE)
    try:
        with open(TRASH_FILE, 'r') as f:
            trash_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        trash_data = {}

    return render_template('index.html', trash_data=trash_data, weather=weather, meals=meals)

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

@main.route('/mealplan/move/<int:meal_id>', methods=['POST'])
def move_meal(meal_id):
    valid = ['Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag','Sonstige']
    new_day = (request.json or {}).get('day', '')
    if new_day not in valid:
        return jsonify({'status': 'invalid'}), 400
    meals = load_data(MEALPLAN_FILE)
    for meal in meals:
        if meal['id'] == meal_id:
            meal['day'] = new_day
            break
    save_data(MEALPLAN_FILE, meals)
    return jsonify({'status': 'moved'})

########################################### RECIPE ROUTES ###########################################
RECIPES_FILE    = os.path.join(os.path.dirname(__file__), '../data/recipes.json')
CATEGORIES_FILE = os.path.join(os.path.dirname(__file__), '../data/categories.json')
STAPLES_FILE    = os.path.join(os.path.dirname(__file__), '../data/staples.json')
PANTRY_FILE     = os.path.join(os.path.dirname(__file__), '../data/pantry.json')
UPLOAD_FOLDER   = os.path.join(os.path.dirname(__file__), 'static', 'uploads')

_DEFAULT_CATEGORIES = [
    'Pasta', 'Suppe', 'Backen', 'Vegetarisch', 'Kalorienarm',
    'Reisgericht', 'Hauptgericht', 'Dessert', 'Sonstige', 'Snacks', 'Frühstück',
]

def load_categories():
    try:
        with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return _DEFAULT_CATEGORIES

@main.route('/recipes')
def recipes():
    all_recipes = load_data(RECIPES_FILE)
    categories  = load_categories()
    q          = request.args.get('q', '').lower().strip()
    cat        = request.args.get('cat', '')
    ingredient = request.args.get('ingredient', '').lower().strip()
    fav        = request.args.get('fav', '')

    all_recipes = [_normalize_recipe(r) for r in all_recipes]
    filtered = all_recipes
    if fav:
        filtered = [r for r in filtered if r.get('favorite', False)]
    if q:
        filtered = [r for r in filtered if q in r['name'].lower()]
    if cat:
        filtered = [r for r in filtered if cat in (r.get('category') if isinstance(r.get('category'), list) else [r.get('category', '')])]
    if ingredient:
        filtered = [r for r in filtered if any(
            ingredient in i['name'].lower() for i in r.get('ingredients', [])
        )]

    return render_template('recipes.html', recipes=filtered, categories=categories,
                           q=q, cat=cat, ingredient=ingredient, fav=fav)

def _scale_amount(amount_str, factor):
    if factor == 1.0:
        return amount_str
    m = re.match(r'^(\d+(?:[.,]\d+)?)(.*)', amount_str.strip())
    if not m:
        return amount_str
    num = float(m.group(1).replace(',', '.'))
    scaled = num * factor
    formatted = str(int(scaled)) if scaled == int(scaled) else str(round(scaled, 2)).replace('.', ',')
    return formatted + m.group(2)

def _normalize_recipe(r):
    r = dict(r)
    cat = r.get('category', [])
    r['category'] = cat if isinstance(cat, list) else ([cat] if cat else [])
    return r

def _pantry_match(ingredient_name, pantry_names):
    ing = ingredient_name.lower().strip()
    return any(p in ing or ing in p for p in pantry_names)

@main.route('/recipes/<int:recipe_id>')
def recipe_detail(recipe_id):
    recipe = next((r for r in load_data(RECIPES_FILE) if r['id'] == recipe_id), None)
    if not recipe:
        return redirect(url_for('main.recipes'))
    return render_template('recipe_detail.html', recipe=_normalize_recipe(recipe))

@main.route('/recipes/add', methods=['GET', 'POST'])
def recipe_add():
    categories = load_categories()
    if request.method == 'POST':
        all_recipes = load_data(RECIPES_FILE)
        new_id = max((r['id'] for r in all_recipes), default=0) + 1

        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                ext = os.path.splitext(secure_filename(file.filename))[1].lower()
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file.save(os.path.join(UPLOAD_FOLDER, f"{new_id}{ext}"))
                image_path = f"uploads/{new_id}{ext}"

        amounts = request.form.getlist('ingredient_amount')
        names   = request.form.getlist('ingredient_name')
        ingredients = [
            {'amount': a.strip(), 'name': n.strip()}
            for a, n in zip(amounts, names) if n.strip()
        ]
        steps = [s.strip() for s in request.form.getlist('step') if s.strip()]

        all_recipes.append({
            'id':        new_id,
            'name':      request.form.get('name', '').strip(),
            'category':  request.form.getlist('category'),
            'prep_time': request.form.get('prep_time', ''),
            'servings':  request.form.get('servings', ''),
            'image':     image_path,
            'ingredients': ingredients,
            'steps':     steps,
        })
        save_data(RECIPES_FILE, all_recipes)
        return redirect(url_for('main.recipe_detail', recipe_id=new_id))

    return render_template('recipe_add.html', categories=categories)

@main.route('/recipes/delete/<int:recipe_id>', methods=['POST'])
def recipe_delete(recipe_id):
    all_recipes = load_data(RECIPES_FILE)
    recipe = next((r for r in all_recipes if r['id'] == recipe_id), None)
    if recipe and recipe.get('image'):
        img = os.path.join(UPLOAD_FOLDER, os.path.basename(recipe['image']))
        if os.path.exists(img):
            os.remove(img)
    save_data(RECIPES_FILE, [r for r in all_recipes if r['id'] != recipe_id])
    return redirect(url_for('main.recipes'))

@main.route('/recipes/search')
def recipe_search():
    q = request.args.get('q', '').lower().strip()
    def first_cat(r):
        cat = r.get('category', [])
        cats = cat if isinstance(cat, list) else ([cat] if cat else [])
        return cats[0] if cats else ''
    matches = [
        {'id': r['id'], 'name': r['name'], 'category': first_cat(r)}
        for r in load_data(RECIPES_FILE)
        if q and q in r['name'].lower()
    ][:8]
    return jsonify(matches)

@main.route('/recipes/<int:recipe_id>/add_to_mealplan', methods=['POST'])
def recipe_add_to_mealplan(recipe_id):
    all_recipes = load_data(RECIPES_FILE)
    recipe = next((r for r in all_recipes if r['id'] == recipe_id), None)
    if not recipe:
        return jsonify({'status': 'not found'}), 404
    for r in all_recipes:
        if r['id'] == recipe_id:
            r['last_cooked'] = datetime.date.today().isoformat()
            break
    save_data(RECIPES_FILE, all_recipes)
    meals = load_data(MEALPLAN_FILE)
    days  = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
    day   = next((d for d in days if not any(m.get('day') == d for m in meals)), 'Sonstige')
    meals.append({'id': max((m['id'] for m in meals), default=0) + 1, 'name': recipe['name'], 'day': day})
    save_data(MEALPLAN_FILE, meals)
    return jsonify({'status': 'added', 'day': day})

@main.route('/recipes/<int:recipe_id>/toggle_favorite', methods=['POST'])
def toggle_favorite(recipe_id):
    all_recipes = load_data(RECIPES_FILE)
    fav = False
    for r in all_recipes:
        if r['id'] == recipe_id:
            r['favorite'] = not r.get('favorite', False)
            fav = r['favorite']
            break
    save_data(RECIPES_FILE, all_recipes)
    return jsonify({'favorite': fav})

@main.route('/recipes/<int:recipe_id>/edit', methods=['GET', 'POST'])
def recipe_edit(recipe_id):
    categories  = load_categories()
    all_recipes = load_data(RECIPES_FILE)
    recipe = next((r for r in all_recipes if r['id'] == recipe_id), None)
    if not recipe:
        return redirect(url_for('main.recipes'))
    recipe = _normalize_recipe(recipe)

    if request.method == 'POST':
        image_path = recipe.get('image')
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                if image_path:
                    old = os.path.join(UPLOAD_FOLDER, os.path.basename(image_path))
                    if os.path.exists(old):
                        os.remove(old)
                ext = os.path.splitext(secure_filename(file.filename))[1].lower()
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file.save(os.path.join(UPLOAD_FOLDER, f"{recipe_id}{ext}"))
                image_path = f"uploads/{recipe_id}{ext}"

        amounts = request.form.getlist('ingredient_amount')
        names   = request.form.getlist('ingredient_name')
        ingredients = [{'amount': a.strip(), 'name': n.strip()} for a, n in zip(amounts, names) if n.strip()]
        steps = [s.strip() for s in request.form.getlist('step') if s.strip()]

        for r in all_recipes:
            if r['id'] == recipe_id:
                r['name']        = request.form.get('name', '').strip()
                r['category']    = request.form.getlist('category')
                r['prep_time']   = request.form.get('prep_time', '')
                r['servings']    = request.form.get('servings', '')
                r['image']       = image_path
                r['ingredients'] = ingredients
                r['steps']       = steps
                break
        save_data(RECIPES_FILE, all_recipes)
        return redirect(url_for('main.recipe_detail', recipe_id=recipe_id))

    return render_template('recipe_edit.html', recipe=recipe, categories=categories)

@main.route('/recipes/<int:recipe_id>/add_to_grocery', methods=['POST'])
def recipe_add_to_grocery(recipe_id):
    recipe = next((r for r in load_data(RECIPES_FILE) if r['id'] == recipe_id), None)
    if not recipe:
        return jsonify({'status': 'not found'}), 404
    data    = request.get_json(silent=True) or {}
    factor  = float(data.get('factor', 1.0))
    grocery = load_data(GROCERY_FILE)
    pantry_names = {p['name'].lower() for p in load_data(PANTRY_FILE)}
    next_id = max((i['id'] for i in grocery), default=0) + 1
    in_pantry = 0
    for ing in recipe.get('ingredients', []):
        amount = _scale_amount(ing.get('amount', ''), factor)
        grocery.append({'id': next_id, 'name': f"{amount} {ing['name']}".strip()})
        next_id += 1
        if pantry_names and _pantry_match(ing['name'], pantry_names):
            in_pantry += 1
    save_data(GROCERY_FILE, grocery)
    return jsonify({'status': 'added', 'count': len(recipe.get('ingredients', [])), 'in_pantry': in_pantry})

########################################### MEALPLAN EXTRAS ###########################################
@main.route('/mealplan/random_week', methods=['POST'])
def random_week():
    days = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
    meals = load_data(MEALPLAN_FILE)
    all_recipes = load_data(RECIPES_FILE)
    if not all_recipes:
        return jsonify({'error': 'Keine Rezepte vorhanden', 'added': 0}), 400
    occupied = {m['day'] for m in meals}
    empty_days = [d for d in days if d not in occupied]
    if not empty_days:
        return jsonify({'added': 0})
    shuffled = list(all_recipes)
    random.shuffle(shuffled)
    next_id = max((m['id'] for m in meals), default=0) + 1
    for i, day in enumerate(empty_days):
        recipe = shuffled[i % len(shuffled)]
        meals.append({'id': next_id, 'name': recipe['name'], 'day': day})
        next_id += 1
    save_data(MEALPLAN_FILE, meals)
    return jsonify({'added': len(empty_days)})

@main.route('/mealplan/add_to_grocery', methods=['POST'])
def mealplan_to_grocery():
    meals = load_data(MEALPLAN_FILE)
    all_recipes = load_data(RECIPES_FILE)
    grocery = load_data(GROCERY_FILE)
    pantry_names = {p['name'].lower() for p in load_data(PANTRY_FILE)}
    recipe_map = {r['name'].lower(): r for r in all_recipes}
    next_id = max((i['id'] for i in grocery), default=0) + 1
    added = 0
    in_pantry = 0
    for meal in meals:
        name = meal.get('name', '')
        recipe = recipe_map.get(name.lower())
        if recipe:
            for ing in recipe.get('ingredients', []):
                item_name = f"{ing.get('amount', '')} {ing['name']}".strip()
                grocery.append({'id': next_id, 'name': item_name})
                next_id += 1
                added += 1
                if pantry_names and _pantry_match(ing['name'], pantry_names):
                    in_pantry += 1
        else:
            grocery.append({'id': next_id, 'name': f"Zutaten für {name}"})
            next_id += 1
            added += 1
    save_data(GROCERY_FILE, grocery)
    return jsonify({'added': added, 'in_pantry': in_pantry})

########################################### STAPLES ROUTES ###########################################
@main.route('/staples', methods=['GET', 'POST'])
def staples():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if name:
            items = load_data(STAPLES_FILE)
            items.append({'id': max((i['id'] for i in items), default=0) + 1, 'name': name})
            save_data(STAPLES_FILE, items)
        return redirect(url_for('main.staples'))
    return render_template('staples.html', items=load_data(STAPLES_FILE))

@main.route('/staples/delete/<int:item_id>', methods=['POST'])
def delete_staple(item_id):
    items = load_data(STAPLES_FILE)
    save_data(STAPLES_FILE, [i for i in items if i['id'] != item_id])
    return jsonify({'status': 'deleted'})

@main.route('/staples/<int:item_id>/add_to_grocery', methods=['POST'])
def staple_to_grocery(item_id):
    items = load_data(STAPLES_FILE)
    item = next((i for i in items if i['id'] == item_id), None)
    if not item:
        return jsonify({'status': 'not found'}), 404
    grocery = load_data(GROCERY_FILE)
    grocery.append({'id': max((i['id'] for i in grocery), default=0) + 1, 'name': item['name']})
    save_data(GROCERY_FILE, grocery)
    return jsonify({'status': 'added'})

########################################### PANTRY ROUTES ###########################################
@main.route('/pantry', methods=['GET', 'POST'])
def pantry():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if name:
            items = load_data(PANTRY_FILE)
            items.append({'id': max((i['id'] for i in items), default=0) + 1, 'name': name})
            save_data(PANTRY_FILE, items)
        return redirect(url_for('main.pantry'))
    return render_template('pantry.html', items=load_data(PANTRY_FILE))

@main.route('/pantry/delete/<int:item_id>', methods=['POST'])
def delete_pantry_item(item_id):
    items = load_data(PANTRY_FILE)
    save_data(PANTRY_FILE, [i for i in items if i['id'] != item_id])
    return jsonify({'status': 'deleted'})
