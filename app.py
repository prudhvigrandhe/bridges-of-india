from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
)
from models import db, Country, State, District, Bridge
from functools import wraps
from sqlalchemy import or_
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super-secret-key-change-me"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bridges.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload configuration
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

# Flag for initial setup
first_request_handled = False


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def handle_first_request():
    """Create tables and seed sample data on first run."""
    global first_request_handled
    if not first_request_handled:
        first_request_handled = True
        db.create_all()

        # Seed data only if empty
        if not Country.query.first():
            india = Country(name="India")
            db.session.add(india)

            ap = State(name="Andhra Pradesh", country=india)
            db.session.add(ap)

            # Add all major Andhra Pradesh districts
            districts_data = [
                "East Godavari",
                "West Godavari",
                "Krishna",
                "Guntur",
                "Prakasam",
                "Nellore",
                "Visakhapatnam",
                "Vizianagaram",
                "Srikakulam",
                "Kurnool",
                "Anantapur",
                "Chittoor",
                "YSR Kadapa",
            ]

            district_objects = []
            for name in districts_data:
                d = District(name=name, state=ap)
                db.session.add(d)
                district_objects.append(d)

            db.session.flush()  # populate district IDs without full commit

            # Lookup helper
            def find_district(name):
                return next((d for d in district_objects if d.name == name), None)

            # Add famous bridges
            east_godavari = find_district("East Godavari")
            krishna = find_district("Krishna")

            godavari_bridge = Bridge(
                name="Godavari Bridge (Havelock Bridge)",
                district=east_godavari,
                river_name="Godavari River",
                year_built=1900,
                bridge_type="Truss railway bridge",
                description=(
                    "Historic railway bridge in Rajahmundry across the Godavari River, "
                    "also known as Havelock Bridge."
                ),
                image_url="https://img.traveltriangle.com/blog/wp-content/uploads/2024/06/Godavari-Bridge-OG.jpg",
            )
            db.session.add(godavari_bridge)

            prakasam_barrage = Bridge(
                name="Prakasam Barrage",
                district=krishna,
                river_name="Krishna River",
                year_built=1957,
                bridge_type="Arch bridge",
                description="A famous barrage across the Krishna River.",
                image_url="https://dynamic-media-cdn.tripadvisor.com/media/photo-o/0f/b5/db/4f/prakasam-barrage.jpg?w=1200&h=-1&s=1",
            )
            db.session.add(prakasam_barrage)

            db.session.commit()


# ========== LOGIN SYSTEM ==========

EDITORS = {"admin": "password123"}


def editor_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "editor":
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if EDITORS.get(username) == password:
            session["username"] = username
            session["role"] = "editor"
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ========== MAIN PAGES ==========


@app.route("/")
def home():
    countries = Country.query.all()
    famous_bridges = Bridge.query.limit(6).all()
    return render_template(
        "home.html",
        countries=countries,
        famous_bridges=famous_bridges,
    )


# ========== SEARCH FEATURE ==========


# Update the search route to handle specific bridge name searches
@app.route("/search")
def search():
    query = request.args.get("q", "")
    results = []

    if query:
        results = Bridge.query.filter(
            or_(
                Bridge.name.ilike(f"%{query}%"),
                Bridge.river_name.ilike(f"%{query}%"),
                Bridge.description.ilike(f"%{query}%")
            )
        ).all()

        # If exactly one result is found, redirect to the bridge detail page
        if len(results) == 1:
            return redirect(url_for("api_bridge_detail", bridge_id=results[0].id))

    return render_template("search_results.html", query=query, results=results)


# ========== API ROUTES ==========


@app.route("/api/countries")
def api_countries():
    countries = Country.query.all()
    return jsonify([{"id": c.id, "name": c.name} for c in countries])


@app.route("/api/states")
def api_states():
    country_id = request.args.get("country_id", type=int)
    states = State.query.filter_by(country_id=country_id).all()
    return jsonify([{"id": s.id, "name": s.name} for s in states])


@app.route("/api/districts")
def api_districts():
    state_id = request.args.get("state_id", type=int)
    districts = District.query.filter_by(state_id=state_id).all()
    return jsonify([{"id": d.id, "name": d.name} for d in districts])


@app.route("/api/bridges")
def api_bridges():
    district_id = request.args.get("district_id", type=int)
    bridges = Bridge.query.filter_by(district_id=district_id).all()
    return jsonify([{"id": b.id, "name": b.name} for b in bridges])


@app.route("/api/bridges/<int:bridge_id>")
def api_bridge_detail(bridge_id):
    b = Bridge.query.get_or_404(bridge_id)
    return render_template(
        "bridge_detail.html",
        bridge=b
    )


# ---------- Bridge detail page (HTML) ----------

@app.route("/bridge/<int:bridge_id>")
def bridge_detail(bridge_id):
    bridge = Bridge.query.get_or_404(bridge_id)
    return render_template("bridge_detail.html", bridge=bridge)



# ========== EDITOR PAGE ==========


@app.route("/editor/add-bridge", methods=["GET", "POST"])
@editor_required
def add_bridge():
    if request.method == "POST":
        name = request.form["name"]
        district_id = int(request.form["district_id"])
        river_name = request.form.get("river_name") or None
        year_built = request.form.get("year_built") or None
        bridge_type = request.form.get("bridge_type") or None
        description = request.form.get("description") or None
        image_url = request.form.get("image_url") or None

        file = request.files.get("image_file")
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            image_url = f"/static/uploads/{filename}"

        if year_built:
            year_built = int(year_built)

        new_bridge = Bridge(
            name=name,
            district_id=district_id,
            river_name=river_name,
            year_built=year_built,
            bridge_type=bridge_type,
            description=description,
            image_url=image_url,
        )
        db.session.add(new_bridge)
        db.session.commit()

        return redirect(url_for("home"))

    countries = Country.query.all()
    return render_template("add_bridge.html", countries=countries)


if __name__ == "__main__":
    app.run(debug=True)
