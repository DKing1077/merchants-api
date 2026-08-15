.PHONY: test test-cov

test:
	PYTHONPATH=. pytest app/tests -q

test-cov:
	PYTHONPATH=. pytest app/tests --cov=app --cov-report=term-missing
