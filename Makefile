# Copyright 2021 eprbell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

BIN := $(wildcard bin/*.py)
RP2_SRC := $(wildcard src/rp2/*.py) $(wildcard src/rp2/plugin/*.py) $(wildcard src/rp2/plugin/*/*.py) $(wildcard src/rp2/plugin/*/*/*.py)
TEST_SRC := $(wildcard tests/*.py)
TESTS := $(wildcard tests/test_*.py)

PYTHONPATH := $(CURDIR)/src
VENV := .venv

RP2_MAKEFILE := 1

all: $(VENV)/bin/activate

$(VENV)/bin/activate: Makefile setup.py setup.cfg
	virtualenv -p python3 $(VENV)
	$(VENV)/bin/pip3 install -e ".[dev]"

run: $(VENV)/bin/activate
	rm -rf log/ output/
	$(VENV)/bin/rp2_us -o output/ -p test_data_ config/test_data.ini input/test_data.ods
	$(VENV)/bin/rp2_us -o output/ -p test_many_year_data_ config/test_data.ini input/test_data.ods
	$(VENV)/bin/rp2_us -o output/ -p crypto_example_ config/crypto_example.ini input/crypto_example.ods
# Temporarily removed lifo and hifo due to https://github.com/eprbell/rp2/issues/79
#	$(VENV)/bin/rp2_us -m lifo -o output/ -p test_data_ config/test_data.ini input/test_data.ods
#	$(VENV)/bin/rp2_us -m lifo -o output/ -p test_many_year_data_ config/test_data.ini input/test_data.ods
#	$(VENV)/bin/rp2_us -m lifo -o output/ -p crypto_example_ config/crypto_example.ini input/crypto_example.ods

check: $(VENV)/bin/activate
	$(VENV)/bin/pytest --tb=native --verbose

static_analysis: $(VENV)/bin/activate
	$(VENV)/bin/mypy src/ tests/
	$(VENV)/bin/pylint -r y src tests/*.py
	$(VENV)/bin/bandit -r src/

reformat: $(VENV)/bin/activate
	$(VENV)/bin/isort .
	$(VENV)/bin/black src/ tests/

archive: clean
	rm -f rp2.zip || true
	zip -r rp2.zip .

distribution: all
	$(VENV)/bin/pip3 install twine
	rm -rf build/ dist/
	$(VENV)/bin/python3 setup.py sdist bdist_wheel
	$(VENV)/bin/python3 -m twine check dist/*

upload_test_distribution: distribution
	$(VENV)/bin/pip3 install twine
	$(VENV)/bin/python3 -m twine upload --repository testpypi dist/*

upload_distribution: distribution
	$(VENV)/bin/pip3 install twine
	$(VENV)/bin/python3 -m twine upload dist/*

clean:
	rm -rf $(VENV) .mypy_cache/ build dist/ log/ output/ src/*.egg-info/
	find . -type f -name '*.pyc' -delete

.PHONY: all archive check clean lint reformat run securitycheck typecheck
