#!/usr/bin/env python3
"""Label Resource models for flask"""

import logging

from flask import request
from flask_restplus import Namespace, Resource, fields
from mongoengine import ValidationError

from abe import database as db
from abe.auth import edit_auth_required
from abe.helper_functions.converting_helpers import mongo_to_dict, request_to_dict
from abe.helper_functions.mongodb_helpers import mongo_resource_errors
from abe.helper_functions.query_helpers import multi_search

api = Namespace('labels', description='Label related operations')

# This should be kept in sync with the document model, which drives the format
label_model = api.model("Label_Model", {
    "name": fields.String(required=True),
    "description": fields.String,
    "url": fields.Url,
    "default":  fields.Boolean,
    "parent_labels": fields.List(fields.String),
    "color": fields.String,
    "visibility": fields.String(enum=['public', 'olin', 'students'])
})


class LabelApi(Resource):
    """API for interacting with all labels (searching, creating)"""

    @mongo_resource_errors
    def get(self, label_name=None):
        """Retrieve labels"""
        if label_name:  # use label name/object id if present
            logging.debug('Label requested: %s', label_name)
            search_fields = ['name', 'id']
            result = multi_search(db.Label, label_name, search_fields)
            if not result:
                return "Label not found with identifier '{}'".format(label_name), 404
            else:
                return mongo_to_dict(result)
        else:  # search database based on parameters
            # TODO: search based on terms
            results = db.Label.objects()
            if not results:
                return []
            else:
                return [mongo_to_dict(result) for result in results]

    @edit_auth_required
    @mongo_resource_errors
    @api.expect(label_model)
    def post(self):
        """Create new label with parameters passed in through args or form"""
        received_data = request_to_dict(request)
        logging.debug("Received POST data: %s", received_data)
        # TODO: replace this try:except: by just the try: block, after PR #229 is merged
        try:
            new_label = db.Label(**received_data)
            new_label.save()
        except ValidationError as error:
            return {'error_type': 'validation',
                    'validation_errors': str(error),  # [str(err) for err in error.errors or [error]],
                    'error_message': error.message,
                    }, 400
        return mongo_to_dict(new_label), 201

    @edit_auth_required
    @mongo_resource_errors
    @api.expect(label_model)
    def put(self, label_name):
        """Modify individual label"""
        received_data = request_to_dict(request)
        logging.debug("Received PUT data: %s", received_data)
        search_fields = ['name', 'id']
        result = multi_search(db.Label, label_name, search_fields)
        if not result:
            return "Label not found with identifier '{}'".format(label_name), 404

        # TODO: replace this try:except: by just the try: block, after PR #229 is merged
        try:
            result.update(**received_data)
        except ValidationError as error:
            return {'error_type': 'validation',
                    'validation_errors': [str(err) for err in error.errors or [error]],
                    'error_message': error.message}, 400
        return mongo_to_dict(result)

    @edit_auth_required
    @mongo_resource_errors
    def delete(self, label_name):
        """Delete individual label"""
        logging.debug('Label requested: %s', label_name)
        search_fields = ['name', 'id']
        result = multi_search(db.Label, label_name, search_fields)
        if not result:
            return "Label not found with identifier '{}'".format(label_name), 404

        received_data = request_to_dict(request)
        logging.debug("Received DELETE data: %s", received_data)
        result.delete()
        return mongo_to_dict(result)


api.add_resource(LabelApi, '/', methods=['GET', 'POST'], endpoint='label')
api.add_resource(LabelApi, '/<string:label_name>',
                 methods=['GET', 'PUT', 'PATCH', 'DELETE'],
                 endpoint='label_name')
