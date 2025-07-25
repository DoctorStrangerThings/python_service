from flask import Flask, request, jsonify
import piexif
from PIL import Image
import io

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "Python EXIF service is running."}), 200

def convert_to_degrees(value):
    d, m, s = value
    degrees = d[0] / d[1]
    minutes = m[0] / m[1]
    seconds = s[0] / s[1]
    return degrees + (minutes / 60.0) + (seconds / 3600.0)

def get_gps_coordinates(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif_bytes = img.info.get("exif")
        if not exif_bytes:
            app.logger.warning("No EXIF data found.")
            return None

        exif_dict = piexif.load(exif_bytes)
        gps = exif_dict.get("GPS", {})
        if not gps:
            app.logger.warning("No GPS data in EXIF.")
            return None

        lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef)
        lat_val = gps.get(piexif.GPSIFD.GPSLatitude)
        lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef)
        lon_val = gps.get(piexif.GPSIFD.GPSLongitude)

        if not (lat_ref and lat_val and lon_ref and lon_val):
            app.logger.warning("Incomplete GPS data.")
            return None

        lat = convert_to_degrees(lat_val)
        if lat_ref == b'S':
            lat *= -1

        lon = convert_to_degrees(lon_val)
        if lon_ref == b'W':
            lon *= -1

        return {"latitude": lat, "longitude": lon}

    except Exception as e:
        app.logger.error(f"❌ EXIF extraction failed: {e}")
        return None

@app.route("/extract", methods=["POST"])
def extract():
    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image file uploaded."}), 400

    image_file = request.files["image"]
    image_bytes = image_file.read()

    coords = get_gps_coordinates(image_bytes)

    if not coords:
        return jsonify({
            "success": False,
            "message": "Missing or invalid GPS metadata. Image will not be saved."
        }), 400

    return jsonify({
        "success": True,
        "latitude": coords["latitude"],
        "longitude": coords["longitude"]
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
