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
PLUGINS := $(wildcard plugin/*/*.py)
SRC := $(wildcard src/*.py)
TESTS := $(wildcard test/test_*.py)
PYTHONPATH := $(CURDIR)/plugin:$(CURDIR)/src:$(CURDIR)/test
VENV := .venv
RP2_MAKEFILE := 1

all: $(VENV)/bin/activate

$(VENV)/bin/activate: bin/rp2_check_requirements.py requirements.txt
	bin/rp2_check_requirements.py
	virtualenv -p python3 $(VENV)
	$(VENV)/bin/pip3 install -r requirements.txt

run: $(VENV)/bin/activate
	rm -rf log/ output/
	bin/rp2.py -o output/ -p test_data_ config/test_data.config input/test_data.ods
	bin/rp2.py -o output/ -p crypto_example_ config/crypto_example.config input/crypto_example.ods

check: $(VENV)/bin/activate $(TESTS)
	$(foreach file, \
	  $(TESTS), \
	  echo; echo "Testing $(file)..."; \
	  PYTHONPATH=$(PYTHONPATH) $(VENV)/bin/python3 $(file); \
	)

lint: $(VENV)/bin/activate $(BIN) $(PLUGINS) $(SRC) $(TESTS)
	$(foreach file, \
	  $(BIN) $(PLUGINS) $(SRC) $(TESTS), \
	  echo; echo "Linting $(file)..."; \
	  PYTHONPATH=$(PYTHONPATH) pylint $(file); \
	)

# Don't typecheck files in $(BIN) because they perform a version check
# and are written using basic language features (no type hints) to ensure
# they parse and run correctly on old versions of the interpreter.
typecheck: $(VENV)/bin/activate $(PLUGINS) $(SRC) $(TESTS)
	$(foreach file, \
	  $(PLUGINS) $(SRC) $(TESTS), \
	  echo; echo "Type checking $(file)..."; \
	  MYPYPATH=$(PYTHONPATH):${CURDIR}/stubs mypy $(file); \
	)

reformat: $(VENV)/bin/activate $(BIN) $(PLUGINS) $(SRC) $(TESTS)
	isort .
	$(foreach file, \
	  $(BIN) $(PLUGINS) $(SRC) $(TESTS), \
	  echo; echo "Reformatting $(file)..."; \
	  PYTHONPATH=$(PYTHONPATH) black -l160 $(file); \
	)

archive: clean
	rm -f rp2.zip || true
	zip -r rp2.zip .

clean:
	rm -rf $(VENV) .mypy_cache/ log/ output/
	find . -type f -name '*.pyc' -delete

.PHONY: all run test lint typecheck reformat archive clean

