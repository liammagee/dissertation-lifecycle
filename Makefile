.PHONY: help deploy logs ssh migrate seed-core apply-core admin advisor notify

help:
	@echo "Common tasks:"
	@echo "  make deploy        # fly deploy"
	@echo "  make logs          # fly logs"
	@echo "  make ssh           # open Fly SSH"
	@echo "  make migrate       # run migrations on Fly"
	@echo "  make seed-core     # reset templates to core-only"
	@echo "  make apply-core    # apply core milestones to existing projects"
	@echo "  make admin         # create superuser (env vars required)"
	@echo "  make advisor       # create advisor user"
	@echo "  make notify        # run notifications command"

deploy:
	fly deploy

logs:
	fly logs

ssh:
	fly ssh console

migrate:
	fly ssh console -C "python manage.py migrate"

seed-core:
	fly ssh console -C "python manage.py reset_templates --only-core"

apply-core:
	fly ssh console -C "python manage.py apply_core"

# Usage: DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_EMAIL=admin@example.com DJANGO_SUPERUSER_PASSWORD=pass make admin
admin:
	fly ssh console -C "DJANGO_SUPERUSER_USERNAME=$$DJANGO_SUPERUSER_USERNAME DJANGO_SUPERUSER_EMAIL=$$DJANGO_SUPERUSER_EMAIL DJANGO_SUPERUSER_PASSWORD='$$DJANGO_SUPERUSER_PASSWORD' python manage.py createsuperuser --noinput"

# Usage: USERNAME=advisor PASSWORD=changeme EMAIL=advisor@example.com make advisor
advisor:
	fly ssh console -C "python manage.py bootstrap_local --username '$$USERNAME' --password '$$PASSWORD' --email '$$EMAIL'"

# Usage: make notify DUE=3 INACTIVE=5
notify:
	fly ssh console -C "python manage.py notify --due-days $${DUE:-3} --inactivity-days $${INACTIVE:-5}"

