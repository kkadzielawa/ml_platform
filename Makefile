.PHONY: test test-versions test-contracts
test:
	python -m pytest

test-versions:
	python -m pytest tests/config

test-contracts:
	python -m pytest tests/contracts
