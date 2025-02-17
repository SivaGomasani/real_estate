from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import pdfkit

app = Flask(__name__, template_folder="templates")
app.secret_key = "your_secret_key"

# SQLite Database Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///realestate.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["RECEIPTS_FOLDER"] = "static/receipts"

# Ensure the necessary folders exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["RECEIPTS_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    bhk = db.Column(db.Integer, nullable=False)
    area = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("properties", lazy=True))
    is_tenant = db.Column(db.Boolean, default=False)  

# Home Route
@app.route("/")
def home():
    return redirect(url_for("dashboard"))

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/dashboard")
def dashboard():
    properties = Property.query.all()
    return render_template("dashboard.html", properties=properties)

# Signup Route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("Email already exists! Try logging in.", "error")
            return redirect(url_for("signup"))

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Signup successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Login Successful!", "success")
            return render_template("index.html")
        else:
            flash("Invalid credentials. Try again.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/index")
@login_required
def index():
    return render_template("index.html")

@app.route("/tenants", methods=["GET"])
def tenants():
    if "user_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    # Retrieve properties listed by tenants
    tenant_properties = Property.query.filter_by(is_tenant=True).all()
    return render_template("tenants.html", properties=tenant_properties)

# Add Property (Protected)
@app.route("/add_property", methods=["POST"])
def add_property():
    try:
        if "user_id" not in session:
            return jsonify({"message": "Unauthorized"}), 403

        title = request.form["title"]
        property_type = request.form["type"]
        price = request.form["price"]
        bhk = request.form["bhk"]
        area = request.form["area"]
        location = request.form["location"]
        contact = request.form["contact"]
        description = request.form["description"]
        image = request.files["image"]

        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image.save(image_path)
        else:
            image_path = None

        new_property = Property(
            title=title,
            property_type=property_type,
            price=price,
            bhk=bhk,
            area=area,
            location=location,
            contact=contact,
            description=description,
            image=filename,
            user_id=session["user_id"]
        )
        db.session.add(new_property)
        db.session.commit()

        flash("Property added successfully!", "success")
        return jsonify({"message": "Property added successfully!"})  # Return JSON response
    except Exception as e:
        print("Error:", e)
        return jsonify({"message": "Internal Server Error"}), 500

# Get All Properties (with filtering for buyers)
@app.route("/get_properties", methods=["GET"])
def get_properties():
    category = request.args.get("category", "all")
    if category == "buyers":
        properties = Property.query.filter_by(property_type="Sale").all()
        print(f"Properties for sale: {properties}")  # Debug print
    else:
        properties = Property.query.all()

    property_list = [
        {
            "id": prop.id,
            "title": prop.title,
            "property_type": prop.property_type,
            "price": prop.price,
            "bhk": prop.bhk,
            "area": prop.area,
            "location": prop.location,
            "contact": prop.contact,
            "description": prop.description,
            "image": prop.image,
            "user_id": prop.user_id,
        }
        for prop in properties
    ]
    return jsonify(property_list)

# Get Property Details
@app.route("/get_property_details/<int:property_id>", methods=["GET"])
def get_property_details(property_id):
    property = Property.query.get_or_404(property_id)
    return jsonify({
        "id": property.id,
        "title": property.title,
        "property_type": property.property_type,
        "price": property.price,
        "bhk": property.bhk,
        "area": property.area,
        "location": property.location,
        "contact": property.contact,
        "description": property.description,
        "image": property.image,
        "user_id": property.user_id
    })

@app.route('/buy_property/<int:property_id>', methods=['POST'])
def buy_property(property_id):
    property = Property.query.get(property_id)
    if property:
        # Simulate payment (In real-world, you'll handle actual payment gateway here)
        payment_data = request.json
        payment_amount = payment_data.get('payment_amount')
        if payment_amount == property.price:
            # Remove the property after payment
            db.session.delete(property)
            db.session.commit()
            return jsonify({"message": "Payment successful. Property removed from listing."}), 200
        else:
            return jsonify({"message": "Payment amount mismatch."}), 400
    return jsonify({"message": "Property not found."}), 404

# Route to download the receipt
@app.route("/download_receipt/<int:property_id>", methods=["GET"])
def download_receipt(property_id):
    property = Property.query.get_or_404(property_id)
    receipt_filename = f"{app.config['RECEIPTS_FOLDER']}/{property.title}_receipt.pdf"
    if os.path.exists(receipt_filename):
        return send_file(receipt_filename, as_attachment=True)
    else:
        return jsonify({"message": "Receipt not found"}), 404

# Buyers Route
@app.route("/buyers")
def buyers():
    properties = Property.query.filter_by(property_type="Sale").all()
    return render_template("buyers.html", properties=properties)

# Dealers Route
@app.route("/dealers", methods=["GET", "POST"])
def dealers():
    if "user_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    properties = Property.query.filter_by(user_id=session["user_id"]).all()
    return render_template("dealers.html", properties=properties)

# Logout Route
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))

# Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
