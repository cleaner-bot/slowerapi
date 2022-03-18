install:
	pip install .

test:
	pytest .

coverage:
	coverage run -m pytest .
	coverage report -m --fail-under 100

lint:
	flake8 . --max-line-length 88 --exclude build
	mypy . --exclude build
	codespell . --skip ".*"

test-all: coverage lint
