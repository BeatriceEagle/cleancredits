.PHONY: lint
lint:
	status=0;\
black . --check || status=1;\
isort . --check || status=1;\
exit $$status

.PHONY: fmt
fmt:
	black .
	isort .