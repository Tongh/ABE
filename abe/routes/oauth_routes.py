import logging
import os
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote_plus as url_quote_plus
from uuid import uuid4

import flask
import jwt
from flask import current_app as app
from flask import Blueprint, flash, redirect, render_template, request

# This is a *different* secret from the auth token, so that email tokens can't
# be used to sign in. This could also be accomplished by using the *same*
# secret, with different properties in the payload.
#
# In order to simplify credential management, this secret is derived from the
# auth token secret. The auth token and secret and the email token secret are
# never used to encrypt the same plaintext, so this shouldn't enable any
# differential cryptoanalysis.
from abe.auth import clear_auth_cookies, create_access_token
from abe.helper_functions.email_helpers import send_message
from abe.helper_functions.url_helpers import url_add_query_params
from flask_wtf import FlaskForm
from wtforms import HiddenField, StringField, SubmitField, validators
from wtforms.validators import DataRequired, Email

SLACK_OAUTH_CLIENT_ID = os.environ.get('SLACK_OAUTH_CLIENT_ID')
SLACK_OAUTH_VALIDATION_CODE = os.environ.get('SLACK_OAUTH_VALIDATION_CODE', str(uuid4()))

profile = Blueprint('oauth', __name__)


@profile.route('/oauth/authorize')
def authorize():
    downstream_redirect_uri = request.args['redirect_uri']
    upstream_redirect_uri = request.url_root + 'oauth/slack'
    state = {
        'state': request.args.get('state'),
        'validation_code': SLACK_OAUTH_VALIDATION_CODE,
    }
    # Some OAuth servesr require exact callback URL. For these, the downstram
    # redirect_uri should be in the state. For Slack, this prevents the state
    # from being present in the callback (maybe because it is too large?), so
    # place it in the redirect instead.
    if False:
        state['redirect_uri'] = downstream_redirect_uri
    else:
        upstream_redirect_uri += '?redirect_uri=' + url_quote_plus(downstream_redirect_uri)
    email_oauth_url = url_add_query_params(
        '/oauth/send_email',
        redirect_uri=downstream_redirect_uri,
        state=request.args.get('state'),
    )
    slack_oauth_url = url_add_query_params(
        "https://slack.com/oauth/authorize",
        client_id=SLACK_OAUTH_CLIENT_ID,
        redirect_uri=upstream_redirect_uri,
        scope='identity.basic',
        state=flask.json.dumps(state),
    )
    if not SLACK_OAUTH_CLIENT_ID:
        logging.warning("SLACK_OAUTH_CLIENT_ID isn't set")
        slack_oauth_url = "javascript:alert('Set SLACK_OAUTH_CLIENT_ID to enable this feature')"
    return render_template('login.html', slack_oauth_url=slack_oauth_url, email_oauth_url=email_oauth_url)


@profile.route('/oauth/deauthorize')
def deauthorize():
    redirect_uri = request.args.get('redirect_uri', '/oauth/authorize')
    clear_auth_cookies()
    return redirect(redirect_uri)


@profile.route('/oauth/slack')
def slack_auth():
    state = flask.json.loads(request.args['state'])
    redirect_uri = state.get('redirect_uri') or request.args['redirect_uri']
    if state['validation_code'] != SLACK_OAUTH_VALIDATION_CODE:
        redirect_uri = url_add_query_params(redirect_uri,
                                            error='access_denied',
                                            error_description='Upstream oauth service called back with invalid state'
                                            )
    elif 'error' in request.args:
        redirect_uri = url_add_query_params(redirect_uri, error=request.args['error'])
    else:
        redirect_uri = url_add_query_params(redirect_uri,
                                            access_token=create_access_token(provider='slack'),
                                            expires_in=str(6 * 30 * 24 * 3600),  # ignored by server
                                            state=state['state'],
                                            token_type='bearer',
                                            )
    return redirect(redirect_uri)


class EmailForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        validators.Regexp(r'.+@(students\.)?olin\.edu', message="An Olin address is required")])
    submit = SubmitField('Submit')
    redirect_uri = HiddenField()
    state = HiddenField()


@profile.route('/oauth/send_email', methods=["GET", "POST"])
def auth_send_email():
    form = EmailForm(
        redirect_uri=request.args.get('redirect_uri'),
        state=request.args.get('state'),
    )
    if form.validate_on_submit():
        email = request.args.get('email')
        email = form.email.data
        payload = {
            'iat': int(time.time()),
            'email': email,
            'redirect_uri': request.args.get('redirect_uri'),
            'state': request.args.get('state'),
        }
        token = jwt.encode(payload, app.secret_key, algorithm='HS256').decode()
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Sign into ABE'
        msg['To'] = email
        email_auth_link = url_add_query_params(request.url_root + 'oauth/email', token=token)
        body = render_template('oauth_email_body.html', email_auth_link=email_auth_link)
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        if send_message(msg):
            return render_template('sign_in_with_email.html', email_sent=True, email=email)
        else:
            flash("Failed to send email. Check the server log.")
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"Error in the {getattr(form, field).label.text} field - {error}")
    return render_template('sign_in_with_email.html', form=form)


@profile.route('/oauth/email')
def email_auth():
    payload = jwt.decode(request.args['token'].encode(), app.secret_key, algorithm='HS256')
    access_token = create_access_token(provider='email', email=payload['email'])
    redirect_uri = url_add_query_params(payload['redirect_uri'],
                                        access_token=access_token,
                                        expires_in=str(6 * 30 * 24 * 3600),  # ignored by server
                                        state=payload['state'],
                                        token_type='bearer',
                                        )
    return redirect(redirect_uri)
