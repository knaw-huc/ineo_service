import json
import logging
import requests
from os import environ
from elastic_index import Index
from flask import Flask, request, jsonify

# Configure logging based on environment
ENVIRONMENT = environ.get('FLASK_ENV', 'development')
LOG_LEVEL = environ.get('LOG_LEVEL', 'INFO' if ENVIRONMENT == 'development' else 'WARNING')

# Production uses WARNING level, development uses INFO
log_level = getattr(logging, LOG_LEVEL, logging.INFO)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized - Environment: {ENVIRONMENT}, Log Level: {LOG_LEVEL}")


app = Flask(__name__)

config = {
    "scheme": environ.get("ELASTICSEARCH_SCHEME"),
    "url": environ.get("ELASTICSEARCH_HOST"),
    "port": environ.get("ELASTICSEARCH_PORT"),
    "index": environ.get("ELASTICSEARCH_INDEX"),
    "ineo_user": environ.get("ELASTICSEARCH_USERNAME"),
    "ineo_password": environ.get("ELASTICSEARCH_PASSWORD"),
}

index = Index(config)


@app.before_request
def before_request():
    method = request.method
    origin = request.headers.get('Origin')
    logger.debug(f"[BEFORE_REQUEST] Incoming {method} request from origin: {origin}")
    
    if method == 'OPTIONS':
        logger.debug(f"[BEFORE_REQUEST] Creating OPTIONS response for preflight request")
        response = app.make_response(('', 204))
        # Use the origin if present, otherwise allow all origins
        response.headers['Access-Control-Allow-Origin'] = origin if origin else '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
        response.headers['Access-Control-Max-Age'] = '3600'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        logger.debug(f"[BEFORE_REQUEST] OPTIONS response status: {response.status_code}, origin: {response.headers.get('Access-Control-Allow-Origin')}")
        return response


@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    logger.debug(f"[AFTER_REQUEST] Processing response status: {response.status_code}, origin: {origin}")
    
    # Always set CORS headers
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    # Only add Content-type for responses with a body
    if response.status_code not in [204, 304]:
        if 'Content-Type' not in response.headers:
            response.headers['Content-Type'] = 'application/json'
    
    logger.debug(f"[AFTER_REQUEST] Final response status: {response.status_code}, CORS header: {response.headers.get('Access-Control-Allow-Origin')}")
    return response


@app.route("/")
def hello_world():
    retStruc = {"app": "Procrustus service", "version": "0.1"}
    return json.dumps(retStruc)


@app.route("/facet", methods=['GET', 'POST', 'OPTIONS'])
def get_facet():
    if request.method == 'OPTIONS':
        return '', 204
    struc = request.get_json()
    new_searchvalues = []
    for d in struc["searchvalues"]:
        if "field" in d and isinstance(d["field"], str) and d["field"].startswith("properties."):
            d["field"] = f"document.{d['field']}"
        new_searchvalues.append(d)

    struc["searchvalues"] = new_searchvalues
    ret_struc = index.get_facet(f"document.{struc["name"]}", struc["amount"], struc["filter"], struc["searchvalues"])
    return json.dumps(ret_struc)


# @app.route("/nested-facet", methods=['GET'])
# def get_nested_facet():
#     facet = request.args.get("name")
#     amount = request.args.get("amount")
#     facet_filter = request.args.get("filter")
#     ret_struc = index.get_nested_facet(facet + ".keyword", amount, facet_filter)
#     return json.dumps(ret_struc)


# @app.route("/filter-facet", methods=['GET'])
# def get_filter_facet():
#     facet = request.args.get("name")
#     amount = request.args.get("amount")
#     facet_filter = request.args.get("filter")
#     ret_struc = index.get_filter_facet(facet + ".keyword", amount, facet_filter)
#     return json.dumps(ret_struc)


@app.route("/browse", methods=['POST', 'OPTIONS'])
def browse():
    logger.debug(f"[BROWSE] Received {request.method} request")
    if request.method == 'OPTIONS':
        logger.debug(f"[BROWSE] Returning early for OPTIONS")
        return '', 204
    struc = request.get_json()
    new_searchvalues = []
    for d in struc["searchvalues"]:
        if "field" in d and isinstance(d["field"], str) and d["field"].startswith("properties."):
            d["field"] = f"document.{d['field']}"
        new_searchvalues.append(d)

    struc["searchvalues"] = new_searchvalues
    # ret_struc = index.browse(struc["page"], struc["page_length"], struc["sortorder"] + ".keyword", struc["searchvalues"])
    ret_struc = index.browse(struc["page"], struc["page_length"], struc["searchvalues"])
    return json.dumps(ret_struc)


@app.get('/typeinfo')
def typeinfo():
    if not request.values.get('url'):
        return 'No url specified', 400

    url = request.values.get('url')
    try:
        res = requests.head(url, allow_redirects=True)
        return jsonify(ok=res.ok,
                       url=url,
                       content_type=res.headers['content-type'] if res.ok else None)
    except:
        return jsonify(ok=False, url=url, content_type=None)


@app.get('/detail')
def get_detail():
    rec = request.args.get("rec")
    try:
        file = f"/data/{rec}_processed.json"
        with open(file, "r") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        try:
            doc = index.get_doc_by_field("document.id", rec)
            result = [
                {
                    "document": doc,
                }
            ]
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)})


@app.errorhandler(404)
def not_found(error):
    logger.error(f"[ERROR] 404 Not Found - Path: {request.path}, Method: {request.method}")
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    logger.error(f"[ERROR] 405 Method Not Allowed - Path: {request.path}, Method: {request.method}")
    return jsonify({"error": "Method not allowed"}), 405
