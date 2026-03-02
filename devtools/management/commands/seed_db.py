# devtools/management/commands/seed_db.py

import hashlib
import random
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from faker import Faker

from accounts.models import User, UserRole
from catalog.models import ProductCategory, Product
from commerce.models.quotes import Quote, QuoteItem
from commerce.models.orders import Order, OrderItem
from commerce.models.payments import Payment
from commerce.services.order_service import OrderService
from commerce.statuses import QuoteStatus


def money(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Seed database with fake but valid data"

    def add_arguments(self, parser):
        parser.add_argument("--clients", type=int, default=20)
        parser.add_argument("--admins", type=int, default=2)
        parser.add_argument("--categories", type=int, default=20)
        parser.add_argument("--products", type=int, default=80)
        parser.add_argument("--quotes", type=int, default=30)
        parser.add_argument("--orders", type=int, default=20)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--keep", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        fake = Faker()
        Faker.seed(opts["seed"])
        random.seed(opts["seed"])

        if not opts["keep"]:
            self._wipe()

        clients = self._seed_users(fake, UserRole.CLIENT, opts["clients"])
        self._seed_users(fake, UserRole.ADMIN, opts["admins"])

        categories = self._seed_categories(fake, opts["categories"])
        products = self._seed_products(fake, categories, opts["products"])

        quotes = self._seed_quotes(fake, clients, products, opts["quotes"])
        self._seed_orders(fake, quotes, opts["orders"])

        self.stdout.write(self.style.SUCCESS("Seeding completed."))

    def _wipe(self):
        Payment.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        QuoteItem.objects.all().delete()
        Quote.objects.all().delete()
        Product.objects.all().delete()
        ProductCategory.objects.all().delete()
        User.objects.all().delete()

    def _seed_users(self, fake, role, count):
        users = []
        for i in range(count):
            u = User.objects.create_user(
                username=f"{role}_{i}_{fake.user_name()}"[:150],
                email=fake.unique.email(),
                password="password123",
                role=role,
                is_active=True,
            )
            users.append(u)
        return users

    def _seed_categories(self, fake, count):
        categories = []
        roots = min(5, count)
        for _ in range(roots):
            categories.append(ProductCategory.objects.create(name=fake.unique.word().title()))
        for _ in range(count - roots):
            categories.append(
                ProductCategory.objects.create(
                    name=f"{fake.unique.word().title()} {fake.unique.word().title()}",
                    parent=random.choice(categories[:roots]),
                )
            )
        return categories

    def _seed_products(self, fake, categories, amount):
        result = []
        for i in range(amount):
            title = f"{fake.word().title()} {fake.word().title()}"
            sku = hashlib.sha256(title.encode()).hexdigest()[:8] + f"-{i}"
            price = money(Decimal(random.randint(500, 50000)) / Decimal("100"))

            p = Product.objects.create(
                category=random.choice(categories),
                title=title,
                description=fake.text(),
                sku=sku,
                product_url=fake.url(),
                image_url=fake.image_url(),
                price_amount=price,
                price_currency="USD",
                attributes={},
                is_active=True,
            )
            result.append(p)
        return result

    def _seed_quotes(self, fake, clients, products, count):
        quotes = []

        for _ in range(count):
            client = random.choice(clients)

            quote = Quote.objects.create(client=client)

            for product in random.sample(products, k=random.randint(1, 5)):
                quote.add_item(product=product, quantity=random.randint(1, 3))

            # transition draft -> sent
            quote.send()
            quote.save()

            # randomly accept or reject
            if random.random() < 0.7:
                quote.accept()
                quote.save()
            else:
                quote.reject()
                quote.save()

            quotes.append(quote)

        return quotes

    def _seed_orders(self, fake, quotes, count):
        accepted_quotes = [q for q in quotes if q.status == QuoteStatus.ACCEPTED]
        if not accepted_quotes:
            return

        chosen = random.sample(accepted_quotes, k=min(count, len(accepted_quotes)))

        for quote in chosen:
            order = OrderService.create_from_quote(
                quote=quote,
                client=quote.client,
            )

            # Create payment
            payment = Payment.objects.create(
                order=order,
                amount=order.total_amount,
                currency=order.currency,
                provider="dummy",
            )

            payment.start_processing()
            payment.save()

            payment.complete()
            payment.paid_at = timezone.now()
            payment.save()

            # confirm order (requires full payment)
            order.confirm()
            order.placed_at = timezone.now()
            order.save()

            # optionally progress further
            if random.random() < 0.8:
                order.process()
                order.save()

                if random.random() < 0.6:
                    order.ship()
                    order.save()

                    if random.random() < 0.5:
                        order.complete()
                        order.save()