.PHONY: lint test contracts smoke check

lint:
	ruff check hydropinpoint tests app

test:
	pytest -m "not network" tests/

contracts:
	python -m hydropinpoint.check_contracts

smoke:
	python -m hydropinpoint.pipeline --smoke

check: lint test contracts
