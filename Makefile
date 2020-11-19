style:
	python3 -m poetry run black .
	python3 -m poetry run isort .
	python3 -m poetry run flake8

test:
	python3 -m poetry run pytest

lint:
	python3 -m poetry run black . --check
	python3 -m poetry run isort . --check
	python3 -m poetry run flake8

publish:
	python3 -m poetry publish --build