from flask import Flask, render_template
from api.geocode import geocode_bp
from api.infrastructure import infra_bp
from api.landprice import landprice_bp
from api.gemini import gemini_bp
from api.landuse import landuse_bp
from api.investment import investment_bp

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

app.register_blueprint(geocode_bp, url_prefix="/api")
app.register_blueprint(infra_bp, url_prefix="/api")
app.register_blueprint(landprice_bp, url_prefix="/api")
app.register_blueprint(gemini_bp, url_prefix="/api")
app.register_blueprint(landuse_bp, url_prefix="/api")
app.register_blueprint(investment_bp, url_prefix="/api")

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5002)
