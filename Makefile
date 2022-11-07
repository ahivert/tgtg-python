test:
	poetry run pytest

lint:
	poetry run pre-commit run -a

publish:
	poetry publish --build