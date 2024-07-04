from flask import Flask, render_template, request, redirect, url_for, session
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/cbjet_airways'
mongo = PyMongo(app)

# Route to main menu
@app.route('/')
def main_menu():
    if 'username' in session:
        return render_template('main_menu.html', username=session['username'])
    return redirect(url_for('login'))

# Route to login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        login_user = users.find_one({'username': request.form['username']})
        if login_user and login_user['password'] == request.form['password']:
            session['username'] = request.form['username']
            session['user_id'] = str(login_user['_id'])
            return redirect(url_for('main_menu'))
        return 'Invalid username/password combination'
    return render_template('login.html')

# Route to create a new account
@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'username': request.form['username']})
        if existing_user is None:
            user_id = users.insert_one({
                'username': request.form['username'],
                'password': request.form['password'],
                'email': request.form['email']
            }).inserted_id
            session['username'] = request.form['username']
            session['user_id'] = str(user_id)
            return redirect(url_for('main_menu'))
        return 'Username already exists'
    return render_template('create_account.html')

@app.route('/flights', methods=['GET'])
def flights():
    cities = list(set(mongo.db.flight_schedules.distinct('origin') + mongo.db.flight_schedules.distinct('destination')))
    from_city = request.args.get('from')
    to_city = request.args.get('to')
    date = request.args.get('date')
    
    query = {}
    if from_city:
        query['origin'] = from_city
    if to_city:
        query['destination'] = to_city
    if date:
        query['departureDate'] = date
    
    flights = list(mongo.db.flight_schedules.find(query))
    for flight in flights:
        flight['departureTime'] = flight['departureTime'].strftime('%Y-%m-%d %H:%M:%S')
        flight['arrivalTime'] = flight['arrivalTime'].strftime('%Y-%m-%d %H:%M:%S')
        flight['_id'] = str(flight['_id'])  # Convert ObjectId to string
    
    return render_template('flights.html', flights=flights, cities=cities)

@app.route('/book/<flight_id>', methods=['GET', 'POST'])
def book_ticket(flight_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))

        flight = mongo.db.flight_schedules.find_one({'_id': ObjectId(flight_id)})
        if not flight:
            return 'Flight not found', 404

        booking = {
            'user_id': user_id,
            'flight_id': flight_id,
            'flightNumber': flight['flightNumber'],
            'origin': flight['origin'],
            'destination': flight['destination'],
            'departureTime': flight['departureTime'],
            'arrivalTime': flight['arrivalTime'],
            'seat_preference': request.form.get('seat_preference'),
            'class': request.form.get('class'),
            'booking_date': datetime.utcnow()
        }
        mongo.db.bookings.insert_one(booking)
        return redirect(url_for('booking_history'))

    flight = mongo.db.flight_schedules.find_one({'_id': ObjectId(flight_id)})
    if not flight:
        return 'Flight not found', 404
    return render_template('book_ticket.html', flight=flight)

@app.route('/booking_history')
def booking_history():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    bookings = list(mongo.db.bookings.find({'user_id': user_id}))

    # Fetch flight details for each booking
    for booking in bookings:
        flight = mongo.db.flight_schedules.find_one({'_id': ObjectId(booking['flight_id'])})
        booking['flight'] = flight

    return render_template('booking_history.html', bookings=bookings)

# Route to view ticket
# Route to view ticket
@app.route('/ticket/<booking_id>')
def ticket(booking_id):
    booking = mongo.db.bookings.find_one({'_id': ObjectId(booking_id)})
    flight = mongo.db.flight_schedules.find_one({'_id': ObjectId(booking['flight_id'])})
    return render_template('ticket.html', booking=booking, flight=flight)

# Route to logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
