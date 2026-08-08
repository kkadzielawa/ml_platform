.PHONY: test test-versions
test:
	python -m pytest

test-versions:
	python -m pytest tests/config
