from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Use DATABASE_URL environment variable for production, SQLite for development
database_url = os.environ.get('DATABASE_URL', 'sqlite:///ratings.db')
# Render uses postgres, so we need to update the URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

db = SQLAlchemy(app)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'score': self.score,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

# Get admin password from environment variable
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'default_password')

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    ratings = Rating.query.order_by(Rating.timestamp.desc()).all()
    return render_template('admin.html', ratings=ratings)

@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    try:
        data = request.json
        rating = Rating(score=data['rating'])
        db.session.add(rating)
        db.session.commit()
        return jsonify({'message': 'Rating submitted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/get_ratings')
def get_ratings():
    try:
        ratings = Rating.query.all()
        total_ratings = len(ratings)
        
        if total_ratings == 0:
            return jsonify({
                'average': 0,
                'total': 0,
                'distribution': {i: 0 for i in range(1, 6)}
            })
        
        distribution = {i: 0 for i in range(1, 6)}
        for rating in ratings:
            distribution[rating.score] += 1
        
        average = sum(r.score for r in ratings) / total_ratings
        
        return jsonify({
            'average': round(average, 1),
            'total': total_ratings,
            'distribution': distribution
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear_data', methods=['POST'])
def clear_data():
    if request.form.get('password') != ADMIN_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    try:
        Rating.query.delete()
        db.session.commit()
        return jsonify({'message': 'All ratings cleared successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Add this new route to your existing app.py
@app.route('/delete_rating/<int:rating_id>', methods=['POST'])
def delete_rating(rating_id):
    if request.form.get('password') != ADMIN_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    try:
        rating = Rating.query.get(rating_id)
        if rating is None:
            return jsonify({'error': 'Rating not found'}), 404
            
        db.session.delete(rating)
        db.session.commit()
        return jsonify({'message': 'Rating deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)