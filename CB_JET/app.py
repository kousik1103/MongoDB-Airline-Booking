from flask import Flask, render_template, request, redirect, url_for, session
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime

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
            users.insert_one({
                'username': request.form['username'],
                'password': request.form['password'],
                'email': request.form['email']
            })
            session['username'] = request.form['username']
            return redirect(url_for('main_menu'))
        return 'Username already exists'
    return render_template('create_account.html')

# Route to view available flights
@app.route('/flights', methods=['GET', 'POST'])
def flights():
    flight_schedules = mongo.db.flight_schedules
    
    if request.method == 'POST':
        from_city = request.form.get('from')
        to_city = request.form.get('to')
        date = request.form.get('date')
    else:
        from_city = request.args.get('from')
        to_city = request.args.get('to')
        date = request.args.get('date')
    
    query = {}
    if from_city:
        query['origin'] = from_city
    if to_city:
        query['destination'] = to_city
    if date:
        query['departureTime'] = {'$gte': datetime.strptime(date, '%Y-%m-%d')}
    
    flights = flight_schedules.find(query)
    flights = [{
        'flightNumber': flight['flightNumber'],
        'origin': flight['origin'],
        'destination': flight['destination'],
        'departureTime': flight['departureTime'].strftime('%Y-%m-%d %H:%M:%S'),
        'arrivalTime': flight['arrivalTime'].strftime('%Y-%m-%d %H:%M:%S'),
        'availableSeats': flight['availableSeats']
    } for flight in flights]
    
    cities = flight_schedules.distinct('origin')
    
    return render_template('flights.html', flights=flights, cities=cities)


# Route to book a ticket
@app.route('/book_ticket/<flight_id>', methods=['GET', 'POST'])
def book_ticket(flight_id):
    if request.method == 'POST':
        bookings = mongo.db.bookings
        flight = mongo.db.flight_schedules.find_one({'_id': ObjectId(flight_id)})
        if flight and flight['availableSeats'] > 0:
            bookings.insert_one({
                'username': session['username'],
                'user_id': mongo.db.users.find_one({'username': session['username']})['_id'],
                'flight_id': ObjectId(flight_id),
                'name': request.form['name'],
                'seat_preference': request.form['seat_preference'],
                'class': request.form['class'],
                'booking_date': datetime.utcnow()
            })
            mongo.db.flight_schedules.update_one({'_id': ObjectId(flight_id)}, {'$inc': {'availableSeats': -1}})
            return redirect(url_for('booking_history'))
        return 'Flight not available or fully booked'
    return render_template('book_ticket.html', flight_id=flight_id)

@app.route('/booking_history')
def booking_history():
    username = session['username']
    user_id = mongo.db.users.find_one({'username': username})['_id']
    bookings = mongo.db.bookings.find({'username': username})
    booking_list = []
    for booking in bookings:
        flight = mongo.db.flight_schedules.find_one({'_id': booking['flight_id']})
        booking['flight'] = flight
        booking['booking_date'] = booking['booking_date'].strftime('%Y-%m-%d %H:%M:%S')
        booking_list.append(booking)
    return render_template('booking_history.html', bookings=booking_list)

# Route to view ticket
@app.route('/ticket/<booking_id>')
def ticket(booking_id):
    booking = mongo.db.bookings.find_one({'_id': ObjectId(booking_id)})
    flight = mongo.db.flight_schedules.find_one({'_id': booking['flight_id']})
    return render_template('ticket.html', booking=booking, flight=flight)

# Route to logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
