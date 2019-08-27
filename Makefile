style:
	python3 -m poetry run black .
	python3 -m poetry run isort -y
	python3 -m poetry run flake8

test:
	python3 -m poetry run pytest --cov=tgtg