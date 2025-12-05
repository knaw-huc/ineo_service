import json
import logging
import requests
from os import environ
from flask_cors import CORS
from elastic_index import Index
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)


app = Flask(__name__)
cors_origins = [item for item in environ.get('FRONTEND_HOST', "").split(",") if item]
CORS(app, supports_credentials=True, resources={r'/*': {'origins': cors_origins}})
# Allow all origins
# CORS(app, supports_credentials=True)

config = {
    "scheme": environ.get("ELASTICSEARCH_SCHEME"),
    "url": environ.get("ELASTICSEARCH_HOST"),
    "port": environ.get("ELASTICSEARCH_PORT"),
    "index": environ.get("ELASTICSEARCH_INDEX"),
    "ineo_user": environ.get("ELASTICSEARCH_USERNAME"),
    "ineo_password": environ.get("ELASTICSEARCH_PASSWORD"),
}

index = Index(config)


@app.after_request
def after_request(response):
    # response.headers['Access-Control-Allow-Origin'] = '*'
    # response.headers['Access-Control-Allow-Headers'] = '*'
    # response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    response.headers['Content-type'] = 'application/json'
    return response


@app.route("/")
def hello_world():
    retStruc = {"app": "Procrustus service", "version": "0.1"}
    return json.dumps(retStruc)


@app.route("/facet", methods=['GET', 'POST'])
def get_facet():
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


@app.route("/browse", methods=['POST'])
def browse():
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


# Start main program

if __name__ == '__main__':
    app.run()
