# A Springy Little Configuration Reader

[![latest release](https://gitlab.com/bfosi/pyspry/-/badges/release.svg)](https://gitlab.com/bfosi/pyspry/-/releases)
[![pipeline status](https://gitlab.com/bfosi/pyspry/badges/main/pipeline.svg)](https://gitlab.com/bfosi/pyspry/-/pipelines/latest)
[![coverage report](https://gitlab.com/bfosi/pyspry/badges/main/coverage.svg)](https://bfosi.gitlab.io/pyspry/reports/pytest-html)
[![Maintainability](https://api.codeclimate.com/v1/badges/996a01b1ab2df27571d5/maintainability)](https://codeclimate.com/github/bryant-finney/pyspry/maintainability)
[![pylint](https://bfosi.gitlab.io/pyspry/reports/pylint.svg)](https://bfosi.gitlab.io/pyspry/reports/pylint-gitlab.html)
[![PyPI version](https://badge.fury.io/py/pyspry.svg)](https://badge.fury.io/py/pyspry)
[![Downloads](https://static.pepy.tech/badge/pyspry)](https://pepy.tech/project/pyspry)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![docs: pdoc](https://img.shields.io/badge/docs-pdoc-blueviolet?logo=gitlab)](https://bfosi.gitlab.io/pyspry/pyspry.html)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://bfosi.gitlab.io/pyspry/reports/mypy-html)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/bryant-finney/pyspry/main.svg)](https://results.pre-commit.ci/latest/github/bryant-finney/pyspry/main)

Influenced by [Spring Boot's YAML configuration features](https://docs.spring.io/spring-boot/docs/1.1.0.M1/reference/html/boot-features-external-config.html#boot-features-external-config-yaml),
this library reads system configuration settings from environment variables and YAML files.

## Installation

To install using `pip`:

```sh
pip install pyspry
```

## Usage

By default, a file named `config.yml` in the current directory will be loaded and parsed for
configuration settings. These can be accessed through the `pyspry.settings` module.

For example, consider the following `config.yml` file:

<!-- note: pdoc was struggling with a YAML markdown codeblock here -->
<div class="pdoc-code codehilite">
<pre><span></span><code><span class="nt">DATABASES</span><span class="p">:</span>
<span class="w">  </span><span class="nt">default</span><span class="p">:</span>
<span class="w">    </span><span class="nt">AUTOCOMMIT</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">true</span>
<span class="w">    </span><span class="nt">NAME</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">db.sqlite3</span>
<span class="nt">DEBUG</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">true</span>
<span class="nt">DEFAULT_CHARSET</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">utf-8</span>
</code></pre>
</div>

These configuration settings can be accessed as follows:

```py
>>> from pyspry import settings
>>> settings.DEBUG
True

>>> settings.DEFAULT_CHARSET
'utf-8'

```

### Specifying Alternate Config Files

Set the environment variable `PYSPRY_CONFIG_PATH` to override the default path to the configuration
file:

```py
>>> import os; os.environ["PYSPRY_CONFIG_PATH"]
'sample-config.yml'

>>> from pyspry import settings
>>> settings.PYSPRY_STATICFILES_FINDERS
['django.contrib.staticfiles.finders.FileSystemFinder', 'django.contrib.staticfiles.finders.AppDirectoriesFinder']

```

### Variable Prefixes

Set the environment variable `PYSPRY_VAR_PREFIX` to filter which settings are loaded:

```py
>>> import os; os.environ["PYSPRY_VAR_PREFIX"]
'PYSPRY'

>>> from pyspry import settings
>>> "TEST_RUNNER" in settings         # the prefix is automatically inserted
True

>>> "IGNORED_SETTING" in settings     # see the last line in 'sample-config.yml'
False

```

### Nested Structures

If the configuration includes nested data structures, each layer of nesting can be traversed using
`_`-separated names:

```py
>>> settings.LOGGING["version"] == settings.LOGGING_version == 1
True

>>> settings.LOGGING["loggers"]["pyspry"]["level"] == \
...   settings.LOGGING_loggers_pyspry_level == 'DEBUG'
True

```

### Environment Variables

In many cases, it can be useful to set one-off overrides for a setting. This can be done with an
environment variable:

```py
>>> import importlib, os
>>> settings.LOGGING_loggers_pyspry_level
'DEBUG'
>>> os.environ["PYSPRY_LOGGING_loggers_pyspry_level"] = "INFO"
>>> settings = importlib.reload(settings)
>>> settings.LOGGING["loggers"]["pyspry"]["level"]
'INFO'

```

### Django Integration

This package was originally designed for use with the [Django](https://www.djangoproject.com/)
framework. To use it:

```sh
# after installing the package, specify it as the settings module
export DJANGO_SETTINGS_MODULE=pyspry.settings

django-admin diffsettings
```

## Development

The following system dependencies are required:

- [`poetry`](https://python-poetry.org/docs/#installation)
- [`pre-commit`](https://pre-commit.com/#install)
- (optional) [`direnv`](https://direnv.net/docs/installation.html)
- (optional) [`docker`](https://docs.docker.com/get-docker/)

Common development commands are managed by [`poethepoet`](https://github.com/nat-n/poethepoet); run
`poe --help` for an up-to-date list of commands:

```txt
Poe the Poet - A task runner that works well with poetry.
version 0.20.0

USAGE
  poe [-h] [-v | -q] [--root PATH] [--ansi | --no-ansi] task [task arguments]

GLOBAL OPTIONS
  -h, --help     Show this help page and exit
  --version      Print the version and exit
  -v, --verbose  Increase command output (repeatable)
  -q, --quiet    Decrease command output (repeatable)
  -d, --dry-run  Print the task contents but don't actually run it
  --root PATH    Specify where to find the pyproject.toml
  --ansi         Force enable ANSI output
  --no-ansi      Force disable ANSI output

CONFIGURED TASKS
  setup-versioning  Install the 'poetry-dynamic-versioning' plugin to the local 'poetry' installation
  docs              Generate this package's docs
  docserver         Use 'pdoc' to launch an HTTP server for this package's docs
  lab               Run Jupyter Lab
  lint              Lint this package
  test              Test this package and report coverage
```

## Reports

- [`bandit`](https://bfosi.gitlab.io/pyspry/reports/bandit.html)
- [`mypy`](https://bfosi.gitlab.io/pyspry/reports/mypy-html/index.html)
- [`pytest` coverage](https://bfosi.gitlab.io/pyspry/reports/pytest-html/index.html)
