style:
	poetry run black .
	poetry run isort .
	poetry run flake8

test:
	poetry run pytest

lint:
	poetry run pre-commit run -a

publish:
	poetry publish --build