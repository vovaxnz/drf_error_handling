# core/management/commands/seed_db.py
import hashlib
import random
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from faker import Faker

from accounts.models import User, UserRole
from catalog.models import (
    ProductCategory,
    Product,
)
from commerce.models import (
    Quote,
    QuoteStatus,
    QuoteItem,
    Order,
    OrderStatus,
    OrderItem,
    Payment,
    PaymentStatus,
)

def money(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Seed database with fake data for all apps"

    def add_arguments(self, parser):
        parser.add_argument("--clients", type=int, default=30)
        parser.add_argument("--admins", type=int, default=2)

        parser.add_argument("--categories", type=int, default=25)

        parser.add_argument("--products_amount", type=int, default=100)
        

        parser.add_argument("--quotes", type=int, default=40)
        parser.add_argument("--quote-items-min", type=int, default=3)
        parser.add_argument("--quote-items-max", type=int, default=10)

        parser.add_argument("--orders", type=int, default=30)
        parser.add_argument("--seed", type=int, default=42)

        parser.add_argument("--keep", action="store_true", help="Do not wipe existing data")

    @transaction.atomic
    def handle(self, *args, **opts):
        fake = Faker()
        Faker.seed(opts["seed"])
        random.seed(opts["seed"])

        if not opts["keep"]:
            self.stdout.write("Wiping existing data ...")
            self._wipe()

        self.stdout.write("Seeding users ...")
        clients = self._seed_users(fake, role=UserRole.CLIENT, count=opts["clients"])
        admins = self._seed_users(fake, role=UserRole.ADMIN, count=opts["admins"])
        _ = admins  # noqa


        self.stdout.write("Seeding product categories ...")
        categories = self._seed_categories(fake, count=opts["categories"])

        self.stdout.write("Seeding products ...")
        all_products = self._seed_products(
            fake,
            categories=categories,
            amount=opts["products_amount"],
        )

        self.stdout.write("Seeding quotes ...")
        quotes = self._seed_quotes(
            fake=fake,
            clients=clients,
            all_products=all_products,
            quote_count=opts["quotes"],
            items_min=opts["quote_items_min"],
            items_max=opts["quote_items_max"],
        )

        self.stdout.write("Seeding orders, payments")
        self._seed_orders_and_fulfillment(
            fake=fake,
            quotes=quotes,
            order_count=opts["orders"],
        )

        self.stdout.write(self.style.SUCCESS("Done."))

    def _wipe(self):
        # order is important due to FKs
        Payment.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()

        QuoteItem.objects.all().delete()
        Quote.objects.all().delete()

        Product.objects.all().delete()
        ProductCategory.objects.all().delete()

        User.objects.all().delete()

    def _seed_users(self, fake: Faker, role: str, count: int):
        users = []
        for i in range(count):
            username = f"{role}_{i}_{fake.user_name()}"[:150]
            email = f"{role}.{i}.{fake.unique.email()}"
            user = User.objects.create_user(
                username=username,
                email=email,
                password="password123",
                role=role,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                is_active=True,
            )
            users.append(user)
        return users


    def _seed_categories(self, fake: Faker, count: int):
        # create a small tree: 5 roots, rest children
        roots_count = min(5, count)
        roots = []
        for _ in range(roots_count):
            roots.append(ProductCategory.objects.create(name=fake.unique.word().title()))

        categories = roots[:]
        for _ in range(count - roots_count):
            parent = random.choice(roots)
            name = f"{fake.unique.word().title()} {fake.unique.word().title()}"
            categories.append(ProductCategory.objects.create(name=name, parent=parent))

        return categories

    def _seed_products(self, fake: Faker,  categories, amount: int):
        result = list()
        for i in range(amount):
            cat = random.choice(categories)
            title=f"{fake.word().title()} {fake.word().title()}"
            hash_part = hashlib.sha256(title.encode()).hexdigest()[:6]
            sku = f"{hash_part}-{i}-{fake.unique.bothify(text='??##??##')}"
            price = money(Decimal(random.randint(5_00, 50_000)) / Decimal("100"))  # 5.00..500.00
            p = Product.objects.create(
                category=cat,
                title=title,
                description=fake.paragraph(nb_sentences=3),
                sku=sku,
                product_url=fake.url(),
                image_url=fake.image_url(),
                price_amount=price,
                price_currency="USD",
                attributes={
                    "color": fake.safe_color_name(),
                    "material": random.choice(["wood", "metal", "glass", "plastic", "fabric", "stone"]),
                    "size": random.choice(["S", "M", "L", "XL"]),
                },
                embedding_ref="",
                is_active=random.random() < 0.9,
            )
            result.append(p)
        return result

    def _seed_quotes(
        self,
        fake: Faker,
        clients,
        all_products,
        quote_count: int,
        items_min: int,
        items_max: int,
    ):
        quotes = []
        for _ in range(quote_count):
            client = random.choice(clients)

            q = Quote.objects.create(
                client=client,
                status=random.choices(
                    [QuoteStatus.OPEN, QuoteStatus.FROZEN, QuoteStatus.CONVERTED, QuoteStatus.EXPIRED],
                    weights=[0.55, 0.25, 0.15, 0.05],
                    k=1,
                )[0],
                currency="USD",
                total_amount=Decimal("0.00"),
            )

            pool = [p for p in all_products if p.is_active]

            n_items = random.randint(items_min, items_max)
            chosen = random.sample(pool, k=min(n_items, len(pool)))

            total = Decimal("0.00")
            for p in chosen:
                qty = random.randint(1, 3)
                qi = QuoteItem.objects.create(
                    quote=q,
                    product=p,
                    quantity=qty,
                    unit_price=p.price_amount,
                    currency=p.price_currency,
                )
                total += money(qi.unit_price * Decimal(qi.quantity))

            q.total_amount = money(total)
            q.save(update_fields=["total_amount"])

            quotes.append(q)

        return quotes

    def _seed_orders_and_fulfillment(self, fake: Faker, quotes, order_count: int):
        # pick only quotes that can reasonably become orders
        usable_quotes = [q for q in quotes if q.items.exists()]
        if not usable_quotes:
            return

        chosen_quotes = random.sample(usable_quotes, k=min(order_count, len(usable_quotes)))

        for q in chosen_quotes:
            client = q.client

            # Create Order (idempotent key is random here, in real flow should come from client request)
            idem = fake.unique.sha1()[:32]
            order = Order.objects.create(
                client=client,
                quote=q,
                status=OrderStatus.DRAFT,
                currency=q.currency,
                total_amount=q.total_amount,
                shipping_address={
                    "country": fake.country_code(),
                    "city": fake.city(),
                    "address1": fake.street_address(),
                    "postal_code": fake.postcode(),
                    "name": f"{fake.first_name()} {fake.last_name()}",
                    "phone": fake.phone_number(),
                },
                idempotency_key=idem,
            )

            # Create OrderItems snapshots from QuoteItems
            order_items = []
            for qi in q.items.select_related("product").all():
                p = qi.product
                oi = OrderItem.objects.create(
                    order=order,
                    product=p,
                    quantity=qi.quantity,
                    unit_price=qi.unit_price,
                    currency=qi.currency,
                    product_title=p.title,
                    sku=p.sku,
                    product_url=p.product_url,
                )
                order_items.append(oi)

            # Payment (succeeded in MVP)
            pay_idem = fake.unique.sha1()[:32]
            paid_at = timezone.now() - timezone.timedelta(minutes=random.randint(1, 20))
            Payment.objects.create(
                order=order,
                status=PaymentStatus.SUCCEEDED,
                amount=order.total_amount,
                currency=order.currency,
                provider="dummy",
                provider_reference=f"pay_{fake.unique.bothify(text='########')}",
                paid_at=paid_at,
                idempotency_key=pay_idem,
            )

            # Place order
            order.status = OrderStatus.PLACED
            order.placed_at = paid_at
            order.save(update_fields=["status", "placed_at"])
