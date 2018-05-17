# Contributing to ABE

:+1::tada: First off, thanks for taking the time to contribute to ABE! :tada::+1:

## Help Needed

Please check out the [the open issues][issues].

## Project setup

### Pipenv

ABE uses [Pipenv][pipenv] for Python management.

First, [install pipenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/#installing-pipenv). Most commonly:

```shell
$ pip install --user pipenv
```

To resolve python dependencies:

```shell
$ pipenv install --dev
```

To enter a virtual environment:

```shell
pipenv shell
```

You can either develop within this virtual environment, or execute individual commands from outside with `pipenv run <COMMAND>`.

You will also need to export `ABE_PASS` and `ABE_EMAIL`, as [found here](https://docs.google.com/document/d/1CZ45xYT33sTi5xpFJF8BkEeniCRszaxcfwiBmvMdmbk/edit).

### RabbitMQ

Install RabbitMQ and any dependencies. Use [these instructions](http://www.rabbitmq.com/download.html). It will likely require a download of [Erlang](https://packages.erlang-solutions.com/erlang/), which must be installed separately.

### MongoDB

Install MongoDB. Use [these
instructions](https://docs.mongodb.com/getting-started/shell/installation/). On
macOS with [Homebrew](https://brew.sh/) installed, you can instead run `brew install mongodb`.

#### Load Sample Data

To load [sample data](../abe/sample_data.py) into the database, run:

```shell
python -m abe.sample_data
```

Load additional sample data via the following. Look at the files in
 `./tests/data` to see the format of the event and label JSON files.

```shell
python -m abe.sample_data --events event-data.json
python -m abe.sample_data --labels label-data.json
```

## Development

### Running Locally

Launch the API server in debug mode:

```shell
./scripts/server
```

(In debug mode, it will reload files when you edit them. You don't need to
quit and re-launch the server.)

Visit <http://127.0.0.1:3000>. You should see a top hat.

Visit <http://127.0.0.1:3000/events/>. You should see `[]`. (This is an empty
JSON list of events.)

### Running the celery tasks

To run the celery tasks concurrently with a local version of ABE, set
`ABE_EMAIL_USERNAME` and `ABE_EMAIL_PASSWORD` to credentials for a GMail
account. (Or, additionally set `ABE_EMAIL_HOST` and `ABE_EMAIL_PORT` to use
a non-GMail POP3 SSL account.)

In order to launch a local copy of ABE from inside the pipenv shell, run the slightly verbose:

```shell
honcho start -f ProcfileHoncho
```

or

```shell
celery -A tasks worker --beat -l info
```

in a separate terminal. These will run the "beat" and "worker" servers alongside the web server.

### Committing and Pushing changes

Please make sure to run the tests before you commit your changes. Run
`./scripts/pre-commit-check`. This runs the test suite and the linter. You can
also run these separately:

#### Testing

`python -m unittest`

This should print `OK` at the end:

```shell
$ python -m unittest
…
----------------------------------------------------------------------
Ran 4 tests in 1.124s

OK
```

Test a specific test:

```shell
$ python -m unittest tests/test_recurrences.py
```

View code coverage:

```shell
$ coverage run --source abe -m unittest
$ coverage html
$ open htmlcov/index.html
```

The test suite will print some `DeprecationWarning`s from files in `…/site-packages/mongoengine/` (#151). It is safe to ignore these.

#### Linting

```shell
$ flake8 abe tests *.py
```

[issues]: https://github.com/olinlibrary/ABE/issues

## Style Guides

### Python Style Guide

Code should follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) and [PEP
257](https://www.python.org/dev/peps/pep-0257/).

Run `pipenv run flake8 abe` to check your code.

### Markdown Style Guide

Markdown should pass [markdown-lint](https://github.com/remarkjs/remark-lint).

The following editor plugins keep code in compliance with markdown-lint:

* Atom: [linter-markdown](https://atom.io/packages/linter-markdown)
* Visual Studio Code:
  * [markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint)
    lints Markdown files.
  * [remark](https://marketplace.visualstudio.com/items?itemName=mrmlnc.vscode-remark)
    beautifies Markdown files.

[issues]: https://github.com/olinlibrary/ABE/issues
[pipenv]: https://docs.pipenv.org/