from __future__ import annotations

import webbrowser
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model

from tracker.models import Profile


class Command(BaseCommand):
    help = "Bootstrap local dev: migrate, seed templates, create advisor user, optionally open URLs"

    def add_arguments(self, parser):
        parser.add_argument('--username', default='advisor', help='Advisor username')
        parser.add_argument('--password', default='changeme', help='Advisor password')
        parser.add_argument('--email', default='advisor@example.com', help='Advisor email')
        parser.add_argument('--open', action='store_true', help='Open advisor URLs in browser')

    def handle(self, *args, **opts):
        self.stdout.write('Running migrate...')
        call_command('migrate', interactive=False)
        self.stdout.write('Seeding templates...')
        call_command('seed_templates')

        User = get_user_model()
        username = opts['username']
        password = opts['password']
        email = opts['email']
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user {username}'))
        else:
            self.stdout.write(f'User {username} already exists')

        prof, _ = Profile.objects.get_or_create(user=user, defaults={'role': 'advisor'})
        if prof.role != 'advisor':
            prof.role = 'advisor'
            prof.save()
        self.stdout.write(self.style.SUCCESS(f'Advisor ready: {username} / {password}'))

        if opts['open']:
            try:
                webbrowser.open('http://127.0.0.1:8000/admin/')
                webbrowser.open('http://127.0.0.1:8000/advisor')
            except Exception:
                pass

