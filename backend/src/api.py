import os
from flask import Flask, Response, request, jsonify, abort
from sqlalchemy import exc
import json
from flask_cors import CORS

from .database.models import db_drop_and_create_all, setup_db, Drink
from .auth.auth import AuthError, requires_auth

app = Flask(__name__)
setup_db(app)
CORS(app, origins=["*"])


@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add(
        "Access-Control-Allow-Headers", "OPTIONS, GET, POST, PATCH, DELETE"
    )
    return response


"""
uncomment the following line to initialize the datbase
!! NOTE THIS WILL DROP ALL RECORDS AND START YOUR DB FROM SCRATCH
!! NOTE THIS MUST BE UNCOMMENTED ON FIRST RUN
!! Running this function will add one
"""
with app.app_context():
    db_drop_and_create_all()

# ROUTES
"""
implement endpoint
    GET /drinks
        it should be a public endpoint
        it should contain only the drink.short() data representation
    returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
        or appropriate status code indicating reason for failure
"""


@app.route("/drinks")
def get_drinks():
    drinks = Drink.query.order_by(Drink.title).all()
    return (
        jsonify({"success": True, "drinks": [drink.short() for drink in drinks]}),
        200,
    )


"""
implement endpoint
    GET /drinks-detail
        it should require the 'get:drinks-detail' permission
        it should contain the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
        or appropriate status code indicating reason for failure
"""


@app.route("/drinks-detail")
@requires_auth("get:drinks-detail")
def get_drinks_detail():
    drinks = Drink.query.order_by(Drink.title).all()
    return jsonify({"success": True, "drinks": [drink.long() for drink in drinks]})


"""
implement endpoint
    POST /drinks
        it should create a new row in the drinks table
        it should require the 'post:drinks' permission
        it should contain the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drink} where drink an array containing only the newly created drink
        or appropriate status code indicating reason for failure
"""


@app.route("/drinks", methods=["POST"])
@requires_auth("post:drinks")
def create_drink():
    body = request.get_json()
    if not (
        body
        and isinstance(body.get("title"), str)
        and isinstance(body.get("recipe"), list)
    ):
        abort(400)
    existing_drink = Drink.query.filter(Drink.title == body.get("title")).one_or_none()
    if existing_drink:
        abort(Response(status=400, response="drink titles must be unique"))
    for ingredient in body.get("recipe"):
        if (
            not ingredient.get("name")
            or not ingredient.get("color")
            or not ingredient.get("parts")
        ):
            abort(400)
    drink = Drink(title=body.get("title"), recipe=json.dumps(body.get("recipe")))
    drink.insert()
    return (
        jsonify({"success": True, "drinks": [drink.long()]}),
        200,  # This **should** be a 201 response for a successful Create operation, not a 200.
    )


# TODO: Add error handler for duplicate title insert

"""
implement endpoint
    PATCH /drinks/<id>
        where <id> is the existing model id
        it should respond with a 404 error if <id> is not found
        it should update the corresponding row for <id>
        it should require the 'patch:drinks' permission
        it should contain the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drink} where drink an array containing only the updated drink
        or appropriate status code indicating reason for failure
"""


@app.route("/drinks/<int:id>", methods=["PATCH"])
@requires_auth("patch:drinks")
def update_drink(id):
    if not isinstance(id, int):
        abort(400)
    body = request.get_json()
    if not (
        body
        and (isinstance(body.get("title"), str) or isinstance(body.get("recipe"), list))
    ):
        abort(400)
    if body.get("recipe"):
        for ingredient in body.get("recipe"):
            if (
                not ingredient.get("name")
                or not ingredient.get("color")
                or not ingredient.get("parts")
            ):
                abort(400)
    if body.get("title"):
        existing_drink = Drink.query.filter(
            Drink.title == body.get("title")
        ).one_or_none()
        if existing_drink:
            abort(Response(status=400, response="drink titles must be unique"))
    drink = Drink.query.filter(Drink.id == id).first_or_404()
    drink.title = body.get("title") or drink.title
    drink.recipe = json.dumps(body.get("recipe")) or drink.recipe
    drink.update()
    return jsonify({"success": True, "drinks": [drink.long()]}), 200


"""
implement endpoint
    DELETE /drinks/<id>
        where <id> is the existing model id
        it should respond with a 404 error if <id> is not found
        it should delete the corresponding row for <id>
        it should require the 'delete:drinks' permission
    returns status code 200 and json {"success": True, "delete": id} where id is the id of the deleted record
        or appropriate status code indicating reason for failure
"""


@app.route("/drinks/<int:id>", methods=["DELETE"])
@requires_auth("delete:drinks")
def delete_drink(id):
    if not isinstance(id, int):
        abort(400)
    drink = Drink.query.filter(Drink.id == id).first_or_404()
    if isinstance(drink, Drink):
        drink.delete()
        return jsonify({"success": True, "delete": drink.id}), 200


# Error Handling

"""
implement error handlers using the @app.errorhandler(error) decorator
    each error handler should return (with approprate messages):
        jsonify({
            "success": False,
            "error": 404,
            "message": "resource not found"
            }), 404

"""

"""
implement error handler for AuthError
    error handler should conform to general task above
"""


def handle_error(err, status_code: int, default_message=""):
    if isinstance(err, AuthError):
        return (
            jsonify(
                {
                    "success": False,
                    "error": err.status_code,
                    "message": err.error["description"],
                }
            ),
            err.status_code,
        )
    else:
        return (
            jsonify(
                {"success": False, "error": status_code, "message": default_message}
            ),
            status_code,
        )


@app.errorhandler(400)
def handle_400(err):
    return handle_error(err, 400, "Bad Request")


@app.errorhandler(401)
def handle_401(err):
    return handle_error(err, 401, "Unauthorized")


@app.errorhandler(403)
def handle_403(err):
    return handle_error(err, 403, "Forbidden")


"""
implement error handler for 404
    error handler should conform to general task above
"""


@app.errorhandler(404)
def handle_404(err):
    return handle_error(err, 404, "Not Found")


@app.errorhandler(405)
def handle_405(err):
    return handle_error(err, 405, "Method Not Allowed")


@app.errorhandler(415)
def unprocessable(err):
    return handle_error(err, 415, "Unsupported Media Type")


@app.errorhandler(422)
def unprocessable(err):
    return handle_error(err, 422, "Unprocessable Content")


@app.errorhandler(500)
def handle_500(err):
    return handle_error(err, 500, "Internal Server Error")
