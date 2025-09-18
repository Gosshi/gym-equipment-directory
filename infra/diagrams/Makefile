PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
OUTPUT := gym-preview-aws
VENV_MARKER := $(VENV)/.installed

.PHONY: init png svg all clean

$(VENV_MARKER): requirements.txt
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt
	touch $(VENV_MARKER)

init: $(VENV_MARKER)

png: $(VENV_MARKER)
	$(BIN)/python aws_arch.py --format png

svg: $(VENV_MARKER)
	$(BIN)/python aws_arch.py --format svg

all: png svg

clean:
	rm -f $(OUTPUT).png $(OUTPUT).svg $(OUTPUT).gv
